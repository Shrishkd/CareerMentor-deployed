# livevid1.py
import os
import cv2
import time
import json
import math
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Tuple
from dotenv import load_dotenv
load_dotenv()

# mediapipe typically imported as mp; if not installed the script will fail at import
try:
    import mediapipe as mp
    MP_AVAILABLE = True
except Exception:
    MP_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = False
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        GENAI_AVAILABLE = True
    else:
        print("❌ No Gemini API key found in env. Set GOOGLE_API_KEY to enable Gemini.")
except Exception:
    GENAI_AVAILABLE = False
    print("❌ google.generativeai library not available (pip install google-generativeai).")



from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from PIL import Image

# Paths
BASE_DIR = Path.cwd()
REPORT_DIR = BASE_DIR / "reports"
EVIDENCE_DIR = BASE_DIR / "reports" / "evidence"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Monitoring thresholds (tweakable)
SHOULDER_TILT_THR = 0.06
NECK_SLUMP_DEG_THR = 12
HAND_MOVE_THR = 0.03
GAZE_DOWN_THR = 0.02

# default gemini model name (if you have API set up)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.0")

# Global minimal log template
def new_log(session_id: str):
    return {
        "session_id": session_id,
        "started_at": datetime.utcnow().isoformat(),
        "ended_at": None,
        "eye_contact": {"center": 0, "left": 0, "right": 0, "down": 0, "examples": []},
        "posture": {"correct": 0, "incorrect": 0, "examples": []},
        "hand_movements": {"detected": 0, "examples": []},
        "objects_detected": {"gadgets": [], "examples": []},
        "frames_processed": 0,
        "duration_sec": 0.0
    }

# small helper to save a frame example image
def save_frame_example(frame, tag, frame_id, session_id):
    fname = f"{session_id}_{tag}_{frame_id}_{int(time.time())}.jpg"
    outp = EVIDENCE_DIR / fname
    try:
        # convert BGR -> RGB and save
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        Image.fromarray(rgb).save(outp)
        return str(outp)
    except Exception as e:
        print("⚠️ failed to save frame example:", e)
        return None

# Build a short prompt for LLM summary (if genai available)
def build_gemini_prompt(log_dict):
    summary = {
        "frames_processed": log_dict.get("frames_processed"),
        "eye_contact": log_dict.get("eye_contact"),
        "posture": log_dict.get("posture"),
        "hand_movements": log_dict.get("hand_movements"),
    }
    prompt = "You are an interview coach. Summarize the candidate performance in three short sections: Executive summary, Observations with evidence, and Actionable tips.\n\n"
    prompt += json.dumps(summary, indent=2)
    return prompt

def get_gemini_report(log_dict):
    try:
        if not GENAI_AVAILABLE:
            raise RuntimeError("Generative AI not available")
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(build_gemini_prompt(log_dict))
        text = resp.text or ""
        return text
    except Exception as e:
        # fallback coaching text
        return (
            "Executive summary: The candidate showed a mix of good and improvable behaviours.\n\n"
            "Observations: Eye contact was variable; posture sometimes slouched; hand movements detected.\n\n"
            "Actionable tips: Practice maintaining steady eye contact with the camera, sit upright, and reduce excessive hand gestures."
        )

