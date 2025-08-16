# api.py — thin runner for Negotiation Pro
from __future__ import annotations

import os
from flask import request, jsonify

# App factory lives in backend/app.py
from backend.app import create_app

# Optional feedback store (loaded only if present)
try:
    from backend.feedback_store import FeedbackStore  # type: ignore
except Exception:
    FeedbackStore = None  # fallback if module is not available

app = create_app()

@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "NegotiationPro API runner"}), 200

# Optional feedback endpoints (safe no-op if store missing)
if FeedbackStore is not None:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    feedback_store = FeedbackStore(data_dir=DATA_DIR)

    @app.post("/feedback")
    def feedback():
        payload = request.get_json(silent=True) or {}
        feedback_store.add(payload)
        return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200

    @app.get("/feedback/stats")
    def feedback_stats():
        return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("DEBUG", "true").lower() in {"1", "true", "yes", "y"}
    app.run(host="0.0.0.0", port=port, debug=debug)
