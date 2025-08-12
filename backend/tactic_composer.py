import re
import random
import logging
from typing import Dict, Any, List

logger = logging.getLogger("TacticComposer")

class TacticComposer:
    def __init__(self, kb: Dict[str, Any]):
        """
        Initializes the composer with the full knowledge base.
        """
        self.tactics = (kb.get("tactic_library.json", {}) or {}).get("tactics", {})
        self.predictor = kb.get("response_predictor.json", {})
        self.persona_map_cfg = kb.get("persona_map.json", {})
        logger.info("TacticComposer initialized successfully.")

    def pick_opener(self, counterpart_persona: str, user_style: str) -> str:
        """
        Selects the best opener based on counterpart persona and user style.
        """
        openers = self.tactics.get("openers", [])
        if not openers:
            return "I'd like to start by ensuring we're aligned on the main goal today."

        def score(op: Dict[str, Any]) -> int:
            s = 0
            # Strong match for persona
            if "best_for_persona" in op and counterpart_persona:
                for tag in op["best_for_persona"]:
                    if tag.lower() in counterpart_persona.lower():
                        s += 2
            # Good match for user's style
            if user_style and "Confident" in op.get("name", "") and "Direct" in user_style:
                s += 1
            return s

        sorted_openers = sorted(openers, key=score, reverse=True)
        return sorted_openers[0].get("text", "")

    def pick_micro_tactics(self, limit: int = 2) -> List[Dict[str, str]]:
        """
        Selects a random set of actionable micro-tactics.
        """
        mts = self.tactics.get("micro_tactics", [])
        if not mts:
            return []
        random.shuffle(mts)
        return mts[:limit]

    def get_counter_by_id(self, tactic_id: str) -> str:
        """
        Finds a tactic's text by its ID from any category.
        """
        for category in self.tactics.values():
            if isinstance(category, list):
                for tactic in category:
                    if tactic.get("id") == tactic_id:
                        return tactic.get("text", "")
        return ""
