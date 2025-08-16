<<<<<<< HEAD
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
=======
# backend/engine_entrypoint.py
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# --------------------------
# Utility & domain helpers
# --------------------------

def _to_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(float(x))
    except Exception:
        return None

def _as_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(s).strip() for s in x if str(s).strip()]
    return [s.strip() for s in str(x).split(",") if s.strip()]

def _derive_range(low: Optional[int], high: Optional[int]) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    Returns p25, median, p75, anchor, floor from low/high.
    Anchor is slightly above p75; floor slightly below low.
    """
    if not (isinstance(low, int) and isinstance(high, int) and high >= low and low > 0):
        return None, None, None, None, None
    gap = max(1, high - low)
    p25    = round(low + 0.25 * gap)
    median = round(low + 0.50 * gap)
    p75    = round(low + 0.75 * gap)
    anchor = round(p75 + 0.07 * gap)
    floor  = round(low - 0.05 * gap)
    return p25, median, p75, anchor, floor

# --------------------------
# Knowledge (lightweight)
# --------------------------

PERSONA_LIBRARY: Dict[str, Dict[str, Any]] = {
    # keep labels simple; you can expand later
    "analytical": {
        "principles": [
            "Lead with evidence and quantified outcomes",
            "Structure the conversation and preview the agenda",
            "Ask clarifying questions to expose constraints"
        ],
        "tactics": [
            "Present 2–3 proof points tied to business KPIs",
            "Use ranges, not single numbers, to anchor rationally",
            "Summarize decisions and next steps in writing"
        ],
        "opening_template": "Based on market data for {role} in {industry}, I'm targeting {target} given my impact on {impact_one}. I'd like to walk through the data and agree on a path that works for both of us.",
        "concessions": [
            "Title calibration with earlier review",
            "Variable/bonus increase tied to clear metrics",
            "Learning budget or conference sponsorship",
            "Flexible work or scope adjustments"
        ]
    },
    "collaborator": {
        "principles": [
            "Make the shared goal explicit",
            "Trade creatively (multi-issue bargaining)",
            "Surface non-monetary value early"
        ],
        "tactics": [
            "Frame proposals as mutual wins",
            "Bundle salary with growth and scope",
            "Offer give-gets, not unilateral concessions"
        ],
        "opening_template": "I’m excited about the impact we can create. If we align on {target} for base, I can commit to {impact_one} in the first quarter and {impact_two} by mid-year.",
        "concessions": [
            "Earlier performance review",
            "Defined growth plan with milestones",
            "Mentorship or team leadership scope"
        ]
    },
    "assertive": {
        "principles": [
            "Project confidence and clarity",
            "Set firm anchors backed by data",
            "Control pacing with explicit deadlines"
        ],
        "tactics": [
            "Lead with the anchor and rationale",
            "Use silence strategically after proposals",
            "Name your BATNA without threatening"
        ],
        "opening_template": "Given my results in {impact_one} and the current market for {role}, I’m anchoring at {anchor}. I’m confident we can land this if we move swiftly.",
        "concessions": [
            "Signing or retention bonus",
            "Scope/OKR alignment to accelerate raises",
            "Defined promotion checkpoint"
        ]
    },
    "cunning": {  # left for compatibility with your screenshot
        "principles": [
            "Gather hidden constraints before proposing",
            "Sequence asks to build momentum",
            "Control information timing"
        ],
        "tactics": [
            "Probe for decision criteria and veto holders",
            "Float exploratory ranges to test reactions",
            "Stack small yeses before the main ask"
        ],
        "opening_template": "Before numbers, I’d like to confirm decision criteria. Then I’ll outline a plan where {target} makes sense given {impact_one}.",
        "concessions": [
            "Staged increases tied to outcomes",
            "Project ownership",
            "Visibility (presentations/credits)"
        ]
    }
}

def _pick_persona(label: str) -> Dict[str, Any]:
    key = (label or "").strip().lower().replace("the ", "")
    return PERSONA_LIBRARY.get(key) or PERSONA_LIBRARY["analytical"]

# --------------------------
# Market data hook (stub)
# --------------------------

def fetch_market_snapshot(industry: str, role: str, country: str) -> Dict[str, Any]:
    """
    Hook to plug real market data (DB/API).
    For now, returns a light hint so the engine works offline.
    Replace this with your integration later.
    """
    hint = {
        "source": "internal-stub",
        "samples": 126,
        "currency": "USD" if country.upper() in ("US","USA") else "EUR",
        "latency_ms": 4
    }
    return hint

# --------------------------
# Renderer
# --------------------------

def _render_html(ctx: Dict[str, Any]) -> str:
    """
    Returns a premium, self-contained HTML fragment
    (the outer shell + modal buttons already handled in backend/app.py).
    """
    chips = "".join(f"<span class='chip'>{x}</span>" for x in ctx["chips"])
    pr_list = "".join(f"<li>{p}</li>" for p in ctx["persona"]["principles"])
    tc_list = "".join(f"<li>{t}</li>" for t in ctx["persona"]["tactics"])
    hi_list = "".join(f"<li>{h}</li>" for h in ctx["highlights"])

    # Market range bars (hide row if missing)
    def _row(label: str, value: Optional[int]) -> str:
        if value is None or ctx["low"] is None or ctx["high"] is None or ctx["high"] == ctx["low"]:
            return f"<div class='row'><div class='pill'>{label}</div><div class='bar'><div class='fill k' data-p='0'></div></div><div class='pill'>—</div></div>"
        p = (value - ctx["low"]) / float(ctx["high"] - ctx["low"])
        return f"<div class='row'><div class='pill'>{label}</div><div class='bar'><div class='fill k' data-p='{max(0,min(1,p))}'></div></div><div class='pill'>{value:,}</div></div>"

    market_block = ""
    if any(ctx[k] is not None for k in ("p25","median","p75","anchor","floor")):
        market_block = f"""
        <section class="section">
          <h3>Market Range</h3>
          <div class="list">
            {_row('p25', ctx['p25'])}
            {_row('median', ctx['median'])}
            {_row('p75', ctx['p75'])}
            {_row('anchor', ctx['anchor'])}
            {_row('floor', ctx['floor'])}
          </div>
          <div class="meta" style="margin-top:.5rem">source: {ctx['market']['source']} • samples: {ctx['market']['samples']} • currency: {ctx['market']['currency']}</div>
        </section>
        """

    concessions = "".join(f"<li>{c}</li>" for c in ctx["persona"]["concessions"])
    achievements = "".join(f"<li>{a}</li>" for a in ctx["impact"])

    opening = ctx["persona"]["opening_template"].format(
        role=ctx["role"],
        industry=ctx["industry"],
        target=f"{ctx['target']:,}" if ctx["target"] else "the target",
        impact_one=ctx["impact"][0] if ctx["impact"] else "impact delivered",
        impact_two=(ctx["impact"][1] if len(ctx["impact"]) > 1 else "team outcomes")
    )

    return f"""
      <h1>Strategic Negotiation Report</h1>
      <div class="meta">{ctx['country'] or '—'} • {ctx['date']} • Persona: {ctx['persona_key']}</div>

      <div class="grid">
        <div>
          {market_block}
        </div>
        <div>
          <section class="section">
            <h3>Highlights</h3>
            <ul>{hi_list}</ul>
            <div class="chips">{chips}</div>
          </section>
          <section class="section">
            <h3>Core Principles</h3>
            <ul>{pr_list}</ul>
          </section>
          <section class="section">
            <h3>Key Tactics</h3>
            <ul>{tc_list}</ul>
          </section>
        </div>
      </div>

      <section class="section">
        <h3>Opening Script</h3>
        <p>{opening}</p>
      </section>

      <section class="section">
        <h3>Concessions (Give-Gets)</h3>
        <ul>{concessions}</ul>
      </section>

      <section class="section">
        <h3>Achievements to Spotlight</h3>
        <ul>{achievements or '<li>Add 2–3 quantified proof points</li>'}</ul>
      </section>

      <details class="section"><summary>Debug Snapshot</summary>
        <div class="card" style="margin-top:8px">
          <table><thead><tr><th>Id</th><th>Value</th></tr></thead><tbody>
            {''.join(f"<tr><td>{k}</td><td>{json.dumps(v, ensure_ascii=False)}</td></tr>" for k,v in ctx["answers"].items())}
          </tbody></table>
        </div>
      </details>
    """

# --------------------------
# Engine class (public API)
# --------------------------

@dataclass
class QuestionnaireEngine:
    debug: bool = False

    # ---- public entrypoint ----
    def run(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input:
          answers: dict from the SPA stepper or the mini-form.
        Output (either one is fine):
          {"status":"ok","html":"<...>"}  OR  {"status":"ok","sections":[...]}
        """
        try:
            ctx = self._build_context(answers)
            html = _render_html(ctx)
            return {"status": "ok", "html": html}
        except Exception as e:
            if self.debug:
                raise
            return {"status": "error", "reason": str(e)}

    # ---- internal: normalization & context ----
    def _build_context(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        answers = raw or {}

        industry = str(answers.get("industry", "General"))
        role     = str(answers.get("role", "Professional"))
        country  = str(answers.get("country", ""))
        persona_key = (answers.get("persona") or "analytical")
        tone     = str(answers.get("tone", "neutral"))

        priorities = _as_list(answers.get("priorities"))
        impact     = _as_list(answers.get("impact"))

        low    = _to_int(answers.get("salary_low"))
        high   = _to_int(answers.get("salary_high"))
        target = _to_int(answers.get("salary_target"))

        p25, median, p75, anchor, floor = _derive_range(low, high)
        persona = _pick_persona(str(persona_key))

        # Highlights, personalized
        highlights: List[str] = []
        if target and p75 and target >= p75:
            highlights.append("Anchor near the 75th percentile using two quantified proof points")
        elif target and median and target >= median:
            highlights.append("Anchor slightly above the median with evidence")
        else:
            highlights.append("Anchor with data-backed rationale and trade across issues")

        if priorities:
            highlights.append(f"Prioritize: {', '.join(priorities[:3])}")
        if impact:
            highlights.append("Open with recent quantified outcomes")

        market = fetch_market_snapshot(industry, role, country)

        chips = [persona_key, country or "—", tone]

        ctx = {
            "date": datetime.utcnow().strftime("%m/%d/%Y"),
            "answers": answers,
            "industry": industry,
            "role": role,
            "country": country,
            "persona_key": persona_key,
            "tone": tone,
            "priorities": priorities,
            "impact": impact,
            "low": low,
            "high": high,
            "target": target,
            "p25": p25,
            "median": median,
            "p75": p75,
            "anchor": anchor,
            "floor": floor,
            "persona": persona,
            "market": market,
            "chips": chips,
            "highlights": highlights,
        }
        return ctx
>>>>>>> 761b083 (Your commit message here)
