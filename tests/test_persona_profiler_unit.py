# tests/test_persona_profiler_unit.py

from pathlib import Path

from backend.persona_profiler import PersonaProfiler


def test_profiler_basic(tmp_path):
    # Arrange: create minimal data dir (empty is fine for this unit)
    data_dir = tmp_path
    profiler = PersonaProfiler(str(data_dir))

    # Act
    profile = profiler.build(
        {
            "industry": "tech",
            "role": "senior editor",
            "seniority": "senior",
            "country": "UK",
            "communication_style": "Analytical",
            "counterpart_persona": "The Analyst (Data-driven)",
            "challenges": [],
            "personality_tone": "neutral",
        }
    )

    # Assert
    assert isinstance(profile, dict)
    assert "persona" in profile
    assert profile.get("country") == "UK"
