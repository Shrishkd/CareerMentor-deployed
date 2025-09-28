import os
import uuid
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import exp2
import livevid1
import shutil 
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
SUPABASE_BUCKET_REPORTS = os.getenv("SUPABASE_BUCKET_REPORTS", "careerMentor")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if USE_SUPABASE else None

def store_report_and_get_url(local_path: str, session_id: str):
    if not USE_SUPABASE:
        return {"storage": "local", "path": local_path, "url": None}
    storage_key = f"{session_id}/{os.path.basename(local_path)}"
    with open(local_path, "rb") as f:
        supabase.storage.from_(SUPABASE_BUCKET_REPORTS).upload(
            storage_key, f, {"content-type": "application/pdf", "upsert": True}
        )
    signed = supabase.storage.from_(SUPABASE_BUCKET_REPORTS).create_signed_url(storage_key, 60*60*24*7)  # 7 days
    return {"storage": "supabase", "path": storage_key, "url": signed["signedURL"]}


BASE_DIR = os.path.dirname(os.path.abspath(__file__))             # .../Backend
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir)) # repo root

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")        # keep uploads inside Backend
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")   # write PDFs to repo-level /reports

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_ORIGIN", "*")}})


@app.route("/api/healthz", methods=["GET"])
def health():
    return jsonify({"ok": True})

# In-memory session storage
active_sessions = {}

# Save uploaded file
def save_uploaded_file(file_storage, folder, filename):
    out_path = os.path.join(folder, filename)
    file_storage.save(out_path)
    return out_path

# Helper: ensure evaluation is a dict (normalize string -> try JSON -> fallback dict)
def normalize_evaluation(eval_obj, fallback_note="Evaluation fallback used"):
    # if already dict, return
    if isinstance(eval_obj, dict):
        return eval_obj
    # if it's JSON string -> try parse
    if isinstance(eval_obj, str):
        s = eval_obj.strip()
        if not s:
            return {
            "overall_score": 50,
            "category_scores": {},
            "strengths": [],
            "weaknesses": ["No evaluation returned"],
            "detailed_feedback": fallback_note,
            "detailed_explanation": "No evaluation text returned from model.",
            "improvement_suggestions": [],
            "interviewer_notes": "",
            "follow_up_questions": []
        }
        try:
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            # not JSON, continue to fallback below
            pass

        # fallback: wrap string into feedback
        return {
    "overall_score": 50,
    "category_scores": {},
    "strengths": [],
    "weaknesses": ["No evaluation returned"],
    "detailed_feedback": fallback_note,
    "detailed_explanation": "No evaluation text returned from model.",
    "improvement_suggestions": [],
    "interviewer_notes": "",
    "follow_up_questions": []
        }

    # any other type -> convert to string fallback
    try:
        txt = str(eval_obj)
    except Exception:
        txt = "Unknown evaluation format"
    return {
        "overall_score": 50,
    "category_scores": {},
    "strengths": [],
    "weaknesses": ["No evaluation returned"],
    "detailed_feedback": fallback_note,
    "detailed_explanation": "No evaluation text returned from model.",
    "improvement_suggestions": [],
    "interviewer_notes": "",
    "follow_up_questions": []
    }

# =========================
# Endpoint: upload resume
# =========================
@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    try:
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        resume_file = request.files["resume"]
        out_path = save_uploaded_file(resume_file, UPLOAD_DIR, f"{uuid.uuid4()}_{resume_file.filename}")

        # Extract text
        try:
            resume_text = exp2.extract_text_from_pdf(str(out_path))
        except Exception as e:
            print("⚠️ extract_text_from_pdf failed:", e)
            resume_text = ""

        # Generate questions
        try:
            q_text = exp2.generate_questions_from_resume(resume_text)
            questions = exp2.parse_questions_properly(q_text)
            if not questions:
                questions = [
                    "Tell me about yourself",
                    "Describe a project you built",
                    "Explain a technical challenge you solved"
                ]
        except Exception as e:
            print("⚠️ Question generation failed:", e)
            questions = [
                "Tell me about yourself",
                "Describe a project you built",
                "Explain a technical challenge you solved"
            ]

        session_id = str(uuid.uuid4())
        active_sessions[session_id] = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "resume_path": str(out_path),
            "resume_text": resume_text,
            "questions": questions,
            "answers": [],
            "evaluations": [],
            "monitoring": None,
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

