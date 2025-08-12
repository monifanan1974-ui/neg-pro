# backend/feedback_loop.py
# Summarizes recent feedback to enrich Stage A.

import logging
# --- FIXED: Added timezone to handle timestamps correctly ---
from datetime import datetime, timedelta, timezone
from collections import Counter

logger = logging.getLogger("FeedbackLoop")

class FeedbackLoop:
    def __init__(self, feedback_data):
        self.feedback_data = feedback_data or {}
        self.entries = self.feedback_data.get("entries", [])

    def analyze(self):
        if not self.entries:
            return {}
        try:
            # We compare against a UTC timestamp, so we need to ensure our loaded times are also in UTC.
            recent_threshold = datetime.now(timezone.utc) - timedelta(days=30)
            recent = []
            for e in self.entries:
                try:
                    # --- FIXED: Read the correct 'ts' field (Unix timestamp) instead of 'timestamp' (ISO string) ---
                    # The `tz=timezone.utc` makes the datetime object "aware" of its timezone.
                    t = datetime.fromtimestamp(e["ts"], tz=timezone.utc)
                    if t >= recent_threshold:
                        recent.append(e)
                except (KeyError, TypeError, ValueError):
                    # Skip entries that are missing the 'ts' key or have an invalid format.
                    continue

            issue_counter = Counter()
            sentiment_sum = 0
            for e in recent:
                issue_counter.update(e.get("issues", []))
                sentiment_sum += float(e.get("sentiment_score", 0))

            avg_sent = round(sentiment_sum / len(recent), 2) if recent else 0.0
            return {
                "total_entries": len(self.entries),
                "recent_entries": len(recent),
                "common_issues": issue_counter.most_common(5),
                "avg_sentiment": avg_sent
            }
        except Exception as ex:
            logger.error(f"Feedback analysis failed: {ex}")
            return {}```

---

### **2) קובץ מתוקן: `backend/advanced_negotiation_engine.py`**

**מה תיקנו כאן?**
בתוך הפונקציה `build_technical_card`, החלפנו את השורה היחידה שקובעת את סמל המטבע בלוגיקה מורחבת שכוללת בדיקה עבור ארה"ב (`US`, `USA`) ומחזירה דולר ($) במקרה המתאים.

**הוראות:** החלף את כל התוכן של `backend/advanced_negotiation_engine.py` בקוד הבא:

```python
# backend/advanced_negotiation_engine.py
# FINAL UPGRADED VERSION V2.3.2 - Adds improved currency detection logic

import os
import re
import json
import random
from typing import Dict, Any, List, Optional, Tuple

from persona_profiler import PersonaProfiler
from market_intel import MarketIntel
from simulation_manager import SimulationManager
from tactic_composer import TacticComposer

try:
    import openai
    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False

def _safe_load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _fmt_range(lo: str, hi: str) -> str:
    lo = (lo or "").strip(); hi = (hi or "").strip()
    if lo and hi: return f"{lo}–{hi}"
    return lo or hi or "a market-aligned range"

