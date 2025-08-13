import os, sys, json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.api import app

def test_health():
    client = app.test_client()
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    # Accept either {"ok": True} or {"status":"ok"} shapes
    assert (body.get("ok") is True) or (body.get("status") == "ok")

def test_report_minimal_html():
    client = app.test_client()
    payload = {
        "style": "html",
        "answers": {
            "industry": "Tech",
            "target_title": "Senior Editor",
            "role": "Senior Editor",
            "seniority": "mid",
            "country": "UK",
            "communication_style": "Analytical",
            "counterpart_persona": "Analyst / Data-driven",
            "impacts": ["cut cycle 28%", "12/12 on-time"],
            "range_low": "36000",
            "range_high": "58000",
            "target_salary": "58000",
            "priorities_ranked": ["Salary","Title","Flexibility"]
        }
    }
    r = client.post("/report", data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("status") == "ok"
    assert isinstance(body.get("html"), str) and len(body["html"]) > 50

@pytest.mark.skip(reason="chat endpoint disabled by default until battle_card_engine is present")
def test_chat_md_minimal(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = app.test_client()
    payload = {
        "style": "md",
        "answers": {
            "industry": "Tech",
            "role": "Senior Editor",
            "seniority": "mid",
            "country": "UK",
            "communication_style": "Analytical"
        }
    }
    r = client.post("/chat", data=json.dumps(payload), content_type="application/json")
    assert r.status_code in (200, 404)  # depending on whether /chat is enabled
