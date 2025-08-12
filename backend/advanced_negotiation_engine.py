# backend/advanced_negotiation_engine.py
# Clean, English-only implementation.
# Purpose: produce a compact plan + reasons + chart_data from a lightweight
# questionnaire/inputs payload, with a stable shape consumed by v2 engine
# and the report builder. No external services are required.

from __future__ import annotations
import os, json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

CurrencyMap = {
    "UK": "£",
    "GB": "£",
    "GBR": "£",
    "US": "$",
    "USA": "$",
    "CA": "$",
    "EU": "€",
    "DE": "€",
    "FR": "€",
    "ES": "€",
    "IT": "€",
}

def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _to_list(v: Any) -> List[str]:
    if v is None: 
        return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str):
        parts = [p.strip() for p in v.replace(";", ",").split(",")]
        return [p for p in parts if p]
    return [str(v)]

def _first_non_empty(*vals: Any, default: str = "") -> str:
    for v in vals:
        s = "" if v is None else str(v).strip()
        if s:
            return s
    return default

def _currency_for(country: str | None) -> str:
    if not country:
        return "£"
    up = country.strip().upper()
    return CurrencyMap.get(up, "£")

@dataclass
class Profile:
    persona: str = "neutral"
    power: str = "peer"
    country: str = "UK"
    context_level: str = "low"
    user_style: str = "Analytical"

@dataclass
class Plan:
    opening_variants: List[str]
    counters: List[str]
    scenarios: List[Dict[str, str]]

class AdvancedNegotiationEngine:
    """Minimal, self-contained v1 engine.
    Returns a dictionary with keys expected by v2:
      - chart_data: { currency, salary: { anchor, low, high } }
      - rules: { matches, recommendations, tone_overrides }
      - reasons: { highlights, tone_reason, rules_matched }
      - debug: { profile, extras }
    """

    def __init__(self, kb: Dict[str, Any] | None = None, data_dir: str | None = None, debug: bool = False):
        self.debug = debug
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "data")
        self.kb = kb or {}
        # Optional files (if present we use them, otherwise fallback silently)
        self.rulebook = _read_json(os.path.join(self.data_dir, "rulebook.json"))
        self.super_kb = _read_json(os.path.join(self.data_dir, "super_kb.json"))

    # --- mapping helpers ----------------------------------------------------
    def _map(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Accept both payloads:
        #   { "questionnaire": {...} }  or  { "inputs": {...} }
        src = payload.get("questionnaire") or payload.get("inputs") or {}
        m: Dict[str, Any] = {}

        m["country"] = _first_non_empty(src.get("country"), "UK")
        m["persona"] = _first_non_empty(src.get("counterpart_persona"), src.get("persona"), "neutral")
        m["user_style"] = _first_non_empty(src.get("communication_style"), src.get("user_style"), "Analytical")
        m["power"] = _first_non_empty(src.get("counterpart_power"), src.get("power"), "peer")
        m["context_level"] = _first_non_empty(src.get("context_level"), "low")

        m["role"] = _first_non_empty(src.get("role"), src.get("target_title"), "Senior Editor")
        m["seniority"] = _first_non_empty(src.get("seniority"), "mid")

        # Numbers are kept as strings to avoid culture issues; UI/HTML will render them.
        m["target_salary"] = _first_non_empty(src.get("target_salary"), src.get("anchor_value"))
        m["range_low"] = _first_non_empty(src.get("range_low"), (src.get("salary_range") or [None, None])[0])
        m["range_high"] = _first_non_empty(src.get("range_high"), (src.get("salary_range") or [None, None])[1])

        m["impacts"] = _to_list(src.get("impacts") or src.get("achievements"))
        m["market_sources"] = _to_list(src.get("market_sources") or ["Glassdoor", "Levels.fyi"])
        m["priorities"] = _to_list(src.get("priorities") or src.get("priorities_ranked"))
        m["primary_objective"] = _first_non_empty(src.get("primary_objective"), "alignment")
        m["risk_tolerance"] = int(src.get("risk_tolerance") or 3)

        return m

    def _build_profile(self, m: Dict[str, Any]) -> Profile:
        return Profile(
            persona=m.get("persona","neutral"),
            power=m.get("power","peer"),
            country=m.get("country","UK"),
            context_level=m.get("context_level","low"),
            user_style=m.get("user_style","Analytical"),
        )

    def _chart_data(self, m: Dict[str, Any]) -> Dict[str, Any]:
        cur = _currency_for(m.get("country"))
        anchor = m.get("target_salary") or ""
        low = m.get("range_low") or None
        high = m.get("range_high") or None
        def _num(x: Optional[str]) -> Optional[float]:
            if x is None: return None
            s = str(x).strip().lower().replace(",", "")
            for sym in ("£","$","€"): s = s.replace(sym,"")
            if not s: return None
            try:
                if s.endswith("k"):
                    return float(s[:-1]) * 1000.0
                return float(s)
            except Exception:
                return None
        return {
            "currency": cur,
            "salary": {
                "anchor": _num(anchor),
                "low": _num(low),
                "high": _num(high),
            }
        }

    def _compose_plan(self, m: Dict[str, Any]) -> Plan:
        cur = _currency_for(m.get("country"))
        anchor = m.get("target_salary") or (m.get("range_high") or "")
        anchor_str = f"{cur}{anchor}" if isinstance(anchor, (int, float)) else (str(anchor) or "your target")

        openings = [
            f"Thanks for the discussion. Based on role and scope, I would like to align around {anchor_str}.",
            "Before numbers, can we confirm success criteria for both sides?",
        ]
        counters = [
            "If budget is tight: propose a path-to-target with a 6-month KPI review.",
            "If title is constrained: secure scope/title note and revisit in 3–6 months.",
        ]
        scenarios = [
            {"id": "lowball", "trigger": "Lowball offer", "reply": "Anchor back near your target, trade scope/timing if needed."},
            {"id": "stall",   "trigger": "Stall or delay", "reply": "Set a clear decision window (e.g., 5 business days)."},
        ]
        return Plan(opening_variants=openings, counters=counters, scenarios=scenarios)

    def _reasons(self, m: Dict[str, Any], plan: Plan) -> Dict[str, Any]:
        highlights = [
            "Lead with facts that matter to an analytical counterpart.",
            "Use an assertive but collaborative tone.",
            "Offer a review path if budget or title is the main constraint.",
        ]
        if m.get("impacts"):
            highlights.insert(0, f"Show 1–2 quantified impacts (e.g., {', '.join(m['impacts'][:2])}).")
        return {
            "highlights": highlights,
            "tone_reason": "Selected for counterpart style and culture fit.",
        }

    # --- public API ----------------------------------------------------------
    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mapped = self._map(payload)
        profile = asdict(self._build_profile(mapped))
        plan = self._compose_plan(mapped)
        reasons = self._reasons(mapped, plan)
        chart = self._chart_data(mapped)

        # Keep shape compatible with v2 and report builder
        rule_out = {"matches": [], "recommendations": [], "tone_overrides": []}

        extras = {
            "inputs_mapped": mapped,
            "plan": asdict(plan),
        }

        return {
            "status": "ok",
            "engine": "v1",
            "chart_data": chart,
            "profile": profile,
            "plan": asdict(plan),
            "reasons": {**reasons, "rules_matched": rule_out.get("matches")},
            "rules": rule_out,                      # available to report
            "debug": {"profile": profile if self.debug else None, "extras": extras if self.debug else None},
        }
