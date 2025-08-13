--- START OF FILE backend/engine_entrypoint.py ---
# backend/engine_entrypoint.py
# Questionnaire → Engine glue.
# Maps answers using questionnaire_mapper, evaluates rules, and builds the HTML report.
from __future__ import annotations
import os, json, traceback, re
from typing import Dict, Any, Optional

# Use relative imports with '.' for modules within the same package
from .questionnaire_mapper import map_questionnaire_to_inputs
from .rule_engine_expansion import RuleEngineExpansion
from .report_builder import build_report_html

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA_DIR = os.path.join(ROOT, "data")

def _load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        traceback.print_exc()
        return {}

_num_re = re.compile(r"[\d\.]+")
def _to_num(x) -> Optional[float]:
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    s = str(x)
    m = _num_re.findall(s.replace(",", ""))
    if not m: return None
    try:
        return float(m[0])
    except Exception:
        return None

def _calc_readiness(mapped: Dict[str, Any]) -> int:
    score = 40
    if ((mapped.get("leverage") or {}).get("alternatives_BATNA")): score += 25
    ms = mapped.get("market_sources") or []
    score += min(20, max(0, (len(ms) - 1) * 10))
    proofs = (mapped.get("leverage") or {}).get("value_proofs") or []
    if len(proofs) >= 2: score += 15
    elif proofs: score += 7
    if ((mapped.get("leverage") or {}).get("time_constraints")): score += 5
    return max(35, min(95, score))

def _profile_slice(mapped: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "persona": (mapped.get("counterpart_persona") or "neutral"),
        "country": (mapped.get("culture") or {}).get("country") or "UK",
        "context_level": (mapped.get("culture") or {}).get("context_level") or "low",
        "power": mapped.get("counterpart_power") or "peer",
        "user_style": mapped.get("user_style") or "Analytical"
    }

def _metrics_from_mapped(mapped: Dict[str, Any]) -> Dict[str, Any]:
    m = (mapped.get("goals") or {}).get("monetary") or {}
    low = _to_num(m.get("range_low"))
    high = _to_num(m.get("range_high"))
    anchor = _to_num(m.get("target_salary"))
    # If only low/high exist, pick anchor near high (p75)
    if anchor is None and (low is not None or high is not None):
        anchor = high or low
    return {"range_low": low, "range_high": high, "anchor_value": anchor}

class QuestionnaireEngine:
    def __init__(self, kb_path: Optional[str] = None, schema_map_path: Optional[str] = None, debug: bool = False):
        self.debug = debug
        kb_path = kb_path or os.path.join(DATA_DIR, "super_kb.json")
        self.kb = _load_json(kb_path)
        self.rules = self.kb
        self.schema_map_path = schema_map_path or os.path.join(DATA_DIR, "schema_map.v127.json")

    def _load_schema_map(self) -> Dict[str, str]:
        m = _load_json(self.schema_map_path)
        return m if isinstance(m, dict) else {}

    def run(self, raw_answers: Dict[str, Any]) -> Dict[str, Any]:
        try:
            schema_map = self._load_schema_map()
            mapped = map_questionnaire_to_inputs(raw_answers or {}, schema_map=schema_map)

            # Evaluate rules (recommendations + tone overrides)
            rexp = RuleEngineExpansion(rules_data=self.rules, kb_root=self.kb)
            fired = rexp.evaluate_all(mapped)

            # Priorities / readiness
            priorities = (mapped.get("priorities_ranked") or ["salary","title","flexibility"])[:3]
            priorities = [str(x).strip().title() for x in priorities]
            readiness = _calc_readiness(mapped)

            # Build an engine_out object that report_builder expects
            engine_out = {
                "debug": {"profile": _profile_slice(mapped)},
                "answers": mapped,                 # so report builder can snapshot context
                "metrics": _metrics_from_mapped(mapped)  # for charts/market merge
            }

            rep = build_report_html(engine_out, extras={
                "priorities": priorities,
                "readiness": readiness,
                "fired_rules": fired
            })
            return {
                "status": "ok",
                "engine": "qengine",
                "html": rep.get("html"),
                "chart_data": rep.get("chart_data"),
                "rules_fired": fired,
                "profile": engine_out["debug"]["profile"]
            }
        except Exception as e:
            if self.debug:
                traceback.print_exc()
            return {"status": "error", "reason": f"{type(e).__name__}: {e}"}
