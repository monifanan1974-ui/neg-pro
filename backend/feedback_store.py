# backend/feedback_store.py
import os, json, time
from typing import Dict, Any, List

class FeedbackStore:
    """
    Tiny JSON store for user feedback. Appends entries and can aggregate simple stats.
    """
    def __init__(self, data_dir: str):
        self.path = os.path.join(data_dir, "feedback_user.json")
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"entries": []}, f)

    def _load(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, doc: Dict[str, Any]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    def add(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        doc = self._load()
        entry = {
            "ts": int(time.time()),
            "scenario_id": payload.get("scenario_id"),
            "outcome": payload.get("outcome"),          # "win" | "loss" | "partial"
            "usefulness": int(payload.get("usefulness", 0)),  # 0..10
            "notes": payload.get("notes", "")[:2000],
            "persona": payload.get("persona"),
            "country": payload.get("country")
        }
        doc["entries"].append(entry)
        self._save(doc)
        return entry

    def aggregate(self) -> Dict[str, Any]:
        doc = self._load()
        entries: List[Dict[str, Any]] = doc.get("entries", [])
        if not entries:
            return {"count": 0, "success_rate": 0.0, "avg_usefulness": 0.0}
        wins = sum(1 for e in entries if e.get("outcome") == "win")
        partial = sum(1 for e in entries if e.get("outcome") == "partial")
        success_rate = (wins + 0.5 * partial) / len(entries)
        avg_usefulness = sum(int(e.get("usefulness", 0)) for e in entries) / len(entries)
        return {
            "count": len(entries),
            "success_rate": round(success_rate * 100, 1),
            "avg_usefulness": round(avg_usefulness, 2),
        }

