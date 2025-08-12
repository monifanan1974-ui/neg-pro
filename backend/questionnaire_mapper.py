# backend/questionnaire_mapper.py
from __future__ import annotations
import re
from typing import Dict, Any, List, Optional

# very rough list for context-level
HIGH_CONTEXT_COUNTRIES = {
    "japan","china","south korea","korea","greece","italy","spain","portugal","turkey",
    "brazil","mexico","uae","saudi arabia","qatar","egypt","morocco","israel"
}
DEFAULT_MARKET_SOURCES = ["Glassdoor","Levels.fyi"]

def _normalize(s: Optional[str]) -> str:
    if s is None: return ""
    if not isinstance(s, str): s = str(s)
    return re.sub(r"\s+", " ", s.strip().lower())

def _split_list(x: Any) -> List[str]:
    if x is None: return []
    if isinstance(x, list): return [str(i).strip() for i in x if str(i).strip()]
    s = str(x)
    if "," in s: return [i.strip() for i in s.split(",") if i.strip()]
    return [s.strip()] if s.strip() else []

def _parse_salary_value(x: Any) -> Optional[float]:
    """Accepts '78000', '78k', '£78k', '78,000' -> float"""
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    s = _normalize(str(x)).replace("£","").replace(",", "")
    m = re.findall(r"[\d\.]+", s)
    if not m: return None
    v = float(m[0])
    if s.endswith("k"): v *= 1000.0
    return v

# ---------- Inference helpers (improved to catch your inputs) ----------

def _infer_persona(text: str) -> str:
    t = _normalize(text)
    # Common labels / synonyms
    if "collaborator" in t or "collaborative" in t or "win-win" in t: return "The Collaborator"
    if "friend" in t: return "The Friend"
    if any(k in t for k in ["aggressive","hardball","pushy","dominating","dominator"]): return "The Dominator"
    if any(k in t for k in ["skeptic","need proof","doubt","prove"]): return "The Analyst"
    if any(k in t for k in ["urgent","deadline","time pressure","asap"]): return "The Expediter"
    if any(k in t for k in ["budget","tight budget","budget constraint"]): return "The Gatekeeper"
    return "neutral"

def _infer_user_style(text: str) -> str:
    t = _normalize(text)
    # catch 'analytical' / 'analytic' too (your demo uses "Analytical")
    if any(k in t for k in ["data","numbers","benchmarks","analysis","analytic","analytical","analyt"]):
        return "Analytical"
    if any(k in t for k in ["relationship","rapport","empathy","diplomatic"]):
        return "Diplomatic"
    if any(k in t for k in ["assertive","direct","firm"]):
        return "Assertive"
    return "Diplomatic"

def _infer_context_level(country: Optional[str]) -> str:
    if not country: return "low"
    return "high" if _normalize(country) in HIGH_CONTEXT_COUNTRIES else "low"

# ---------- Main mapper ----------

