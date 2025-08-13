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

def test_chat_md_minimal(monkeypatch):
    # Ensure no OpenAI calls
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = app.test_client()
    payload = {
        "style": "md",
        "questionnaire": {
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
    assert "Dummy battle card" in body["card"]

def test_chat_html_includes_ui(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = app.test_client()
    payload = {
        "style": "html",
        "questionnaire": {
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
    assert "Dummy battle card" in body["card"]
