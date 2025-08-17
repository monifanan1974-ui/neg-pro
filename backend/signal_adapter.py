cat > backend/signal_adapter.py <<'PY'
# backend/signal_adapter.py
# Translate questionnaire answers (signals) into rules-engine context:
# persona.types, emotions[], tags[].

from __future__ import annotations
from typing import Any, Dict, List

def _ensure_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]

class SignalAdapter:
    def __init__(self, mapping: Dict[str, Any]):
        self.map = mapping or {}

    def _persona_from_conflict(self, conflict_style: str) -> List[str]:
        table = self.map.get("persona_from_conflict_style", {})
        return _ensure_list(table.get(str(conflict_style or "").lower(), []))

    def _emotions_from_dominant(self, dominant: str) -> List[str]:
        table = self.map.get("emotions_from_dominant", {})
        return _ensure_list(table.get(str(dominant or "").lower(), []))

    def _emotions_from_anxiety(self, rating: Any) -> List[str]:
        out: List[str] = []
        try:
            r = int(rating)
        except Exception:
            return out
        ranges = _ensure_list(self.map.get("emotions_from_anxiety_rating"))
        for rng in ranges:
            try:
                if rng["min"] <= r <= rng["max"]:
                    out.extend(_ensure_list(rng.get("emotions")))
            except Exception:
                pass
        return list(dict.fromkeys(out))  # unique, keep order

    def _tags_from_negotiation_type(self, t: str) -> List[str]:
        table = self.map.get("tags_from_negotiation_type", {})
        return _ensure_list(table.get(str(t or "").lower(), []))

    def _tags_from_culture_region(self, region: str) -> List[str]:
        table = self.map.get("tags_from_culture_region", {})
        return _ensure_list(table.get(str(region or "").lower(), []))

    def build_context(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        conflict_style = str(answers.get("conflict_style") or "")
        dominant_emotion = str(answers.get("dominant_emotion") or "")
        anxiety_rating = answers.get("anxiety_rating")
        negotiation_type = str(answers.get("negotiation_type") or "")
        culture_region = str(answers.get("culture_region") or "")

        persona_types = self._persona_from_conflict(conflict_style)
        emotions = self._emotions_from_dominant(dominant_emotion)
        emotions += self._emotions_from_anxiety(anxiety_rating)
        tags: List[str] = []
        tags += self._tags_from_negotiation_type(negotiation_type)
        tags += self._tags_from_culture_region(culture_region)

        # fallbacks
        if not persona_types:
            persona_types = _ensure_list(self.map.get("default_persona"))
        if not emotions:
            emotions = _ensure_list(self.map.get("default_emotions"))
        if not tags:
            tags = _ensure_list(self.map.get("default_tags"))

        # de-dup while keeping order
        persona_types = list(dict.fromkeys(persona_types))
        emotions = list(dict.fromkeys(emotions))
        tags = list(dict.fromkeys(tags))

        return {
            "persona": {"types": persona_types},
            "emotions": emotions,
            "tags": tags
        }
PY