# create a PDF with the coaching text and evidence thumbnails
def make_pdf_report(pdf_path: str, log_dict: dict, coaching_text: str):
    try:
        W, H = A4
        margin = 2 * cm
        c = canvas.Canvas(pdf_path, pagesize=A4)
        y = H - margin
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, "AI Interview Monitoring Report")
        y -= 30

        styles = getSampleStyleSheet()
        para = styles["Normal"]
        text_lines = coaching_text.split("\n")
        c.setFont("Helvetica", 10)
        for line in text_lines:
            if y < margin + 40:
                c.showPage()
                y = H - margin
            c.drawString(margin, y, line)
            y -= 14

        # add evidence thumbnails if present
        def add_section(title, paths):
            nonlocal y
            if not paths: return
            c.setFont("Helvetica-Bold", 12)
            if y < margin + 80:
                c.showPage()
                y = H - margin
            c.drawString(margin, y, title)
            y -= 16
            cols = 3
            gap = 0.5 * cm
            iw = (W - 2 * margin - (cols - 1) * gap) / cols
            ih = 4 * cm
            x = margin
            for i, p in enumerate(paths):
                try:
                    img = ImageReader(p)
                    w0, h0 = img.getSize()
                    scale = min(iw / w0, ih / h0)
                    fw, fh = w0 * scale, h0 * scale
                    if y - fh < margin:
                        c.showPage()
                        y = H - margin
                    c.drawImage(p, x, y - fh, fw, fh)
                except Exception:
                    pass
                x += iw + gap
                if (i + 1) % cols == 0:
                    x = margin
                    y -= ih + 20
            y -= 16

        add_section("Evidence: Eye Contact Examples", log_dict["eye_contact"]["examples"])
        add_section("Evidence: Posture Examples", log_dict["posture"]["examples"])
        add_section("Evidence: Hand Movement Examples", log_dict["hand_movements"]["examples"])

        c.showPage()
        c.save()
        return True
    except Exception as e:
        print("❌ make_pdf_report failed:", e)
        traceback.print_exc()
        return False

# ---------------- Core per-frame processing logic ----------------
def process_frame(frame, mp_face_mesh, face_mesh, pose, hands, prev_state, frame_id, log, session_id):
    """Analyze one frame; update log and return updated prev_state"""
    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Face/gaze processing
        if mp_face_mesh and face_mesh:
            res = face_mesh.process(rgb)
            if res.multi_face_landmarks and len(res.multi_face_landmarks) > 0:
                # approximate gaze using eye center y relative to nose
                lm = res.multi_face_landmarks[0]
                # select some landmarks for eyes & nose (approx indices, may vary)
                ih, iw = frame.shape[:2]
                # use approximate coords: 1 = nose tip, 33 left eye outer, 263 right eye outer (mediapipe face mesh indexing)
                try:
                    nose = lm.landmark[1]
                    left_eye = lm.landmark[33]
                    right_eye = lm.landmark[263]
                    nose_y = nose.y
                    eye_center_y = (left_eye.y + right_eye.y) / 2
                    dy = eye_center_y - nose_y
                    # classify gaze roughly
                    if dy < -GAZE_DOWN_THR:
                        log["eye_contact"]["down"] += 1
                        if frame_id % 10 == 0:
                            p = save_frame_example(frame, "gaze_down", frame_id, session_id)
                            if p: log["eye_contact"]["examples"].append(p)
                    else:
                        log["eye_contact"]["center"] += 1
                except Exception:
                    pass

        # Pose/posture
        if pose:
            resp = pose.process(rgb)
            if resp.pose_landmarks:
                pl = resp.pose_landmarks.landmark
                # use shoulders 11 (left), 12 (right), ears 7,8 roughly
                try:
                    ls, rs = pl[11], pl[12]
                    le, re = pl[7], pl[8]
                    tilt = abs(ls.y - rs.y)
                    mid_ear = ((le.x + re.x) / 2, (le.y + re.y) / 2)
                    mid_shoulder = ((ls.x + rs.x) / 2, (ls.y + rs.y) / 2)
                    neck_vec = (mid_ear[0] - mid_shoulder[0], mid_ear[1] - mid_shoulder[1])
                    neck_angle = math.degrees(math.atan2(neck_vec[1], neck_vec[0]) * -1)
                    incorrect = tilt > SHOULDER_TILT_THR or abs(neck_angle) > NECK_SLUMP_DEG_THR
                    if incorrect:
                        log["posture"]["incorrect"] += 1
                        if frame_id % 15 == 0:
                            p = save_frame_example(frame, "posture_incorrect", frame_id, session_id)
                            if p: log["posture"]["examples"].append(p)
                    else:
                        log["posture"]["correct"] += 1
                except Exception:
                    pass

        # Hands movement
        if hands:
            hr = hands.process(rgb)
            if hr.multi_hand_landmarks:
                try:
                    # check movement distance between successive frames
                    cur = hr.multi_hand_landmarks[0].landmark[0]
                    hx, hy = cur.x, cur.y
                    prev = prev_state.get("hand_pos")
                    if prev:
                        dist = math.hypot(hx - prev[0], hy - prev[1])
                        if dist > HAND_MOVE_THR:
                            log["hand_movements"]["detected"] += 1
                            if frame_id % 10 == 0:
                                p = save_frame_example(frame, "hand_move", frame_id, session_id)
                                if p: log["hand_movements"]["examples"].append(p)
                    prev_state["hand_pos"] = (hx, hy)
                except Exception:
                    pass

        log["frames_processed"] = log.get("frames_processed", 0) + 1
    except Exception as e:
        print("⚠️ process_frame exception:", e)
    return prev_state