# =========================
# Endpoint: submit answer
# =========================
@app.route("/api/submit-answer", methods=["POST"])
def submit_answer():
    """
    Accepts either:
    - JSON: { session_id, question_index, answer, type: "text"|"code" }
    - multipart/form-data: session_id, question_index, audio=file
    """
    try:
        # JSON path (text/code)
        if request.is_json:
            data = request.get_json()
            session_id = data.get("session_id")
            try:
                q_idx = int(data.get("question_index", 0))
            except Exception:
                q_idx = 0
            answer = data.get("answer", "") or ""
            ans_type = data.get("type", "text")

            if not session_id or session_id not in active_sessions:
                return jsonify({"error": "Invalid or missing session_id"}), 400

            session = active_sessions[session_id]

            # validate question index
            questions = session.get("questions", [])
            if q_idx < 0 or q_idx >= len(questions):
                return jsonify({"error": "Invalid question_index"}), 400

            question = questions[q_idx]
            resume_ctx = session.get("resume_text", "")

            # Route to code evaluator or normal evaluator
            if ans_type == "code":
                try:
                    eval_result = exp2.evaluate_code_answer(question, answer, resume_ctx)
                except Exception as e:
                    print("⚠️ evaluate_code_answer failed:", e)
                    # fallback: try enhanced_evaluate_answer or wrap fallback
                    try:
                        eval_result = exp2.enhanced_evaluate_answer(question, answer, resume_ctx)
                    except Exception as e2:
                        print("⚠️ fallback evaluator also failed:", e2)
                        eval_result = {
                            "overall_score": 50,
                            "category_scores": {},
                            "strengths": [],
                            "weaknesses": ["Evaluation failed"],
                            "detailed_feedback": str(e2)
                        }
            else:
                try:
                    eval_result = exp2.enhanced_evaluate_answer(question, answer, resume_ctx)
                except Exception as e:
                    print("⚠️ enhanced_evaluate_answer failed:", e)
                    try:
                        eval_result = exp2.evaluate_answer(answer)
                    except Exception as e2:
                        print("⚠️ evaluate_answer fallback failed:", e2)
                        eval_result = {
                            "overall_score": 50,
                            "category_scores": {},
                            "strengths": [],
                            "weaknesses": ["Evaluation failed"],
                            "detailed_feedback": str(e2)
                        }

            # Normalize evaluation to dict (safety)
            eval_result = normalize_evaluation(eval_result)

            # store
            session["answers"].append(answer)
            session["evaluations"].append(eval_result)

            return jsonify({
                "transcript": answer,
                "evaluation": eval_result
            })

        # multipart/form-data path (audio upload)
        else:
            session_id = request.form.get("session_id")
            if not session_id or session_id not in active_sessions:
                return jsonify({"error": "Invalid or missing session_id"}), 400

            try:
                q_idx = int(request.form.get("question_index", 0))
            except Exception:
                q_idx = 0

            session = active_sessions[session_id]
            questions = session.get("questions", [])
            if q_idx < 0 or q_idx >= len(questions):
                return jsonify({"error": "Invalid question_index"}), 400

            if "audio" not in request.files:
                return jsonify({"error": "No audio uploaded"}), 400

            audio_file = request.files["audio"]
            out_path = save_uploaded_file(audio_file, UPLOAD_DIR, f"{uuid.uuid4()}_{audio_file.filename}")

            # Transcribe audio (exp2 helper)
            try:
                transcript = exp2.transcribe_with_whisper(str(out_path))
            except Exception as e:
                print("⚠️ transcribe_with_whisper failed:", e)
                transcript = ""

            # Evaluate using enhanced evaluator (question context + resume)
            question = questions[q_idx]
            resume_ctx = session.get("resume_text", "")
            try:
                evaluation = exp2.enhanced_evaluate_answer(question, transcript, resume_ctx)
            except Exception as e:
                print("⚠️ enhanced_evaluate_answer failed:", e)
                try:
                    evaluation = exp2.evaluate_answer(transcript)
                except Exception as e2:
                    print("⚠️ fallback evaluate_answer failed:", e2)
                    evaluation = {
                        "overall_score": 0,
                        "strengths": [],
                        "weaknesses": ["Evaluation failed"],
                        "detailed_feedback": str(e2)
                    }

            # Normalize and store
            evaluation = normalize_evaluation(evaluation)
            session["answers"].append(transcript)
            session["evaluations"].append(evaluation)

            return jsonify({
                "transcript": transcript,
                "evaluation": evaluation
            })

    except Exception as e:
        print("❌ submit-answer error:", e)
        return jsonify({"error": str(e)}), 500

