<<<<<<< HEAD
--- START OF FILE api.py ---
# api.py
from __future__ import annotations
import os
import sys
from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS

# Add the project root to the Python path to help with module resolution
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(HERE)
sys.path.insert(0, ROOT)

DATA_DIR = os.path.join(ROOT, "data")
FRONTEND_DIR  = os.path.join(ROOT, "frontend")

# Corrected imports to include the 'backend' package prefix
from backend.engine_entrypoint import QuestionnaireEngine
from backend.feedback_store import FeedbackStore

# Serve static files from the frontend directory
app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)
feedback_store = FeedbackStore(data_dir=DATA_DIR)

# --- Static File Routing ---
@app.route('/')
def serve_root():
    """Serves the main index.html file."""
    # Based on the file list, the main index seems to be in the 'backend' folder
    # This should probably be moved to 'frontend' for consistency
    return send_from_directory(os.path.join(ROOT, 'backend'), 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    """Serves other static files like CSS, JS, or JSON from the root or frontend."""
    # Check root directory first for files like report_embed.js
    if os.path.exists(os.path.join(ROOT, path)):
        return send_from_directory(ROOT, path)
    # Fallback to frontend directory
    return send_from_directory(app.static_folder, path)

# --- API Endpoints ---
@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "NegotiationPro API"}), 200

@app.post("/questionnaire/report")
def questionnaire_report():
    payload = request.get_json(silent=True) or {}
    answers = payload.get("questionnaire") or payload.get("answers") or {}
    if not isinstance(answers, dict) or not answers:
        return jsonify({"status": "error", "reason": "No answers provided in the expected format."}), 400

    engine = QuestionnaireEngine(debug=os.getenv("DEBUG", "true").lower() in ("1", "true", "yes"))
    result = engine.run(answers)
    http_status = 200 if (result.get("status") == "ok" and result.get("html")) else 500
    return jsonify(result), http_status
=======
# api.py — Thin runner for NegotiationPro
# RUN from project root:  python api.py

from backend.app import create_app

# Do NOT import engine_entrypoint here.
# backend/app.py already handles importing the engine via:
#   from .engine_entrypoint import QuestionnaireEngine

app = create_app()
>>>>>>> 761b083 (Your commit message here)

@app.post("/feedback")
def feedback():
    payload = request.get_json(silent=True) or {}
    feedback_store.add(payload)
    return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200

@app.get("/feedback/stats")
def feedback_stats():
    return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200


# --- Main Execution ---
if __name__ == "__main__":
<<<<<<< HEAD
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "y")
    print("==== NegotiationPro API ====")
    print(f"Listening on http://localhost:{port} (Debug={debug})")
    print(f"Serving static files from: {FRONTEND_DIR} and {ROOT}")
    app.run(host="0.0.0.0", port=port, debug=debug)
=======
    # Bind on all interfaces for containers/Codespaces; keep debug=True for dev
    app.run(host="0.0.0.0", port=5000, debug=True)
>>>>>>> 761b083 (Your commit message here)
