from __future__ import annotations

from typing import Any, Dict, List


def _ensure_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


class SignalAdapter:
    """
    Adapts raw questionnaire answers into a normalized context
    used by the rules engine:

      {
        "persona": {"types": [...]},
        "emotions": [...],
        "tags": [...]
      }

    All lookups are driven by a mapping JSON (rules_signal_map.json).
    """

    def __init__(self, mapping: Dict[str, Any]) -> None:
        self.map: Dict[str, Any] = mapping or {}

    # ---------- persona ----------
    def _persona_from_conflict(self, conflict_style: str) -> List[str]:
        table = self.map.get("persona_from_conflict_style", {})
        key = (conflict_style or "").strip().lower()
        return _ensure_list(table.get(key, []))

    # ---------- emotions ----------
    def _emotions_from_dominant(self, dominant: str) -> List[str]:
        table = self.map.get("emotions_from_dominant", {})
        key = (dominant or "").strip().lower()
        return _ensure_list(table.get(key, []))

    def _emotions_from_anxiety(self, rating: Any) -> List[str]:
        """
        Map a numeric anxiety rating to emotion buckets using ranges from mapping.
        The mapping should look like:
          "emotions_from_anxiety_rating": [
            {"min": 0, "max": 2, "emotions": ["calm"]},
            {"min": 3, "max": 5, "emotions": ["anxiety"]}
          ]
        """
        out: List[str] = []
        try:
            r = int(rating)
        except Exception:
            return out

        ranges = _ensure_list(self.map.get("emotions_from_anxiety_rating"))
        for rng in ranges:
            try:
                lo = int(rng.get("min"))
                hi = int(rng.get("max"))
                if lo <= r <= hi:
                    out.extend(_ensure_list(rng.get("emotions")))
            except Exception:
                # ignore malformed range objects
                pass
        # make unique, keep order
        return list(dict.fromkeys(out))

    # ---------- tags ----------
    def _tags_from_negotiation_type(self, negotiation_type: str) -> List[str]:
        table = self.map.get("tags_from_negotiation_type", {})
        key = (negotiation_type or "").strip().lower()
        return _ensure_list(table.get(key, []))

    def _tags_from_culture_region(self, region: str) -> List[str]:
        table = self.map.get("tags_from_culture_region", {})
        key = (region or "").strip().lower()
        return _ensure_list(table.get(key, []))

    # ---------- main adapter ----------
    def build_context(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expected incoming answer keys (customize to your questionnaire schema):
          - conflict_style: str
          - dominant_emotion: str or emoji
          - anxiety_rating: int
          - negotiation_type: str
          - culture_region: str
        """
        conflict_style = str(answers.get("conflict_style") or "")
        dominant_emotion = str(answers.get("dominant_emotion") or "")
        anxiety_rating = answers.get("anxiety_rating")
        negotiation_type = str(answers.get("negotiation_type") or "")
        culture_region = str(answers.get("culture_region") or "")

        persona_types: List[str] = self._persona_from_conflict(conflict_style)

        emotions: List[str] = []
        emotions += self._emotions_from_dominant(dominant_emotion)
        emotions += self._emotions_from_anxiety(anxiety_rating)

        tags: List[str] = []
        tags += self._tags_from_negotiation_type(negotiation_type)
        tags += self._tags_from_culture_region(culture_region)

        # fallbacks from mapping defaults
        if not persona_types:
            persona_types = _ensure_list(self.map.get("default_persona"))
        if not emotions:
            emotions = _ensure_list(self.map.get("default_emotions"))
        if not tags:
            tags = _ensure_list(self.map.get("default_tags"))

        # de-duplicate while preserving order
        persona_types = list(dict.fromkeys(persona_types))
        emotions = list(dict.fromkeys(emotions))
        tags = list(dict.fromkeys(tags))

        return {
            "persona": {"types": persona_types},
            "emotions": emotions,
            "tags": tags,
        }
