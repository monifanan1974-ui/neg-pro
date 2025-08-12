# backend/market_intel.py
# Pulls impact bullets, normalizes salary ranges, ensures multiple sources, emits warnings.

import os, json, re
from typing import Dict, Any, List, Tuple

def _safe_load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _norm_amount(s: str) -> str:
    return (s or "").strip().replace(" ", "")

def _parse_amount(s: str):
    if not s: return None
    t = s.replace(",", "").replace("$","").replace("€","").replace("£","").lower()
    t = t.replace("k","000")
    try: return float(t)
    except: return None

def _fmt_amount(v: float, symbol: str="£") -> str:
    if v is None: return ""
    v = int(round(v, -2))
    if v % 1000 == 0: return f"{symbol}{int(v/1000)}k"
    return f"{symbol}{v:,}"

def infer_market_range(local_data: dict, role: str, country: str) -> Tuple[str,str,dict]:
    roles = ((local_data or {}).get("comp_benchmarks", {}) or {}).get("roles", {})
    key = f"{role}|{country}"
    row = roles.get(key)
    if row:
        return _norm_amount(str(row.get("p25"))), _norm_amount(str(row.get("p75"))), {"source":"local-data.json","quality":0.75}
    return "", "", {"source":"none","quality":0.0}

class MarketIntel:
    def __init__(self, data_dir: str):
        self.local = _safe_load(os.path.join(data_dir, "local-data.json"))
        self.validation = _safe_load(os.path.join(data_dir, "data-validation.json"))

    def build(self, inputs: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        # impacts
        impacts: List[str] = inputs.get("impacts") or []
        if not impacts:
            # try to parse a simple CSV text like: "Reduced cycle 28%, 12 on-time campaigns"
            raw = inputs.get("achievements_text") or ""
            parts = [p.strip() for p in re.split(r"[;,]", raw) if p.strip()]
            impacts = parts[:3]
        if not impacts:
            impacts = ["[impact #1]", "[impact #2]"]  # placeholders

        # ensure 2 sources minimum
        sources = inputs.get("market_sources") or ["Glassdoor","Levels.fyi"]
        if len(sources) < 2:
            sources.append("BLS/Industry report")

        # salary range
        lo = _norm_amount(inputs.get("range_low") or "")
        hi = _norm_amount(inputs.get("range_high") or "")
        if not lo and not hi:
            lo, hi, meta = infer_market_range(self.local, inputs.get("role") or inputs.get("target_title") or "", profile.get("country") or "UK")
        else:
            meta = {"source":"user","quality":0.6}

        warnings = []
        for rule in (self.validation.get("validation_rules") or []):
            if rule.get("id") == "VR001" and len(sources)==1 and sources[0].lower()=="glassdoor":
                warnings.append(rule.get("message"))
            if rule.get("id") == "VR002" and (not lo and not hi):
                warnings.append("No salary range provided — cross-check with BLS/Levels.fyi/industry reports.")

        return {
            "impacts": impacts,
            "sources": list(dict.fromkeys(sources)),
            "range_low": lo,
            "range_high": hi,
            "meta": meta,
            "warnings": warnings
        }

    @staticmethod
    def numeric_anchor(range_low: str, range_high: str, target: str, persona: str, risk: int, symbol: str="£"):
        lo = _parse_amount(range_low); hi = _parse_amount(range_high); tg = _parse_amount(target)
        base = tg if tg is not None else ((lo + hi)/2.0 if lo and hi else (lo or hi))
        if base is None: return "I’m targeting within that range.", None
        persona_l = (persona or "").lower()
        premium = 0.0
        if "dominator" in persona_l: premium = 0.04
        elif "analyst" in persona_l: premium = 0.01
        elif "friend" in persona_l or "fox" in persona_l: premium = 0.02
        premium += (max(1, min(5, risk)) - 3) * 0.01
        anchor_val = base * (1.0 + premium)
        tail = f"I’m targeting {_fmt_amount(anchor_val, symbol)} within that."
        return tail, _fmt_amount(anchor_val, symbol)

