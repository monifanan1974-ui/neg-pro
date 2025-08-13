# tests/test_feedback.py

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_PATH = PROJECT_ROOT / "api.py"


def _load_app():
    spec = importlib.util.spec_from_file_location("api", str(API_PATH))
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module.app


def test_feedback_roundtrip():
    app = _load_app()
    client = app.test_client()

    # post feedback
    payload = {"entries": [{"ts": 1754796553, "scenario_id": "lowball", "outcome": "partial"}]}
    r = client.post("/feedback", json=payload)
    assert r.status_code == 200

    # get stats
    r2 = client.get("/feedback/stats")
    assert r2.status_code == 200
    data = r2.get_json()
    assert data.get("status") == "ok"
    assert "aggregate" in data
