# backend_api.py
import os
import io
import uuid
import json
import time
import shutil
import tempfile
import threading
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# import your project-specific helpers from exp2.py and livevid1.py
import exp2
import livevid1

app = Flask(__name__)
CORS(app)

# storage for active sessions (in-memory). For production, persist to DB.
active_sessions = {}

# where to save uploads/reports
BASE_DIR = Path.cwd()
UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"
TMP_DIR = BASE_DIR / "tmp"
for d in (UPLOAD_DIR, REPORT_DIR, TMP_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Helper: Save uploaded file
def save_uploaded_file(file_storage, dest_dir: Path, filename: str = None) -> Path:
    if filename is None:
        filename = file_storage.filename or f"file_{int(time.time())}"
    out_path = dest_dir / filename
    file_storage.save(str(out_path))
    return out_path

# Helper: convert uploaded audio to WAV (16k mono) using ffmpeg if installed
def convert_to_wav(input_path: str, target_rate: int = 16000) -> str:
    # produce a .wav temp file
    base = Path(input_path)
    out_path = str(base.with_suffix(".wav"))
    try:
        # -y overwrite, -ar sample rate, -ac 1 mono
        subprocess.run([
            "ffmpeg", "-y", "-i", str(input_path),
            "-ar", str(target_rate), "-ac", "1", out_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return out_path
    except Exception as e:
        # ffmpeg might not be available; return input path to try direct transcription
        print("⚠️ ffmpeg conversion failed or not available:", e)
        return str(input_path)

# Endpoint: upload resume => create session
@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    try:
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        resume_file = request.files["resume"]
        # save file
        out_path = save_uploaded_file(resume_file, UPLOAD_DIR, f"{uuid.uuid4()}_{resume_file.filename}")
        # extract text using exp2's helper (if present)
        resume_text = ""
        try:
            resume_text = exp2.extract_text_from_pdf(str(out_path))
        except Exception as e:
            print("⚠️ extract_text_from_pdf failed:", e)
            # fallback: store empty resume_text
            resume_text = ""

        # generate personalized questions using exp2.generate_questions_from_resume + parse
        try:
            questions_text = exp2.generate_questions_from_resume(resume_text)
            questions = exp2.parse_questions_properly(questions_text)
            if not questions:
                questions = ["Tell me about yourself", "Describe a project you built", "Explain a technical challenge you solved"]
        except Exception as e:
            print("⚠️ Question generation failed:", e)
            questions = ["Tell me about yourself", "Describe a project you built", "Explain a technical challenge you solved"]

        session_id = str(uuid.uuid4())
        active_sessions[session_id] = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "resume_path": str(out_path),
            "resume_text": resume_text,
            "questions": questions,
            "answers": [],
            "evaluations": [],
            "monitoring": None,   # will be filled by start-monitoring
            "report_path": None
        }

        return jsonify({
            "session_id": session_id,
            "questions": questions,
            "question_count": len(questions)
        })
    except Exception as e:
        print("❌ upload-resume error:", e)
        return jsonify({"error": str(e)}), 500

# Endpoint: start server-side monitoring (non-blocking) for session
@app.route("/api/start-monitoring", methods=["POST"])
def start_monitoring():
    try:
        data = request.get_json(force=True)
        session_id = data.get("session_id")
        duration = int(data.get("duration", 180))  # default 3 minutes
        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session_id"}), 400

        def _run():
            try:
                log_dict, pdf_path = livevid1.run_monitor_for_session(session_id, duration)
                # store results in session
                active_sessions[session_id]["monitoring"] = {
                    "status": "completed",
                    "started_at": log_dict.get("started_at"),
                    "ended_at": log_dict.get("ended_at"),
                    "log": log_dict,
                    "monitor_report": pdf_path
                }
                print(f"✅ Monitoring completed for session {session_id}, report: {pdf_path}")
            except Exception as e:
                active_sessions[session_id]["monitoring"] = {"status": "failed", "error": str(e)}
                print(f"❌ Monitoring failed for session {session_id}: {e}")

        # spawn background thread
        t = threading.Thread(target=_run, daemon=True)
        t.start()

        # mark session as starting
        active_sessions[session_id]["monitoring"] = {"status": "starting", "requested_at": datetime.utcnow().isoformat()}
        return jsonify({"message": "monitoring started", "session_id": session_id})
    except Exception as e:
        print("❌ start-monitoring error:", e)
        return jsonify({"error": str(e)}), 500

# Endpoint: accept answer (JSON text or multipart audio file)
@app.route("/api/submit-answer", methods=["POST"])
def submit_answer():
    try:
        transcript = None
        # allow multipart/form-data with audio, or JSON with text answer
        if request.content_type and "multipart/form-data" in request.content_type:
            form = request.form
            session_id = form.get("session_id")
            qindex = int(form.get("question_index", -1))
            audio = request.files.get("audio")
            # optional textual 'answer' field
            answer_text = form.get("answer", None)

            if audio:
                # save temp
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=os.path.basename(audio.filename))
                os.close(tmp_fd)
                audio.save(tmp_path)
                try:
                    wav_path = convert_to_wav(tmp_path)
                    # use exp2 transcription helpers
                    try:
                        transcript = exp2.transcribe_with_whisper(wav_path)
                    except Exception as e:
                        print("⚠️ whisper transcription failed:", e)
                        transcript = exp2.transcribe_with_google_fallback(wav_path)
                finally:
                    # cleanup
                    try:
                        if os.path.exists(tmp_path): os.remove(tmp_path)
                    except: pass
                    try:
                        if os.path.exists(wav_path) and wav_path != tmp_path: os.remove(wav_path)
                    except: pass

                if not transcript:
                    transcript = ""
            else:
                transcript = answer_text or ""
        else:
            data = request.get_json(force=True, silent=True) or {}
            session_id = data.get("session_id")
            qindex = int(data.get("question_index", -1))
            transcript = data.get("answer", "") or ""

        # validations
        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session_id"}), 400
        session = active_sessions[session_id]
        if qindex < 0 or qindex >= len(session["questions"]):
            return jsonify({"error": "Invalid question_index"}), 400

        # If processing resources available, call enhanced_evaluate_answer (exp2)
        try:
            evaluation = exp2.enhanced_evaluate_answer(session["questions"][qindex], transcript, session["resume_text"])
        except Exception as e:
            print("⚠️ enhanced_evaluate_answer failed, using fallback:", e)
            # fallback: simple mock evaluation
            evaluation = {
                "overall_score": 60,
                "category_scores": {
                    "technical_accuracy": 15,
                    "completeness": 15,
                    "communication": 15,
                    "problem_solving": 10,
                    "relevance": 5
                },
                "strengths": ["Gave an answer"],
                "weaknesses": ["Needs more depth"],
                "detailed_feedback": "Fallback evaluation used because LLM evaluation failed.",
                "detailed_explanation": "This is a fallback evaluation."
            }

        # store
        session["answers"].append(transcript)
        session["evaluations"].append(evaluation)

        return jsonify({
            "message": "answer processed",
            "evaluation": evaluation,
            "transcript": transcript
        })
    except Exception as e:
        print("❌ submit-answer error:", e)
        return jsonify({"error": str(e)}), 500

# Endpoint: generate final report (synchronous)
@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    try:
        data = request.get_json(force=True) or {}
        session_id = data.get("session_id")
        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session_id"}), 400
        session = active_sessions[session_id]
        questions = session["questions"]
        answers = session["answers"]
        evaluations = session["evaluations"]
        resume_text = session.get("resume_text", "")

        # generate final assessment (calls exp2.generate_final_interview_assessment)
        try:
            final_assessment = exp2.generate_final_interview_assessment(evaluations, resume_text)
        except Exception as e:
            print("⚠️ generate_final_interview_assessment failed:", e)
            final_assessment = {
                "final_recommendation": "Consider improvement",
                "confidence_level": 5,
                "overall_assessment": "Fallback assessment used"
            }

        # create comprehensive PDF using exp2.create_comprehensive_report
        try:
            pdf_path = exp2.create_comprehensive_report(questions, answers, evaluations, final_assessment, resume_text)
            # this function in exp2 returns a path (observed in your repo)
            if not pdf_path:
                raise RuntimeError("create_comprehensive_report returned no path")
        except Exception as e:
            print("❌ create_comprehensive_report failed:", e)
            return jsonify({"error": "Failed to create report", "detail": str(e)}), 500

        # attach monitoring report if exists for the session
        monitor = session.get("monitoring") or {}
        monitor_pdf = monitor.get("monitor_report")

        # store in session
        session["report_path"] = pdf_path

        return jsonify({
            "message": "report generated",
            "report_path": pdf_path,
            "monitor_report": monitor_pdf
        })
    except Exception as e:
        print("❌ generate-report error:", e)
        return jsonify({"error": str(e)}), 500

# Debug: get session state
@app.route("/api/get-session/<session_id>", methods=["GET"])
def get_session(session_id):
    s = active_sessions.get(session_id)
    if not s:
        return jsonify({"error": "not found"}), 404
    return jsonify(s)

if __name__ == "__main__":
    print("Starting backend_api on http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=True)
