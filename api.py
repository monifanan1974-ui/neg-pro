--- START OF FILE api.py ---
# api.py
from __future__ import annotations
import os
from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(HERE)
DATA_DIR = os.path.join(ROOT, "data")

# Pointing to the correct template and asset directories
TEMPLATES_DIR = os.path.join(HERE, "backend", "templates")
FRONTEND_DIR  = os.path.join(ROOT, "frontend")
# There is no 'public' directory based on the screenshot, so we will not reference it.

# Corrected imports to include the 'backend' package prefix
from backend.engine_entrypoint import QuestionnaireEngine
from backend.feedback_store import FeedbackStore

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=FRONTEND_DIR)
CORS(app)
feedback_store = FeedbackStore(data_dir=DATA_DIR)

# Health check endpoint
@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "NegotiationPro API"}), 200

# Serve the main application index.html from /
@app.route('/')
def serve_root():
    return send_from_directory(app.static_folder, 'index.html')

# Serve other static files from the frontend directory
@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory(app.static_folder, path)

# ---------- API Endpoints ----------
@app.post("/questionnaire/report")
def questionnaire_report():
    payload = request.get_json(silent=True) or {}
    answers = payload.get("questionnaire") or payload.get("answers") or {}
    if not isinstance(answers, dict) or not answers:
        return jsonify({"status": "error", "reason": "No answers provided (expected JSON with 'questionnaire' or 'answers')."}), 400

    engine = QuestionnaireEngine(debug=os.getenv("DEBUG", "true").lower() in ("1", "true", "yes"))
    result = engine.run(answers)
    http_status = 200 if (result.get("status") == "ok" and result.get("html")) else 500
    return jsonify(result), http_status

@app.post("/feedback")
def feedback():
    payload = request.get_json(silent=True) or {}
    feedback_store.add(payload)
    return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200

@app.get("/feedback/stats")
def feedback_stats():
    return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "y")
    print("==== NegotiationPro API ====")
    print(f"Listening on http://localhost:{port} (Debug={debug})")
    print(f"Serving static files from: {FRONTEND_DIR}")
    app.run(host="0.0.0.0", port=port, debug=debug)
