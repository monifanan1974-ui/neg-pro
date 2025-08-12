# backend/tagger.py
# Simple persona & emotion detector (keyword-based, fast, deterministic).

import logging
from collections import Counter

logger = logging.getLogger("PersonaDetector")

class PersonaDetector:
    def __init__(self, persona_data=None, emotion_rules=None):
        self.persona_data = persona_data or {"personas":[]}
        self.emotion_rules = emotion_rules or {"triggers":[]}
        logger.info("PersonaDetector initialized")

    def detect(self, text):
        lowered = (text or "").lower()
        for persona in self.persona_data.get("personas", []):
            for keyword in persona.get("keywords", []):
                if keyword in lowered:
                    return persona["type"]
        return "default"

    def detect_emotion(self, text):
        lowered = (text or "").lower()
        emotion_counter = Counter()
        for trig in self.emotion_rules.get("triggers", []):
            for ind in trig.get("detection_indicators", []):
                if ind.lower() in lowered:
                    emotion_counter[trig["name"]] += 1
        return emotion_counter.most_common(1)[0][0] if emotion_counter else "neutral"

