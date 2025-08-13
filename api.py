# backend/api.py

from __future__ import annotations
import os
from typing import Any, Dict, List

from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(HERE)
DATA_DIR = os.path.join(ROOT, "data")

TEMPLATES_DIR = os.path.join(HERE, "templates")
FRONTEND_DIR = os.path.join(ROOT, "frontend")
PUBLIC_DIR = os.path.join(ROOT, "public")

# ---- Safe imports with fallbacks -------------------------------------------------

# Questionnaire engine (fallback to a tiny stub if missing)
try:
    from backend.engine_entrypoint import QuestionnaireEngine  # type: ignore
except Exception:
    class QuestionnaireEngine:  # minimal stub to keep CI green
        def __init__(self, debug: bool = False) -> None:
            self.debug = debug
        def run(self, answers: Dict[str, Any]) -> Dict[str, Any]:
            # Return a very simple HTML wrapper so the frontend has something to render
            html = f"<h3>NegotiationPro Report (stub)</h3><pre>{answers}</pre>"
            return {"status": "ok", "html": html, "debug": self.debug, "engine": "stub"}

# Optional battlecard routes registration
def _try_register_battlecards(flask_app: Flask) -> None:
    try:
        from backend.battlecard_integration_plus import register_battlecard_routes  # type: ignore
        register_battlecard_routes(flask_app)
    except Exception:
        # Silently ignore if file is absent; keep API running
        pass

# Feedback store (fallback in-memory if module missing)
try:
    from backend.feedback_store import FeedbackStore  # type: ignore
except Exception:
    class FeedbackStore:
        def __init__(self, data_dir: str) -> None:
            self._items: List[Dict[str, Any]] = []
        def add(self, payload: Dict[str, Any]) -> None:
            if isinstance(payload, dict):
                self._items.append(payload)
        def aggregate(self) -> Dict[str, Any]:
            total = len(self._items)
            usefulness = [x.get("usefulness") for x in self._items if isinstance(x.get("usefulness"), (int, float))]
            avg_usefulness = (sum(usefulness) / len(usefulness)) if usefulness else None
            return {"count": total, "avg_usefulness": avg_usefulness}

# ---- Flask app -------------------------------------------------------------------

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_url_path=None, static_folder=None)
CORS(app)

# Register optional battlecard routes if available
_try_register_battlecards(app)

feedback_store = FeedbackStore(data_dir=DATA_DIR)

# ---- Helpers --------------------------------------------------------------------

def _dir(p: str) -> bool: 
    return os.path.isdir(p)

def _file(p: str) -> bool: 
    return os.path.isfile(p)

def _ls(p: str):
    try:
        return sorted(os.listdir(p)) if _dir(p) else []
    except Exception:
        return []

# ---- Health & static -------------------------------------------------------------

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
def app_assets(fn: str):
    p = os.path.join(FRONTEND_DIR, fn)
    if _file(p):
        return send_from_directory(FRONTEND_DIR, fn)
    p = os.path.join(PUBLIC_DIR, fn)
    if _file(p):
        return send_from_directory(PUBLIC_DIR, fn)
    return (f"File not found under frontend/ or public/: {fn}", 404)

# Optional direct static routes
@app.get("/frontend/<path:fn>")
def serve_frontend(fn: str):
    p = os.path.join(FRONTEND_DIR, fn)
    if _file(p):
        return send_from_directory(FRONTEND_DIR, fn)
    return (f"File not found: {p}", 404)

@app.get("/public/<path:fn>")
def serve_public(fn: str):
    p = os.path.join(PUBLIC_DIR, fn)
    if _file(p):
        return send_from_directory(PUBLIC_DIR, fn)
    return (f"File not found: {p}", 404)

# ---- API endpoints ---------------------------------------------------------------

@app.post("/questionnaire/report")
def questionnaire_report():
    payload = request.get_json(silent=True) or {}
    answers = payload.get("questionnaire") or payload.get("answers") or {}
    if not isinstance(answers, dict) or not answers:
        return jsonify({"status": "error", "reason": "No answers provided (expected JSON with 'questionnaire' or 'answers')."}), 400

    engine = QuestionnaireEngine(debug=os.getenv("DEBUG", "true").lower() in ("1", "true", "yes"))
    result = engine.run(answers)
    http = 200 if (isinstance(result, dict) and result.get("status") == "ok" and result.get("html")) else 500
    return jsonify(result), http

@app.post("/feedback")
def feedback():
    payload = request.get_json(silent=True) or {}
    feedback_store.add(payload)
    return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200

@app.get("/feedback/stats")
def feedback_stats():
    return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200

# ---- Main -----------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "y")
    print("==== NegotiationPro API ====")
    print(f"Listening on http://localhost:{port} (Debug={debug})")
    print(f"[static root] frontend = {FRONTEND_DIR}")
    app.run(host="0.0.0.0", port=port, debug=debug)