def map_questionnaire_to_inputs(answers: Dict[str, Any], schema_map: Dict[str, str] | None = None) -> Dict[str, Any]:
    """
    Convert raw questionnaire answers into a normalized structure that the engine expects.
    schema_map lets you rename question IDs (right now your demo uses q_* IDs).
    """
    schema_map = schema_map or {}

    # Read raw fields from either schema_map IDs or direct keys
    persona_text = answers.get(schema_map.get("q_persona_desc","q_persona_desc")) or \
                   answers.get("counterpart_description") or \
                   answers.get("counterpart_persona") or ""

    power_raw = answers.get(schema_map.get("q_power","q_power")) or \
                answers.get("counterpart_power") or "peer"

    user_style_text = answers.get(schema_map.get("q_user_style","q_user_style")) or \
                      answers.get("user_style") or ""

    target_salary = answers.get(schema_map.get("q_salary_target","q_salary_target")) or \
                    answers.get("target_salary")

    salary_range = answers.get(schema_map.get("q_salary_range","q_salary_range")) or \
                   answers.get("salary_range")

    country = answers.get(schema_map.get("q_country","q_country")) or \
              answers.get("country") or "UK"

    # optional / nice-to-have
    benefits = answers.get(schema_map.get("q_benefits","q_benefits")) or answers.get("benefits") or []
    if not isinstance(benefits, list): benefits = _split_list(benefits)

    title = answers.get(schema_map.get("q_title","q_title")) or answers.get("target_title")

    value_proofs = answers.get(schema_map.get("q_achievements","q_achievements")) or answers.get("achievements") or []
    if not isinstance(value_proofs, list): value_proofs = _split_list(value_proofs)

    prior_offers = answers.get(schema_map.get("q_prior_offers","q_prior_offers")) or \
                   answers.get("prior_offer_status") or ""

    what_failed = answers.get(schema_map.get("q_failed","q_failed")) or \
                  answers.get("current_challenges") or []

    market_sources = answers.get(schema_map.get("q_market_sources","q_market_sources")) or \
                     answers.get("market_data_sources") or DEFAULT_MARKET_SOURCES
    if not isinstance(market_sources, list): market_sources = _split_list(market_sources)

    risk = answers.get(schema_map.get("q_risk","q_risk")) or answers.get("anxiety_rating") or 3
    try:
        risk = int(risk)
    except Exception:
        risk = 3

    # Priorities (accept array or CSV)
    priorities_raw = answers.get(schema_map.get("q_priorities","q_priorities")) or answers.get("priorities_ranked") or []
    if not isinstance(priorities_raw, list): priorities = _split_list(priorities_raw)
    else: priorities = [str(x).strip() for x in priorities_raw if str(x).strip()]

    # Parse range
    range_low, range_high = None, None
    if isinstance(salary_range, (list, tuple)) and len(salary_range) >= 2:
        range_low, range_high = _parse_salary_value(salary_range[0]), _parse_salary_value(salary_range[1])
    elif isinstance(salary_range, str) and ("-" in salary_range or "–" in salary_range):
        parts = re.split(r"\-|–", salary_range)
        if len(parts) >= 2:
            range_low, range_high = _parse_salary_value(parts[0]), _parse_salary_value(parts[1])

    # --- Final normalized fields ---
    # persona: prefer explicit text, else infer
    counterpart_persona = answers.get("counterpart_persona") or (persona_text if persona_text else _infer_persona(persona_text))
    # power normalize
    counterpart_power = _normalize(power_raw)
    if counterpart_power not in ("high","peer","low"): counterpart_power = "peer"
    # user style: prefer explicit text, else infer
    user_style = answers.get("user_style") or (user_style_text if user_style_text else _infer_user_style(user_style_text))

    # Context keywords for the rule engine (help it match)
    ctx = set()
    if counterpart_persona: ctx.add(f"persona:{_normalize(counterpart_persona)}")
    if counterpart_power: ctx.add(f"power:{counterpart_power}")
    if user_style: ctx.add(f"style:{_normalize(user_style)}")
    for src in market_sources: ctx.add(f"src:{_normalize(src)}")
    if risk and int(risk) >= 4: ctx.add("risk:high")

    # Build the normalized dict
    mapped: Dict[str, Any] = {
        "counterpart_persona": counterpart_persona,
        "counterpart_power": counterpart_power,
        "user_style": user_style,
        "goals": {
            "monetary": {
                "target_salary": _parse_salary_value(target_salary) or "",
                "range_low": range_low or "",
                "range_high": range_high or ""
            },
            "non_monetary": {
                "benefits": benefits or []
            }
        },
        "leverage": {
            "value_proofs": value_proofs or [],
            "alternatives_BATNA": answers.get("batna") or "",
            "time_constraints": answers.get("deadline") or answers.get(schema_map.get("q_deadline","q_deadline")) or ""
        },
        "role": title or "",
        "culture": {
            "country": country,
            "language": answers.get("language") or "en",
            "context_level": _infer_context_level(country)
        },
        "history": {
            "prior_offers": prior_offers,
            "what_worked": answers.get("what_worked") or [],
            "what_failed": what_failed or []
        },
        "risk_tolerance": risk,
        "priorities_ranked": priorities or ["salary","title","flexibility"],
        "market_sources": market_sources,
        "context_keywords": sorted(ctx)
    }
    return mapped
