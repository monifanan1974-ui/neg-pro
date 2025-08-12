# backend/api.py
from __future__ import annotations
import os
from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))

TEMPLATES_DIR = os.path.join(HERE, "templates")
FRONTEND_DIR  = os.path.join(ROOT, "frontend")
PUBLIC_DIR    = os.path.join(ROOT, "public")

from engine_entrypoint import QuestionnaireEngine

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_url_path=None, static_folder=None)
CORS(app)

def _dir(p): return os.path.isdir(p)
def _file(p): return os.path.isfile(p)
def _ls(p):
    try:
        return sorted(os.listdir(p)) if _dir(p) else []
    except Exception:
        return []

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "NegotiationPro API",
        "version": "2025-08-12",
        "frontend_dir": FRONTEND_DIR, "frontend_exists": _dir(FRONTEND_DIR), "frontend_files": _ls(FRONTEND_DIR),
        "public_dir": PUBLIC_DIR,     "public_exists": _dir(PUBLIC_DIR),     "public_files": _ls(PUBLIC_DIR),
        "active_static_root": FRONTEND_DIR if _dir(FRONTEND_DIR) else PUBLIC_DIR
    }), 200

@app.get("/")
def root():
    # Always redirect to /app/ (with a trailing slash) so relative paths resolve correctly.
    return redirect(url_for("app_index_slash"))

# If someone hits /app (no slash), redirect to /app/
@app.get("/app")
def app_index_redirect():
    return redirect(url_for("app_index_slash"))

# Serve the SPA index from frontend/ (or public/ as a fallback)
@app.get("/app/")
def app_index_slash():
    idx = os.path.join(FRONTEND_DIR, "index.html")
    if _file(idx):
        return send_from_directory(FRONTEND_DIR, "index.html")
    idx = os.path.join(PUBLIC_DIR, "index.html")
    if _file(idx):
        return send_from_directory(PUBLIC_DIR, "index.html")
    return ("index.html not found. Put it under 'frontend/' (preferred) or 'public/'.", 404)

# Serve assets relative to /app/ → /app/report_embed.js, /app/questionnaire.json, etc.
@app.get("/app/<path:fn>")
def app_assets(fn):
    p = os.path.join(FRONTEND_DIR, fn)
    if _file(p):
        return send_from_directory(FRONTEND_DIR, fn)
    p = os.path.join(PUBLIC_DIR, fn)
    if _file(p):
        return send_from_directory(PUBLIC_DIR, fn)
    return (f"File not found under frontend/ or public/: {fn}", 404)

# Optional direct static routes
@app.get("/frontend/<path:fn>")
def serve_frontend(fn):
    p = os.path.join(FRONTEND_DIR, fn)
    if _file(p):
        return send_from_directory(FRONTEND_DIR, fn)
    return (f"File not found: {p}", 404)

@app.get("/public/<path:fn>")
def serve_public(fn):
    p = os.path.join(PUBLIC_DIR, fn)
    if _file(p):
        return send_from_directory(PUBLIC_DIR, fn)
    return (f"File not found: {p}", 404)

# ---------- API ----------
@app.post("/questionnaire/report")
def questionnaire_report():
    payload = request.get_json(silent=True) or {}
    answers = payload.get("questionnaire") or payload.get("answers") or {}
    if not isinstance(answers, dict) or not answers:
        return jsonify({"status": "error", "reason": "No answers provided (expected JSON with 'questionnaire' or 'answers')."}), 400

    engine = QuestionnaireEngine(debug=os.getenv("DEBUG", "true").lower() in ("1", "true", "yes"))
    result = engine.run(answers)
    http = 200 if (result.get("status") == "ok" and result.get("html")) else 500
    return jsonify(result), http

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "y")
    print("==== NegotiationPro API ====")
    print(f"Listening on http://localhost:{port} (Debug={debug})")
    print(f"[static root] frontend = {FRONTEND_DIR}")
    app.run(host="0.0.0.0", port=port, debug=debug)