# =========================
# Endpoint: start monitoring
# =========================
@app.route("/api/start-monitoring", methods=["POST"])
def start_monitoring():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        duration = int(data.get("duration", 180))

        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session"}), 400

        # Launch monitoring (non-blocking)
        report_path = livevid1.start_monitoring_async(session_id, duration, REPORTS_DIR)
        active_sessions[session_id]["monitoring"] = {
            "duration": duration,
            "report_path": report_path
        }
        return jsonify({"status": "monitoring started"})
    except Exception as e:
        print("❌ start-monitoring error:", e)
        return jsonify({"error": str(e)}), 500

# =========================
# Endpoint: generate report
# =========================
@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session"}), 400

        session = active_sessions[session_id]

        questions = session.get("questions", [])
        answers = session.get("answers", [])
        evaluations = session.get("evaluations", [])
        resume_text = session.get("resume_text", "")

        # ✅ Build a minimal final_assessment dict so PDF has data
        final_assessment = {
            "final_recommendation": "Promising candidate, recommended for further rounds.",
            "confidence_level": 8,
            "overall_assessment": "The candidate performed well overall. Strengths outweigh weaknesses.",
            "key_strengths": ["Good technical foundation", "Clear communication"],
            "development_areas": ["Handle edge cases better", "Optimize code efficiency"],
            "technical_level": "Intermediate to Advanced",
            "communication_rating": 8,
            "problem_solving_rating": 7,
            "role_fit": "Strong fit for software engineering roles requiring problem-solving.",
            "next_steps": "Schedule a live technical round for deeper evaluation."
        }

        # ✅ Save PDF to repo-root /reports folder
        report_path = exp2.create_comprehensive_report(
            questions, answers, evaluations, final_assessment, resume_text,
        )

        # ✅ Optionally upload to Supabase storage
        meta = {"storage": "local", "path": report_path, "url": None}
        if supabase:  # only if Supabase client configured
            try:
                storage_key = f"{session_id}/{os.path.basename(report_path)}"
                with open(report_path, "rb") as f:
                    supabase.storage.from_(SUPABASE_BUCKET_REPORTS).upload(
                        storage_key, f, {"content-type": "application/pdf", "upsert": True}
                    )
                signed = supabase.storage.from_(SUPABASE_BUCKET_REPORTS).create_signed_url(
                    storage_key, 60 * 60 * 24 * 7  # 7 days
                )
                meta = {"storage": "supabase", "path": storage_key, "url": signed["signedURL"]}
            except Exception as e:
                print("⚠️ Supabase upload failed:", e)

        session["report_path"] = report_path
        session["report_meta"] = meta

        return jsonify({
            "report_path": report_path,
            "report_url": meta.get("url"),
            "evaluations": evaluations
        })

    except Exception as e:
        print("❌ generate-report error:", e)
        return jsonify({"error": str(e)}), 500


# =========================
# Endpoint: download report
# =========================
@app.route("/api/download-report/<session_id>", methods=["GET"])
def download_report(session_id):
    try:
        if session_id not in active_sessions:
            return jsonify({"error": "Invalid session"}), 400

        session = active_sessions[session_id]
        meta = session.get("report_meta") or {}
        report_path = session.get("report_path")

        # ✅ Prefer Supabase signed URL if available
        if meta.get("storage") == "supabase" and meta.get("url"):
            return jsonify({"signed_url": meta["url"]})

        # ✅ Otherwise fall back to local file
        if not report_path or not os.path.exists(report_path):
            return jsonify({"error": "Report not found"}), 404

        return send_file(report_path, as_attachment=True)

    except Exception as e:
        print("❌ download-report error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
