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

# ----------------- helpers -----------------
def _dir(p: str) -> bool: return os.path.isdir(p)
def _file(p: str) -> bool: return os.path.isfile(p)
def _ls(p: str) -> List[str]:
    try: return sorted(os.listdir(p)) if _dir(p) else []
    except Exception: return []

def _serve_index():
    if _file(os.path.join(FRONTEND_DIR, "index.html")):
        return send_from_directory(FRONTEND_DIR, "index.html")
    if _file(os.path.join(PUBLIC_DIR, "index.html")):
        return send_from_directory(PUBLIC_DIR, "index.html")
    html = f"""<!doctype html><meta charset="utf-8"><title>NegotiationPro</title>
    <style>body{{font-family:system-ui;margin:40px;background:#0b1220;color:#e5e7eb}}
    a{{color:#60a5fa}}</style>
    <h2>NegotiationPro is running ✅</h2>
    <p>No <code>index.html</code> found. Add one to <code>{FRONTEND_DIR}</code> or <code>{PUBLIC_DIR}</code>.</p>
    <ul>
      <li><a href="/health">/health</a></li>
      <li>frontend exists: {_dir(FRONTEND_DIR)}, public exists: {_dir(PUBLIC_DIR)}</li>
    </ul>"""
    return (html, 200)

# ----------------- health & static -----------------
@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "NegotiationPro API",
        "frontend_exists": _dir(FRONTEND_DIR),
        "public_exists": _dir(PUBLIC_DIR),
    }), 200

@app.get("/")
def root(): return _serve_index()
@app.get("/app")        # keep old URLs working
def app_index_redirect(): return _serve_index()
@app.get("/app/")
def app_index_slash(): return _serve_index()

@app.get("/app/<path:fn>")
def app_assets(fn: str):
    p = os.path.join(FRONTEND_DIR, fn)
    if _file(p): return send_from_directory(FRONTEND_DIR, fn)
    p = os.path.join(PUBLIC_DIR, fn)
    if _file(p): return send_from_directory(PUBLIC_DIR, fn)
    return (f"File not found under frontend/ or public/: {fn}", 404)

# ----------------- report API -----------------
def _build_report_html(answers: Dict[str, Any]) -> str:
    # very small HTML so there's always something to show
    rows = "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in answers.items())
    return f"""<!doctype html><meta charset="utf-8">
    <style>body{{font-family:system-ui;margin:20px;background:#0b1326;color:#e5e7eb}}</style>
    <h2>NegotiationPro Report</h2><ul>{rows}</ul>"""

def _report_impl(payload: Dict[str, Any]):
    answers = payload.get("answers") or payload.get("questionnaire") or {}
    if not isinstance(answers, dict) or not answers:
        return jsonify({"status": "error", "reason": "Missing answers/questionnaire dict"}), 400
    html = _build_report_html(answers)
    return jsonify({"status": "ok", "html": html}), 200

@app.post("/report")
def report():
    payload = request.get_json(silent=True) or {}
    return _report_impl(payload)

# compatibility with older frontend
@app.post("/questionnaire/report")
def questionnaire_report():
    payload = request.get_json(silent=True) or {}
    return _report_impl(payload)

# ----------------- feedback (minimal, in-memory) -----------------
_FEEDBACK: List[Dict[str, Any]] = []

@app.post("/feedback")
def feedback():
    payload = request.get_json(silent=True) or {}
    if isinstance(payload, dict): _FEEDBACK.append(payload)
    return jsonify({"status": "ok", "aggregate": {"count": len(_FEEDBACK)}}), 200

@app.get("/feedback/stats")
def feedback_stats():
    return jsonify({"status": "ok", "aggregate": {"count": len(_FEEDBACK)}}), 200

# ----------------- main -----------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "y")
    print("==== NegotiationPro API ====")
    print(f"Listening on http://localhost:{port} (Debug={debug})")
    print(f"[static root] frontend = {FRONTEND_DIR}")
    app.run(host="0.0.0.0", port=port, debug=debug)
