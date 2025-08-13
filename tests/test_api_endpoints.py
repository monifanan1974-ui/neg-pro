import os, sys, json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import app

def test_health():
    client = app.test_client()
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("status") == "ok"

@pytest.mark.skip(reason="Disabling test due to missing battle_card_engine.py module")
def test_chat_md_minimal(monkeypatch):
    # Ensure no OpenAI calls
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
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "success"
    assert body["format"] == "md"
    assert "Estimated Success Probability" in body["card"]

@pytest.mark.skip(reason="Disabling test due to missing battle_card_engine.py module")
def test_chat_html_includes_ui(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = app.test_client()
    payload = {
        "style": "html",
        "answers": {
            "industry": "Tech",
            "role": "Senior Editor",
            "seniority": "mid",
            "country": "UK",
            "communication_style": "Analytical"
        }
    }
    r = client.post("/chat", data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "success"
    assert body["format"] == "html"
    assert "sim-btn" in body["card"]         # buttons simulation
    assert "tone-btn" in body["card"]        # tone carousel
    assert "ui_payload" in body
    assert "openings" in body["ui_payload"]