class AdvancedNegotiationEngine:
    def __init__(self, kb: Dict[str, Any] | None = None, data_dir: str | None = None, debug: bool = False):
        self.debug = bool(debug)
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

        if kb is None:
            self.kb = {f: _safe_load(os.path.join(self.data_dir, f)) for f in os.listdir(self.data_dir) if f.lower().endswith(".json")}
        else:
            self.kb = kb
        
        self.profiler = PersonaProfiler(self.data_dir)
        self.market = MarketIntel(self.data_dir)
        
        playlets_data = self.kb.get("simulation-playlets.json", {})
        dilemmas_data = self.kb.get("user-dilemmas.json", {})
        self.simulation_manager = SimulationManager(playlets_data, dilemmas_data)
        self.tactic_composer = TacticComposer(self.kb)

    def collect_and_enrich(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        answers = payload.get("answers") or {}
        return {
            "industry": answers.get("industry"), "role": answers.get("role"),
            "seniority": answers.get("seniority") or "mid", "country": answers.get("country") or "UK",
            "communication_style": answers.get("communication_style"), "counterpart_persona": answers.get("counterpart_persona"),
            "challenges": answers.get("challenges") or [], "personality_tone": payload.get("tone") or "neutral",
            "impacts": answers.get("impacts") or [], "market_sources": answers.get("market_sources") or ["Glassdoor", "Levels.fyi"],
            "range_low": answers.get("range_low") or "", "range_high": answers.get("range_high") or "",
            "target_salary": answers.get("target_salary") or ""
        }

    def build_persona(self, enriched: Dict[str, Any]) -> Dict[str, Any]:
        return self.profiler.build(enriched)

    def build_technical_card(self, enriched: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        intel = self.market.build(enriched, profile)
        
        # --- FIXED: Improved currency detection logic ---
        country_code = (profile.get("country") or "").upper()
        if country_code in ("UK", "GB", "ENGLAND"):
            symbol = "£"
        elif country_code in ("US", "USA", "AMERICA"):
            symbol = "$"
        else:
            symbol = "€" # Default to Euro for other regions

        tail, anchor_val = self.market.numeric_anchor(
            intel["range_low"], intel["range_high"], enriched.get("target_salary"),
            persona=profile["persona"], risk=3, symbol=symbol
        )
        rng = _fmt_range(intel["range_low"], intel["range_high"])
        sources = ", ".join(intel["sources"])
        proofs = ", ".join(intel["impacts"]) if intel["impacts"] else "recent measurable results"

        base_opening = "Before we dive into specifics, I want to make sure we’re aligned on a shared goal: a solution that works for both sides over the long term. From your perspective, what would a successful outcome look like?"
        opener_text = self.tactic_composer.pick_opener(profile.get("persona", ""), profile.get("communication_style", ""))
        opening_variants = {
            "soft": opener_text,
            "neutral": base_opening,
            "firm": opener_text.replace("I'd like to start by ensuring", "Let's be clear and ensure")
        }

        tech_card = {
            "profile": profile,
            "plan": {
                "posture": "Value Articulator" if "Friend" in profile.get("persona", "") else "Controlled Assertiveness",
                "opening": base_opening,
                "opening_variants": opening_variants,
                "anchor": f"Based on current market data ({sources}) and my delivered results ({proofs}), a range of {rng} is standard. {tail}",
                "pivot": "Let’s align on scope, title, and compensation first; then we can revisit perks."
            },
            "scenarios": [
                {"id":"lowball","trigger":"Lowball offer","reply":"I appreciate the offer. It may help if I clarify the unique value and specific results I deliver, as it seems we’re valuing the role differently."},
                {"id":"stall","trigger":"Stall / Delay","reply":"I understand careful consideration. To be transparent, I do have other timelines; could we agree on a realistic decision window?"},
            ],
            "micro": self.tactic_composer.pick_micro_tactics(limit=2),
            "warnings": intel["warnings"],
            "meta": {"range": rng, "anchor_value": anchor_val}
        }
        reasons = {
            "range_reason": "Based on user-provided data." if enriched.get("range_low") else "Inferred from local market data as no user range was provided.",
            "anchor_reason": f"Calculated based on a '{profile.get('persona', 'default')}' persona, which adjusts the anchor for optimal effect."
        }
        return tech_card, reasons

    def build_personalized_content(self, profile: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[Dict], List[Dict], Dict[str, str]]:
        playlet = self.simulation_manager.get_relevant_scenario(profile)
        dilemma = random.choice(self.simulation_manager.dilemmas) if self.simulation_manager.dilemmas else None
        deep_dives = [{"id": "STRAT-002", "title": "Negotiating from a Position of Weakness"}, {"id": "MODEL-001", "title": "Distributive vs. Integrative Models"}]

        playlet_reason = (
            f"Selected because its persona fit ('{', '.join(playlet.get('persona_fit', []))}') matches your counterpart's profile."
            if playlet and playlet.get('persona_fit')
            else "No specific playlet matched the persona; a generally useful one was selected."
        )
        dilemma_reason = (
            f"Selected to address common challenges like '{dilemma.get('title')}' which often arise in such negotiations."
            if dilemma and dilemma.get('title')
            else "A general dilemma was selected for practice."
        )
        
        reasons = {
            "playlet_reason": playlet_reason,
            "dilemma_reason": dilemma_reason,
            "deep_dives_reason": "Selected to provide strategic depth on power dynamics and value creation, key themes in your scenario."
        }
        return playlet, dilemma, deep_dives, reasons

    def _markdown_from_tech(self, tech: Dict[str, Any]) -> str:
        p = tech.get("profile", {})
        pl = tech.get("plan", {})
        
        def bullets(items, formatter=lambda x: f"- {x}"):
            return "\n".join([formatter(item) for item in items]) if items else "- (none)"

        return f"""
# Counterpart Psychological Profile
- **Persona:** {p.get('persona', 'N/A')}
- **Decision Style:** {p.get('decision_style', 'N/A')}
- **Motivations:** {', '.join(p.get('motivations', []))}
- **Fears:** {', '.join(p.get('fears', []))}

# Your Strategic Game Plan
- **Overall Posture:** {pl.get('posture', 'N/A')}
- **Opening Move:** {pl.get('opening', 'N/A')}
- **Anchor:** {pl.get('anchor', 'N/A')}
- **Mid-Game Pivot:** {pl.get('pivot', 'N/A')}

# Response Scenarios
{bullets(tech.get('scenarios', []), lambda s: f"- **{s.get('trigger', '')}:** {s.get('reply', '')}")}

# Power Micro-Tactics
{bullets(tech.get('micro', []), lambda m: f"- **{m.get('name', '')}:** {m.get('description', '')}")}

# Data Warnings
{bullets(tech.get('warnings', []))}
""".strip()

    def _openai_super_polish(self, md: str, tone: str) -> Dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not (_OPENAI_OK and api_key):
            return {"text": md + "\n\n> *Enhanced by local engine only.*", "engine": "fallback", "model": None}
        try:
            openai.api_key = api_key
            resp = openai.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                messages=[
                    {"role": "system", "content": f"You are a world-class negotiation coach. Rewrite this battle card to be clearer and more encouraging. Keep all facts and markdown structure. Tone: {tone}."},
                    {"role": "user", "content": md}
                ],
                temperature=0.4, max_tokens=1500
            )
            return {"text": resp.choices[0].message["content"].strip(), "engine": "openai", "model": os.getenv("OPENAI_MODEL", "gpt-4")}
        except Exception as e:
            return {"text": md + f"\n\n> *OpenAI polish failed: {e}. Showing base version.*", "engine": "fallback", "model": None}

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        enriched = self.collect_and_enrich(payload)
        profile = self.build_persona(enriched)
        tech_card, tech_reasons = self.build_technical_card(enriched, profile)
        playlet, dilemma, deep_dives, content_reasons = self.build_personalized_content(profile)

        md_raw = self._markdown_from_tech(tech_card)
        polish_info = self._openai_super_polish(md_raw, enriched["personality_tone"])
        
        return {
            "status": "success", "format": "md",
            "card": polish_info["text"],
            "ui_payload": {
                "openings": tech_card.get("plan", {}).get("opening_variants"),
                "scenarios": tech_card.get("scenarios"),
                "playlet": playlet, "dilemma": dilemma, "dives": deep_dives
            },
            "reasons": {**tech_reasons, **content_reasons},
            "debug": {"profile": profile, "polish": polish_info}
        }
אחרי שתחליף את שני הקבצים האלה, המערכת שלך תהיה יציבה יותר ומדויקת יותר. אתה מוזמן להמשיך לבדוק ולראות שהכל עובד כמצופה.