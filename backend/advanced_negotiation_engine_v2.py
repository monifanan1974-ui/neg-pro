# backend/advanced_negotiation_engine_v2.py
# V2 – Uses the branded HTML template via report_builder; keeps light quality gates.
# NOTE: We DO NOT strip <script> tags — the template uses JS to render.

from __future__ import annotations
import os, json, re, traceback
from typing import Dict, Any, List

from advanced_negotiation_engine import AdvancedNegotiationEngine
from rule_engine_expansion import RuleEngineExpansion
from questionnaire_mapper import map_questionnaire_to_inputs
from report_builder import build_report_html

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))

class AdvancedNegotiationEngineV2:
    def __init__(self, kb: Dict[str, Any] | None, data_dir: str, debug: bool = False):
        self.debug = bool(debug)
        self.data_dir = data_dir
        self.base_engine = AdvancedNegotiationEngine(kb, data_dir, debug=debug)

        rule_path = os.path.join(self.data_dir, "rulebook.json")
        try:
            with open(rule_path, "r", encoding="utf-8") as f:
                rules_data = json.load(f)
        except Exception:
            rules_data = {"rule_categories": {}}
        self.rule_engine = RuleEngineExpansion(rules_data, market_data={}, validation_rules={})

    def _calc_readiness(self, mapped: Dict[str, Any]) -> int:
        score = 40.0
        if (mapped.get("leverage") or {}).get("alternatives_BATNA"): score += 25.0
        ms = mapped.get("market_sources") or []
        score += min(20.0, max(0.0, (len(ms) - 1) * 10.0))
        proofs = (mapped.get("leverage") or {}).get("value_proofs") or []
        if len(proofs) >= 2: score += 15.0
        elif proofs: score += 7.5
        if (mapped.get("leverage") or {}).get("time_constraints"): score += 5.0
        return int(_clamp(score, 35.0, 95.0))

    def _quality_note(self, html: str, persona: str | None, region: str | None) -> str:
        warnings: List[str] = []
        # Persona phrasing (counterpart-only)
        head = html[:2000].lower()
        if "negotiate as the friend" in head:
            warnings.append("Persona phrasing: use counterpart style; avoid 'negotiate as The Friend'.")
            html = re.sub(r"negotiate\s+as\s+(['\"]?)the\s+friend\1", "align with a Friend-style counterpart", html, flags=re.IGNORECASE)

        # Currency consistency
        if (region or "").lower().startswith("uk") and "£" not in html and "$" in html:
            warnings.append("Currency mismatch: UK region should use GBP (£). Converted.")
            html = html.replace("$", "£")

        # Sources clickable (2+)
        if html.lower().count("<a ") < 2:
            warnings.append("Too few sources with links (need ≥ 2).")

        # If we found issues — add an alert box (non-blocking)
        if warnings:
            alert = (
                "<div style=\"background-color:#fffbe5;border:1px solid #fde047;"
                "padding:12px;border-radius:8px;margin:16px 0;\">"
                "<strong>AI Quality Alert:</strong> " + " ".join(warnings) +
                "</div>"
            )
            # Put alert after <header> if exists
            html = re.sub(r"(</header>)", r"\1" + alert, html, count=1, flags=re.IGNORECASE) if "</header>" in html else alert + html
        return html

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 1) Base engine v1
            base = self.base_engine.run(payload)

            # 2) Map questionnaire (priorities etc.)
            answers = (payload or {}).get("answers") or {}
            mapped = map_questionnaire_to_inputs(answers)

            # 3) Rules
            persona = ((base.get("debug") or {}).get("profile") or {}).get("persona", "")
            region  = ((base.get("debug") or {}).get("profile") or {}).get("country", "UK")
            fired = self.rule_engine.evaluate_all(mapped, persona, market_data={})

            # 4) Extras (if needed in future)
            priorities = (mapped.get("priorities_ranked") or ["salary", "title", "flexibility"])[:3]
            priorities = [str(x).strip().title() for x in priorities]
            readiness = self._calc_readiness(mapped)

            # 5) Build HTML from the template (report.html)
            rep = build_report_html(base, extras={"priorities": priorities, "readiness": readiness, "fired_rules": fired})

            # 6) Light quality note (non-blocking), do NOT strip <script>
            html = self._quality_note(rep.get("html") or "", persona, region)

            return {
                "status": "success",
                "format": "html",
                "engine": "v2",
                "html": html,
                "chart_data": rep.get("chart_data"),  # kept for API compatibility
                "rules_fired": fired,
                "profile": (base.get("debug") or {}).get("profile"),
                "reasons": base.get("reasons"),
            }
        except Exception as e:
            if self.debug:
                traceback.print_exc()
            return {"status": "error", "reason_code": "V2_ENGINE_ERROR", "reason": f"{type(e).__name__}: {e}"}
