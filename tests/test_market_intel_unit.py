import sys
from pathlib import Path
import json
import pytest

# Import backend modules
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from market_intel import MarketIntel  # noqa


@pytest.fixture()
def data_dir_with_rules_and_local(tmp_path):
    # data-validation with VR001 + VR002
    validation = {
        "validation_rules": [
            {"id": "VR001", "message": "Glassdoor alone may be biased — add another source."},
            {"id": "VR002", "message": "Missing salary range."}
        ]
    }
    (tmp_path / "data-validation.json").write_text(json.dumps(validation), encoding="utf-8")

    # local-data with comp benchmarks
    local = {
        "comp_benchmarks": {
            "roles": {
                "Senior Editor|UK": {"p25": "£74k", "p75": "£82k"}
            }
        }
    }
    (tmp_path / "local-data.json").write_text(json.dumps(local), encoding="utf-8")

    return tmp_path


def test_build_parses_impacts_and_infers_range(data_dir_with_rules_and_local):
    mi = MarketIntel(str(data_dir_with_rules_and_local))
    profile = {"country": "UK"}

    out = mi.build({
        "impacts": [],
        "achievements_text": "Reduced cycle 28%, 12 on-time campaigns",
        "market_sources": ["Glassdoor"],     # single source -> should add BLS/Industry
        "role": "Senior Editor",
        "range_low": "",
        "range_high": "",
    }, profile)

    # Impacts parsed from CSV text
    assert "Reduced cycle 28%" in out["impacts"]
    assert "12 on-time campaigns" in out["impacts"]

    # Market sources should have at least 2 (and unique)
    assert len(out["sources"]) >= 2
    assert "Glassdoor" in out["sources"]

    # Range inferred from local-data.json
    assert out["range_low"] == "£74k"
    assert out["range_high"] == "£82k"
    assert out["meta"]["source"] == "local-data.json"
    # Since range was inferred, VR002 shouldn't trigger
    assert not any("No salary range provided" in w for w in out["warnings"])


def test_build_missing_range_triggers_warning_when_local_empty(tmp_path):
    # Minimal validation with VR002
    validation = {
        "validation_rules": [
            {"id": "VR002", "message": "Missing salary range."}
        ]
    }
    (tmp_path / "data-validation.json").write_text(json.dumps(validation), encoding="utf-8")
    (tmp_path / "local-data.json").write_text("{}", encoding="utf-8")

    mi = MarketIntel(str(tmp_path))
    profile = {"country": "UK"}

    out = mi.build({
        "impacts": [],
        "market_sources": ["Glassdoor"],     # will be auto-augmented
        "role": "Unknown Role",
        "range_low": "",
        "range_high": "",
    }, profile)

    # No local match -> ranges empty, VR002 warning present
    assert out["range_low"] == ""
    assert out["range_high"] == ""
    assert any("No salary range provided" in w for w in out["warnings"])
    # Sources augmented to at least 2
    assert len(out["sources"]) >= 2


@pytest.mark.parametrize("persona,premium_str", [
    ("The Dominator (Aggressive)", "£83,200"),  # +4% on 80k => 83,200
    ("The Analyst (Data-driven)", "£80,800"),   # +1% => 80,800
    ("The Friend (Relationship-focused)", "£81,600"),  # +2% => 81,600
    ("The Fox (Cunning)", "£81,600"),           # +2%
])
def test_numeric_anchor_premium_by_persona(data_dir_with_rules_and_local, persona, premium_str):
    mi = MarketIntel(str(data_dir_with_rules_and_local))
    # base from average of 70k–90k = 80k, risk=3 (no extra)
    tail, amount = mi.numeric_anchor("£70k", "£90k", "", persona=persona, risk=3, symbol="£")
    assert amount == premium_str
    assert premium_str in tail


def test_numeric_anchor_risk_amplifies_premium(data_dir_with_rules_and_local):
    mi = MarketIntel(str(data_dir_with_rules_and_local))
    # Analyst (1%) + risk 5 adds 2% → total 3% of 80k = 82,400
    tail, amount = mi.numeric_anchor("£70k", "£90k", "", persona="The Analyst", risk=5, symbol="£")
    assert amount == "£82,400"
    assert "£82,400" in tail


def test_numeric_anchor_handles_missing_base(data_dir_with_rules_and_local):
    mi = MarketIntel(str(data_dir_with_rules_and_local))
    tail, amount = mi.numeric_anchor("", "", "", persona="The Friend", risk=3, symbol="£")
    assert amount is None
    assert "within that range" in tail
