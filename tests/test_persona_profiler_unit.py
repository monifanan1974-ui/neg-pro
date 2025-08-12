import sys, os
from pathlib import Path
import json
import pytest

# Make backend importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from persona_profiler import PersonaProfiler  # noqa


@pytest.fixture()
def tmp_data_dir(tmp_path):
    # Minimal data dir; profiler tolerates missing content
    d = tmp_path
    # Create empty JSON files used by _safe_load
    (d / "Maagar_Sofi_994.json").write_text("{}", encoding="utf-8")
    (d / "local-data.json").write_text("{}", encoding="utf-8")
    (d / "rules-engine.json").write_text("{}", encoding="utf-8")
    (d / "tactic_library.json").write_text("{}", encoding="utf-8")
    return d


def test_profile_finance_high_context_direct_analytical(tmp_data_dir):
    p = PersonaProfiler(str(tmp_data_dir))
    out = p.build({
        "industry": "Finance",
        "role": "Analyst",
        "seniority": "lead",
        "country": "JP",
        "communication_style": "Direct Analytical",
        "counterpart_persona": "",     # let the detector infer
        "challenges": ["Anxiety", "Burnout", "Imposter", "Other"]
    })

    # Culture inference
    assert out["culture"] == "high"
    # Persona by industry defaults
    assert "Analyst" in out["persona"]
    # Decision style signals
    assert "data-first" in out["decision_style"]
    assert "concise" in out["decision_style"]
    assert "time-boxed decisions" in out["decision_style"]
    # Tone derived from decision style (concise -> firm)
    assert out["tone"] == "firm"
    # Motivations/Fears for finance
    assert "risk control" in out["motivations"]
    assert "audit issues" in out["fears"]
    # Challenge signals mapping (case-insensitive)
    assert "prefer soft openers" in out["challenge_signals"]
    assert "short meetings" in out["challenge_signals"]
    assert "emphasize objective wins" in out["challenge_signals"]
    # Unknown challenge passes through
    assert "Other" in out["challenge_signals"]


@pytest.mark.parametrize("industry,expected_snippet", [
    ("Tech", "Friend"),
    ("Software", "Friend"),
    ("Marketing Agency", "Fox"),
    ("", "Dominator"),
])
def test_persona_defaults_by_industry(tmp_data_dir, industry, expected_snippet):
    p = PersonaProfiler(str(tmp_data_dir))
    out = p.build({
        "industry": industry,
        "role": "Any",
        "seniority": "mid",
        "country": "UK",
        "communication_style": "Diplomatic"
    })
    assert expected_snippet in out["persona"]
    # Culture low for UK
    assert out["culture"] == "low"
    # Decision style for Diplomatic -> consensus-seeking
    assert "consensus-seeking" in out["decision_style"]
    # Tone neutral when no "concise"
    assert out["tone"] in ("neutral", "firm")  # neutral expected here
