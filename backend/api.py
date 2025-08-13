# backend/api.py

from __future__ import annotations
import os
from typing import Any, Dict, List
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA_DIR = os.path.join(ROOT, "data")

FRONTEND_DIR = os.path.join(ROOT, "frontend")
PUBLIC_DIR = os.path.join(ROOT, "public")

app = Flask(__name__, static_url_path=None, static_folder=None)
CORS(app)


# ---------- helpers ----------
def _dir(p: str) -> bool:
    return os.path.isdir(p)

def _file(p: str) -> bool:
    return os.path.isfile(p)

def _ls(p: str) -> List[str]:
    try:
        return sorted(os.listdir(p)) if _dir(p) else []
    except Exception:
        return []


def _serve_index():
    """Try to serve index.html from frontend/ or public/. Fallback: simple HTML help page."""
    if _file(os.path.join(FRONTEND_DIR, "index.html")):
        return send_from_directory(FRONTEND_DIR, "index.html")
    if _file(os.path.join(PUBLIC_DIR, "index.html")):
        return send_from_directory(PUBLIC_DIR, "index.html")
    # Fallback page so we never get "Cannot GET /"
    html = f"""
    <!doctype html>
    <meta charset="utf-8">
    <title>NegotiationPro</title>
    <style>
      body{{font-family:system-ui,Arial;margin:40px;line-height:1.5}}
      code{{background:#f4f4f4;padding:2px 4px;border-radius:4px}}
    </style>
    <h2>NegotiationPro is running ✅</h2>
    <p>No <code>index.html</code> was found.</p>
    <p>Add one at <code>{FRONTEND_DIR}/index.html</code> (preferred) or <code>{PUBLIC_DIR}/index.html</code>.</p>
    <ul>
      <li>Health check: <a href="/health">/health</a></li>
      <li>Static root (frontend): {_dir(FRONTEND_DIR)}</li>
      <li>Static root (public): {_dir(PUBLIC_DIR)}</li>
    </ul>
    """
    return (html, 200)


# ---------- health ----------
@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "NegotiationPro API",
        "frontend_dir": FRONTEND_DIR, "frontend_exists": _dir(FRONTEND_DIR), "frontend_files": _ls(FRONTEND_DIR),
        "public_dir": PUBLIC_DIR,     "public_exists": _dir(PUBLIC_DIR),     "public_files": _ls(PUBLIC_DIR),
    }), 200


# ---------- index & static ----------
# Serve the SPA (no redirect to avoid 404 in proxies)
@app.get("/")
def root():
    return _serve_index()

# Keep /app and /app/ working too
@app.get("/app")
def app_index_redirect():
    return _serve_index()

@app.get("/app/")
def app_index_slash():
    return _serve_index()

# Assets under /app/*
@app.get("/app/<path:fn>")
def app_assets(fn: str):
    p = os.path.join(FRONTEND_DIR, fn)
    if _file(p):
        return send_from_directory(FRONTEND_DIR, fn)
    p = os.path.join(PUBLIC_DIR, fn)
    if _file(p):
        return send_from_directory(PUBLIC_DIR, fn)
    return (f"File not found under frontend/ or public/: {fn}", 404)

# Optional direct static paths
@app.get("/frontend/<path:fn>")
def serve_frontend(fn: str):
    p = os.path.join(FRONTEND_DIR, fn)
    if _file(p):
        return send_from_directory(FRONTEND_DIR, fn)
    return (f"Not found: {p}", 404)

@app.get("/public/<path:fn>")
def serve_public(fn: str):
    p = os.path.join(PUBLIC_DIR, fn)
    if _file(p):
        return send_from_directory(PUBLIC_DIR, fn)
    return (f"Not found: {p}", 404)


# ---------- API (minimal demo so endpoints לא יפילו CI) ----------
@app.post("/questionnaire/report")
def questionnaire_report():
    payload = request.get_json(silent=True) or {}
    answers = payload.get("questionnaire") or payload.get("answers") or {}
    if not isinstance(answers, dict) or not answers:
        return jsonify({"status": "error", "reason": "No answers provided"}), 400
    html = f"<h3>NegotiationPro Report</h3><pre>{answers}</pre>"
    return jsonify({"status": "ok", "html": html}), 200

# simple feedback store in-memory (שומר רק במהלך ריצה)
_feedback: List[Dict[str, Any]] = []

@app.post("/feedback")
def feedback():
    payload = request.get_json(silent=True) or {}
    if isinstance(payload, dict):
        _feedback.append(payload)
    return jsonify({"status": "ok", "aggregate": {"count": len(_feedback)}}), 200

@app.get("/feedback/stats")
def feedback_stats():
    return jsonify({"status": "ok", "aggregate": {"count": len(_feedback)}}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "y")
    print(f"NegotiationPro running on http://localhost:{port} (Debug={debug})")
    app.run(host="0.0.0.0", port=port, debug=debug)
