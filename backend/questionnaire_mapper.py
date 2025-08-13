# backend/questionnaire_mapper.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

HIGH_CONTEXT_COUNTRIES = {
    "japan",
    "china",
    "south korea",
    "korea",
    "greece",
    "italy",
    "spain",
    "portugal",
    "turkey",
    "brazil",
    "mexico",
    "uae",
    "saudi arabia",
    "qatar",
    "egypt",
    "morocco",
    "israel",
}
DEFAULT_MARKET_SOURCES = ["Glassdoor", "Levels.fyi"]


def _normalize(s: Optional[str]) -> str:
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    return re.sub(r"\s+", " ", s.strip().lower())


def _split_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    txt = str(value)
    return [v.strip() for v in re.split(r"[;,]|\n", txt) if v.strip()]


def _parse_salary_value(s: Any) -> Optional[str]:
    if s is None:
        return None
    txt = str(s).strip()
    return txt if txt else None


def _infer_persona(text: str) -> str:
    t = _normalize(text)
    if any(k in t for k in ["budget", "tight budget", "budget constraint"]):
        return "budget_guard"
    if any(k in t for k in ["aggressive", "hardball", "pushy", "dominating"]):
        return "assertive"
    if any(k in t for k in ["skeptic", "need proof", "doubt", "prove"]):
        return "skeptical"
    if any(k in t for k in ["urgent", "deadline", "time pressure", "asap"]):
        return "time_pressed"
    if any(k in t for k in ["collaborative", "relationship", "win-win"]):
        return "collaborative"
    return "neutral"


def _infer_user_style(text: str) -> str:
    t = _normalize(text)
    if any(k in t for k in ["data", "numbers", "benchmarks", "analysis"]):
        return "data_driven"
    if any(k in t for k in ["relationship", "rapport", "empathy", "diplomatic"]):
        return "relationship_builder"
    if any(k in t for k in ["assertive", "direct", "firm"]):
        return "assertive"
    return "diplomatic"


def _infer_context_level(country: Optional[str]) -> str:
    if not country:
        return "low"
    return "high" if _normalize(country) in HIGH_CONTEXT_COUNTRIES else "low"


def map_questionnaire_to_inputs(answers: Dict[str, Any], schema_map: Dict[str, str] | None = None) -> Dict[str, Any]:
    schema_map = schema_map or {}

    persona_text = (
        answers.get(schema_map.get("q_persona_desc", "q_persona_desc"))
        or answers.get("counterpart_description")
        or answers.get("counterpart_persona")
        or ""
    )

    counterpart_power = (
        answers.get(schema_map.get("q_power", "q_power")) or answers.get("counterpart_power") or "peer"
    ).lower()
    if counterpart_power not in ("high", "peer", "low"):
        counterpart_power = "peer"

    user_style_text = answers.get(schema_map.get("q_user_style", "q_user_style")) or answers.get("user_style") or ""

    target_salary = answers.get(schema_map.get("q_salary_target", "q_salary_target")) or answers.get("target_salary")
    salary_range = answers.get(schema_map.get("q_salary_range", "q_salary_range")) or answers.get("salary_range")

    range_low = None
    range_high = None
    if isinstance(salary_range, (list, tuple)) and len(salary_range) >= 2:
        range_low = _parse_salary_value(salary_range[0])
        range_high = _parse_salary_value(salary_range[1])
    elif isinstance(salary_range, str) and ("-" in salary_range or "–" in salary_range):
        parts = re.split(r"\-|–", salary_range)
        if len(parts) >= 2:
            range_low = _parse_salary_value(parts[0])
            range_high = _parse_salary_value(parts[1])

    benefits = answers.get(schema_map.get("q_benefits", "q_benefits")) or answers.get("benefits") or []
    if not isinstance(benefits, list):
        benefits = _split_list(benefits)

    title = answers.get(schema_map.get("q_title", "q_title")) or answers.get("target_title")

    value_proofs = (
        answers.get(schema_map.get("q_achievements", "q_achievements")) or answers.get("achievements") or []
    )
    if not isinstance(value_proofs, list):
        value_proofs = _split_list(value_proofs)

    batna = answers.get(schema_map.get("q_batna", "q_batna")) or answers.get("batna") or ""
    time_constraints = answers.get(schema_map.get("q_deadline", "q_deadline")) or answers.get("deadline") or ""

    country = answers.get(schema_map.get("q_country", "q_country")) or answers.get("country") or ""
    language = answers.get(schema_map.get("q_language", "q_language")) or answers.get("language") or "en"
    context_level = _infer_context_level(country)

    def _split_any(x: Any) -> List[str]:
        if isinstance(x, list):
            return x
        return _split_list(x)

    prior_offers = _split_any(
        answers.get(schema_map.get("q_prior_offers", "q_prior_offers")) or answers.get("prior_offers") or []
    )
    what_worked = _split_any(
        answers.get(schema_map.get("q_worked", "q_worked")) or answers.get("what_worked") or []
    )
    what_failed = _split_any(
        answers.get(schema_map.get("q_failed", "q_failed")) or answers.get("what_failed") or []
    )

    try:
        risk_raw = answers.get(schema_map.get("q_risk", "q_risk")) or answers.get("risk_tolerance") or 3
        risk = int(risk_raw)
        if not (1 <= risk <= 5):
            risk = 3
    except Exception:
        risk = 3

    priorities = answers.get(schema_map.get("q_priorities", "q_priorities")) or answers.get("priorities") or []
    if not isinstance(priorities, list):
        priorities = _split_list(priorities)

    market_sources = (
        answers.get(schema_map.get("q_market_sources", "q_market_sources"))
        or answers.get("market_sources")
        or DEFAULT_MARKET_SOURCES
    )
    if not isinstance(market_sources, list):
        market_sources = _split_list(market_sources)

    counterpart_persona = answers.get("counterpart_persona") or _infer_persona(persona_text)
    user_style = answers.get("user_style") or _infer_user_style(user_style_text)

    # context keywords for rule triggers
    ctx = set()
    if counterpart_power:
        ctx.add(f"power:{counterpart_power}")
    for p in priorities or []:
        ctx.add(f"prio:{_normalize(p)}")
    if time_constraints:
        ctx.add("deadline")
    if batna:
        ctx.add("batna")
    for src in market_sources:
        ctx.add(f"src:{_normalize(src)}")

    return {
        "counterpart_persona": counterpart_persona,
        "counterpart_power": counterpart_power,
        "user_style": user_style,
        "goals": {
            "monetary": {
                "target_salary": _parse_salary_value(target_salary) or "",
                "range_low": range_low or "",
                "range_high": range_high or "",
            },
            "title": {"target_title": title or ""},
            "benefits": benefits,
        },
        "leverage": {
            "value_proofs": value_proofs,
            "alternatives_BATNA": batna,
            "time_constraints": time_constraints,
        },
        "culture": {
            "country": country,
            "language": language,
            "context_level": context_level,
        },
        "history": {
            "prior_offers": prior_offers,
            "what_worked": what_worked,
            "what_failed": what_failed,
        },
        "risk_tolerance": risk,
        "priorities_ranked": priorities or ["salary", "title", "flexibility"],
        "market_sources": market_sources,
        "context_keywords": sorted(ctx),
    }
