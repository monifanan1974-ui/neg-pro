# backend/advanced_negotiation_engine.py
# V3 – Super KB + Advanced Rule Engine integration

import json
import os
from typing import Any, Dict, List, Tuple


from persona_profiler import PersonaProfiler
from market_intel import MarketIntel
from simulation_manager import SimulationManager
from tactic_composer import TacticComposer
from rule_engine_expansion import RuleEngineExpansion

# Use relative imports for modules within the same package
from .persona_profiler import PersonaProfiler
from .market_intel import MarketIntel
from .simulation_manager import SimulationManager
from .tactic_composer import TacticComposer
from .rule_engine_expansion import RuleEngineExpansion

try:
    import openai  # noqa: F401
    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False


def _safe_load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _fmt_range(lo: str, hi: str) -> str:
    lo = (lo or "").strip()
    hi = (hi or "").strip()
    if lo and hi:
        return f"{lo}–{hi}"
    return lo or hi or "a market-aligned range"


def _to_list(x):
    return x if isinstance(x, list) else ([x] if x else [])


class AdvancedNegotiationEngine:
    def __init__(self, kb: Dict[str, Any] | None = None, data_dir: str | None = None, debug: bool = False):
        self.debug = bool(debug)
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

        if kb is None:
            self.kb = {}
            if os.path.isdir(self.data_dir):
                for f in os.listdir(self.data_dir):
                    if f.lower().endswith(".json"):
                        self.kb[f] = _safe_load(os.path.join(self.data_dir, f))
        else:
            self.kb = kb

        self.super_kb = self.kb.get("super_kb.json") or _safe_load(os.path.join(self.data_dir, "super_kb.json"))

        self.profiler = PersonaProfiler(self.data_dir)
        self.market = MarketIntel(self.data_dir)
        self.tactic_composer = TacticComposer(self.kb)

        playlets_data = self.kb.get("simulation-playlets.json", {})
        dilemmas_data = self.kb.get("user-dilemmas.json", {})
        self.simulation_manager = SimulationManager(playlets_data, dilemmas_data)

        self.rules = RuleEngineExpansion(self.super_kb, self.super_kb)

    # ---------- Stage A: Collect & Enrich ----------
    def collect_and_enrich(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        answers = payload.get("answers") or {}
        return {
            "industry": answers.get("industry"),
            "role": answers.get("role") or answers.get("target_title"),
            "seniority": answers.get("seniority") or "mid",
            "country": answers.get("country") or "UK",
            "communication_style": answers.get("communication_style") or answers.get("user_style"),
            "counterpart_persona": answers.get("counterpart_persona"),
            "challenges": _to_list(answers.get("challenges")),
            "personality_tone": payload.get("tone") or "neutral",
            "impacts": _to_list(answers.get("impacts")),
            "market_sources": _to_list(answers.get("market_sources")) or ["Glassdoor", "Levels.fyi"],
            "range_low": answers.get("range_low") or (answers.get("salary_range") or [None, None])[0] or "",
            "range_high": answers.get("range_high") or (answers.get("salary_range") or [None, None])[1] or "",
            "target_salary": answers.get("target_salary") or answers.get("anchor_value") or "",
            # rule context:
            "risk_tolerance": answers.get("risk_tolerance", 3),
            "primary_objective": answers.get("primary_objective", ""),
            "loss_aversion": answers.get("loss_aversion", False),
            "stalling": answers.get("stalling", False),
            "decision_delay_days": answers.get("decision_delay_days", 0),
            "user_style": answers.get("communication_style") or "",
        }

    # ---------- Stage B: Persona ----------
    def build_persona(self, enriched: Dict[str, Any]) -> Dict[str, Any]:
        return self.profiler.build(enriched)

    # ---------- Stage C: Market + Plan ----------
    def _currency_symbol(self, country_code: str) -> str:
        cc = (country_code or "").upper()
        if cc in ("UK", "GB", "ENGLAND"):
            return "£"
        if cc in ("US", "USA"):
            return "$"
        return "€"

    def build_core_plan(self, enriched: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        intel = self.market.build(enriched, profile)
        symbol = self._currency_symbol(profile.get("country"))
        tail, anchor_val = self.market.numeric_anchor(
            intel["range_low"],
            intel["range_high"],
            enriched.get("target_salary"),
            persona=profile["persona"],
            risk=enriched.get("risk_tolerance", 3),
            symbol=symbol,
        )
        rng = _fmt_range(intel["range_low"], intel["range_high"])
        sources = ", ".join(intel["sources"])
        proofs = ", ".join(intel["impacts"]) if intel["impacts"] else "recent measurable results"

        base_opening = (
            "Before we dive into specifics, I want to make sure we’re aligned on a shared goal: "
            "a solution that works for both sides over the long term. From your perspective, what would a successful outcome look like?"
        )
        anchor_text = (
            f"Based on current market data ({sources}) and my delivered results ({proofs}), "
            f"a range of {rng} is standard. {tail}"
        )

        plan = {
            "posture": "Controlled Assertiveness",
            "opening": base_opening,
            "anchor": anchor_text,
            "pivot": "Let’s align on scope, title, and compensation first; then we can revisit perks.",
            "opening_variants": {
                "soft": base_opening.replace(
                    "I want to make sure we’re aligned on a shared goal:", "Would you be open to aligning on a shared goal?"
                ),
                "neutral": base_opening,
                "firm": base_opening.replace(
                    "I want to make sure we’re aligned on a shared goal:", "I want to be clear on a shared goal:"
                ),
            },
        }
        meta_reasons = {
            "range_reason": "Based on user-provided data."
            if enriched.get("range_low")
            else "Inferred from local market data as no user range was provided.",
            "anchor_reason": f"Anchor tuned to persona '{profile.get('persona','default')}' and risk tolerance.",
        }
        return {"intel": intel, "plan": plan, "meta": {"range": rng, "anchor_value": anchor_val}}, meta_reasons

    # ---------- Stage D: Rules ----------
    def _apply_rules(self, enriched: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        ctx = {
            "counterpart_persona": (profile.get("persona") or "").split(" (")[0],
            "risk_tolerance": enriched.get("risk_tolerance", 3),
            "culture": profile.get("culture"),
            "country": profile.get("country"),
            "user_style": enriched.get("user_style") or profile.get("decision_style", ""),
            "primary_objective": enriched.get("primary_objective", ""),
            "loss_aversion": bool(enriched.get("loss_aversion", False)),
            "stalling": bool(enriched.get("stalling", False)),
            "decision_delay_days": int(enriched.get("decision_delay_days", 0)),
        }
        return self.rules.evaluate_all(ctx)

    def _merge_rule_output(self, plan: Dict[str, Any], rule_out: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        recs = rule_out.get("recommendations") or []
        extra_openers: List[str] = []
        micro_tactics: List[Dict[str, str]] = []
        bias_tips: List[str] = []
        psych_tips: List[str] = []

        for item in recs:
            if not isinstance(item, dict):
                continue
            if "best_openers" in item and isinstance(item["best_openers"], list):
                extra_openers.extend([str(x) for x in item["best_openers"]])
            if item.get("id") and item.get("text"):
                micro_tactics.append({"id": item["id"], "how_to_use": item["text"], "why": item.get("why", "")})
            if item.get("mitigation"):
                bias_tips.extend([str(x) for x in item["mitigation"]])
            if item.get("recommended_actions"):
                psych_tips.extend([str(x) for x in item["recommended_actions"]])

        tone = profile.get("tone") or "neutral"
        for t in rule_out.get("tone_overrides", []):
            tone = t
            break

        culture = profile.get("culture")
        cult_advices: List[str] = []
        if self.super_kb.get("culture_advice") or {}:
            if culture == "high":
                cult_advices = _to_list((self.super_kb["culture_advice"]).get("high_context"))
            else:
                cult_advices = _to_list((self.super_kb["culture_advice"]).get("low_context"))

        return {
            "extra_openers": extra_openers[:3],
            "micro_from_rules": micro_tactics[:4],
            "bias_tips": bias_tips[:4],
            "psych_tips": psych_tips[:4],
            "tone_override": tone,
            "culture_tips": cult_advices[:3],
        }

    # ---------- Stage F: Final (Markdown) ----------
    def _render_markdown(
        self,
        profile: Dict[str, Any],
        plan: Dict[str, Any],
        extras: Dict[str, Any],
        core_meta: Dict[str, Any],
        intel: Dict[str, Any],
    ) -> str:
        p = profile
        pl = plan

        def bullets(arr):
            return "\n".join([f"- {x}" for x in (arr or [])]) or "- (none)"

        micro_lines = []
        for m in extras.get("micro_from_rules") or []:
            line = f"**{m.get('id','TACTIC')}** — {m.get('how_to_use','')}"
            if m.get("why"):
                line += f" _(why: {m['why']})_"
            micro_lines.append(line)

        openers = [pl["opening"]] + (extras.get("extra_openers") or [])
        opening_block = "\n".join([f"- {x}" for x in openers])

        md = f"""# Counterpart Psychological Profile
- **Persona:** {p.get('persona','-')}
- **Culture:** {p.get('culture','-')}
- **Decision Style:** {p.get('decision_style','-')}
- **Motivations:** {", ".join(p.get('motivations', []))}
- **Fears:** {", ".join(p.get('fears', []))}

# Your Strategic Game Plan
- **Overall Posture:** {'Value Articulator' if 'Friend' in p.get('persona','') else 'Controlled Assertiveness'}
- **Anchor:** {pl.get('anchor')}
- **Pivot:** {pl.get('pivot')}

**Opening options (tone={extras.get('tone_override','neutral')}):**
{opening_block}

# Power Micro-Tactics (AI-picked)
{bullets(micro_lines)}

# Bias Management (targeted)
{bullets(extras.get('bias_tips'))}

# Psychology Actions (why this works)
{bullets(extras.get('psych_tips'))}

# Culture Fit Tips
{bullets(extras.get('culture_tips'))}

# Meta
- **Market Range:** {core_meta.get('range')}
- **Anchor Value:** {core_meta.get('anchor_value')}
"""
        return md.strip()

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        enriched = self.collect_and_enrich(payload)
        profile = self.build_persona(enriched)

        base, reasons = self.build_core_plan(enriched, profile)
        intel = base["intel"]
        plan = base["plan"]
        core_meta = base["meta"]

        rule_out = self._apply_rules(enriched, profile)
        extras = self._merge_rule_output(plan, rule_out, profile)

        tone = extras.get("tone_override") or profile.get("tone") or enriched.get("personality_tone", "neutral")
        if tone in plan.get("opening_variants", {}):
            plan["opening"] = plan["opening_variants"][tone]

        md = self._render_markdown(profile, plan, extras, core_meta, intel)

        return {
            "status": "success",
            "format": "md",
            "card": md,
            "ui_payload": {
                "openings": plan.get("opening_variants"),
                "scenarios": [
                    {
                        "id": "lowball",
                        "trigger": "Lowball offer",
                        "reply": "I appreciate the offer. It may help if I clarify unique value — e.g., [impact #1], [impact #2] — since we may be valuing scope differently.",
                    },
                    {
                        "id": "stall",
                        "trigger": "Stall / Delay",
                        "reply": "I understand careful consideration. Could we align a 5-business-day decision window?",
                    },
                ],
            },
            "reasons": {**reasons, "rules_matched": rule_out.get("matches"), "tone_reason": "Tone selected by AI triggers and culture fit."},
            "rules": rule_out,
            "debug": {"profile": profile if self.debug else None, "extras": extras if self.debug else None},
        }
