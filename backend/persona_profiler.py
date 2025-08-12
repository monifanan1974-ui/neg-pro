# backend/persona_profiler.py
# Persona & context profiler: builds a rich, industry-aware profile JSON.
# English-only output by design.

import os, json
from typing import Dict, Any, List

def _safe_load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

class PersonaProfiler:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.kb_sofi = _safe_load(os.path.join(data_dir, "Maagar_Sofi_994.json"))
        self.local = _safe_load(os.path.join(data_dir, "local-data.json"))
        self.rules = _safe_load(os.path.join(data_dir, "rules-engine.json"))
        self.tactics = _safe_load(os.path.join(data_dir, "tactic_library.json"))

    def _infer_culture(self, country: str) -> str:
        hc = {"JP","Japan","KR","CN","AE","SA","QA","KW"}
        return "high" if (country or "").strip() in hc else "low"

    def _infer_counterpart(self, counterpart_persona: str, industry: str) -> str:
        if counterpart_persona:
            return counterpart_persona
        # simple industry defaults
        ind = (industry or "").lower()
        if any(x in ind for x in ["finance","bank","invest"]):
            return "The Analyst (Data-driven, logical, avoids emotion, slow to decide)"
        if any(x in ind for x in ["sales","agency","vendor"]):
            return "The Fox (Cunning, strategic, may use tricky tactics)"
        if any(x in ind for x in ["tech","software","startup"]):
            return "The Friend (Relationship-focused, avoids conflict, may hide true interests)"
        return "The Dominator (Aggressive, impatient, sees it as a battle)"

    def _decision_style(self, communication_style: str, seniority: str) -> str:
        cs = (communication_style or "").lower()
        sn = (seniority or "").lower()
        style = []
        if "analyt" in cs: style.append("data-first")
        if "direct" in cs: style.append("concise")
        if "diplomat" in cs or "collab" in cs: style.append("consensus-seeking")
        if "quiet" in cs or "observ" in cs: style.append("listening-heavy")
        if "lead" in sn or "senior" in sn: style.append("time-boxed decisions")
        return ", ".join(style) or "balanced"

    def _motivations_and_fears(self, industry: str, user_challenges: List[str]) -> Dict[str, Any]:
        ind = (industry or "").lower()
        motiv = []
        fears = []
        if "finance" in ind:
            motiv += ["risk control", "regulatory compliance", "predictable delivery"]
            fears += ["reputation loss", "audit issues"]
        if "tech" in ind or "software" in ind:
            motiv += ["velocity", "innovation", "talent retention"]
            fears += ["missed deadlines", "hiring churn"]
        if "agency" in ind or "marketing" in ind:
            motiv += ["client satisfaction", "case studies", "renewals"]
            fears += ["churn", "overruns"]

        # Map user mental/professional challenges into tactics signal
        signals = {"anxiety":"prefer soft openers", "burnout":"short meetings", "imposter":"emphasize objective wins"}
        flags = [signals.get(c.lower(), c) for c in (user_challenges or [])]

        return {"motivations": list(dict.fromkeys(motiv)) or ["business continuity"],
                "fears": list(dict.fromkeys(fears)) or ["budget overrun"],
                "challenge_signals": flags}

    def build(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        inputs expects keys:
        industry, role, seniority, country, communication_style,
        counterpart_persona (optional), challenges: List[str]
        """
        country = inputs.get("country") or "UK"
        persona = self._infer_counterpart(inputs.get("counterpart_persona"), inputs.get("industry"))
        culture = self._infer_culture(country)
        decision = self._decision_style(inputs.get("communication_style"), inputs.get("seniority"))
        mf = self._motivations_and_fears(inputs.get("industry"), inputs.get("challenges") or [])

        tone = inputs.get("personality_tone") or ("firm" if "concise" in decision else "neutral")

        return {
            "persona": persona,
            "culture": culture,
            "power": inputs.get("power") or "peer",
            "industry": inputs.get("industry"),
            "role": inputs.get("role"),
            "seniority": inputs.get("seniority"),
            "country": country,
            "decision_style": decision,
            "tone": tone,
            "motivations": mf["motivations"],
            "fears": mf["fears"],
            "challenge_signals": mf["challenge_signals"],
            "key_terms": [
                {"term":"Logrolling","definition":"Trade low-priority issues for high-priority wins."},
                {"term":"Bounded Ethicality","definition":"Stay ethical and watch for blind spots."},
                {"term":"Loss Aversion","definition":"People fear losses; frame to reduce perceived loss."}
            ],
            "insights": [
                "High-context: soften anchors, longer pauses, emphasize continuity." if culture=="high"
                else "Low-context: use crisp numbers, short asks, clear timeboxes."
            ]
        }

