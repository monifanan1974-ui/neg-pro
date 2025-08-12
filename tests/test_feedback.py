import os, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from api import app  # noqa

def test_feedback_roundtrip():
    client = app.test_client()
    save = client.post("/feedback", data=json.dumps({
        "scenario_id": "lowball",
        "outcome": "partial",
        "usefulness": 7,
        "notes": "Helped me keep it professional.",
        "persona": "Friend",
        "country": "UK"
    }), content_type="application/json")
    assert save.status_code == 200
    body = save.get_json()
    assert body["status"] == "ok"
    assert body["aggregate"]["count"] >= 1

    stats = client.get("/feedback/stats")
    assert stats.status_code == 200
    agg = stats.get_json()["aggregate"]
    assert "success_rate" in agg