# ---------------- run_monitor_for_session wrapper ----------------
def run_monitor_for_session(session_id: str, duration_sec: int = 180) -> Tuple[dict, str]:
    """
    Run camera monitoring for duration_sec seconds (non-interactive).
    Returns: (log_dict, pdf_path)
    """
    if not MP_AVAILABLE:
        raise RuntimeError("mediapipe not installed or not available on this environment")

    log = new_log(session_id)
    start_ts = time.time()
    frame_id = 0
    prev_state = {}

    mp_face_mesh = mp.solutions.face_mesh if MP_AVAILABLE else None
    mp_pose = mp.solutions.pose if MP_AVAILABLE else None
    mp_hands = mp.solutions.hands if MP_AVAILABLE else None

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # try directshow on Windows; on linux default is fine
    if not cap.isOpened():
        # attempt without cv2.CAP_DSHOW
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Webcam not accessible - ensure device has a camera and server has permission")

    try:
        with mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1) as face_mesh, \
             mp_pose.Pose(model_complexity=1) as pose, \
             mp_hands.Hands(max_num_hands=2) as hands:

            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frame_id += 1
                prev_state = process_frame(frame, mp_face_mesh, face_mesh, pose, hands, prev_state, frame_id, log, session_id)

                # Optional: show live window for debugging (comment out in headless servers)
                try:
                    cv2.imshow("Interview Monitor (press q to quit early)", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                except Exception:
                    # headless environment can't show window, ignore
                    pass

                # stop after duration
                if (time.time() - start_ts) >= duration_sec:
                    break

        # cleanup
        try:
            cap.release()
            cv2.destroyAllWindows()
        except:
            pass

        log["ended_at"] = datetime.utcnow().isoformat()
        log["duration_sec"] = int(time.time() - start_ts)

        # create coaching text via genai or fallback
        coaching_text = get_gemini_report(log)

        # build pdf path
        pdf_name = f"Interview_Report_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = str(REPORT_DIR / pdf_name)

        success = make_pdf_report(pdf_path, log, coaching_text)
        if not success:
            raise RuntimeError("Failed to create PDF report")

        # return log dict and pdf_path
        return log, pdf_path

    except Exception as e:
        traceback.print_exc()
        # ensure resources are released
        try:
            cap.release()
        except:
            pass
        raise

# Keep original run_monitor() for direct CLI testing if desired
def run_monitor():
    """Run interactively until 'q' pressed (keeps old behaviour for debugging)."""
    if not MP_AVAILABLE:
        raise RuntimeError("mediapipe not installed")
    print("Starting interactive monitor. Press 'q' in the window to stop.")
    log = new_log("interactive")
    try:
        l, pdf = run_monitor_for_session("interactive", duration_sec=6000)
        print("Interactive monitoring finished.")
    except Exception as e:
        print("Interactive monitoring error:", e)

if __name__ == "__main__":
    # when run directly for testing: run for 2 minutes
    sid = f"localtest_{int(time.time())}"
    l, p = run_monitor_for_session(sid, duration_sec=120)
    print("Report saved to:", p)
