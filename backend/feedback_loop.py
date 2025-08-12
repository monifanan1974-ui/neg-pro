# backend/feedback_loop.py
# Summarize recent feedback to enrich Stage A (English-only).

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from collections import Counter
from typing import Any, Dict, List

class FeedbackLoop:
    def __init__(self, feedback_data: Dict[str, Any] | None):
        self.feedback_data = feedback_data or {}
        self.entries: List[Dict[str, Any]] = list(self.feedback_data.get("entries", []))

    def analyze(self) -> Dict[str, Any]:
        """Return a compact summary over the last 30 days.
        Expects each entry like: { "ts": <unix seconds>, "issues": [..], "sentiment_score": float }
        """
        if not self.entries:
            return {}

        recent_threshold = datetime.now(timezone.utc) - timedelta(days=30)
        recent: List[Dict[str, Any]] = []
        for e in self.entries:
            try:
                t = datetime.fromtimestamp(float(e["ts"]), tz=timezone.utc)
            except Exception:
                continue
            if t >= recent_threshold:
                recent.append(e)

        issue_counter = Counter()
        sentiment_sum = 0.0
        for e in recent:
            issue_counter.update(e.get("issues", []))
            try:
                sentiment_sum += float(e.get("sentiment_score", 0))
            except Exception:
                pass

        avg_sent = round(sentiment_sum / len(recent), 2) if recent else 0.0

        return {
            "total_entries": len(self.entries),
            "recent_entries": len(recent),
            "common_issues": issue_counter.most_common(5),
            "avg_sentiment": avg_sent,
        }
