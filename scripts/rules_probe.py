from __future__ import annotations
import json, os, sys
from typing import Any, List, Dict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = [
    os.path.join(ROOT, "rules-engine.json"),
    os.path.join(ROOT, "data", "rules-engine.json"),
    os.path.join(ROOT, "backend", "rules-engine.json"),
    os.path.join(ROOT, "configs", "rules-engine.json"),
]

# Known signals from questionnaire schema
KNOWN_SIGNALS = [
    "fear_core_text","emotion_dominant","negotiation_type","goal_primary","leverage_main",
    "walkaway_limit_type","target_salary","target_bonus_percentage","key_benefits","anxiety_rating",
    "conflict_style","counterpart_style","counterpart_power","counterpart_walkaway_signals",
    "prior_offer_status","relationship_importance","deadline_type","culture_region",
    "market_sources","current_challenges","preferred_communication"
]

def load_rules() -> Any:
    for p in CANDIDATES:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[INFO] Using rules file: {p}")
            return data
    print("[ERROR] rules-engine.json not found in common paths.")
    sys.exit(1)

def walk(node: Any, path: List[str], hits: Dict[str, List[str]]):
    # Find any place where a known signal appears either as a VALUE string,
    # or as a KEY name (some rule formats use {"negotiation_type": "salary"}).
    if isinstance(node, dict):
        for k, v in node.items():
            new_path = path + [str(k)]
            if isinstance(v, str) and v in KNOWN_SIGNALS:
                hits.setdefault(v, []).append(".".join(new_path))
            if isinstance(k, str) and k in KNOWN_SIGNALS:
                hits.setdefault(k, []).append(".".join(path + [f"<KEY:{k}>"]))
            walk(v, new_path, hits)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            walk(item, path + [f"[{i}]"], hits)
    # primitives -> ignore

def main():
    rules = load_rules()
    hits: Dict[str, List[str]] = {}
    walk(rules, [], hits)

    print("\n=== Rules Probe Results ===")
    if not hits:
        print("No known signals found anywhere in rules. (Structure might be theoretical or uses different names.)")
        return

    for sig, paths in sorted(hits.items(), key=lambda x: (-len(x[1]), x[0])):
        print(f"\n• {sig}: {len(paths)} occurrence(s)")
        for p in paths[:25]:
            print(f"   - {p}")
        if len(paths) > 25:
            print(f"   ... (+{len(paths)-25} more)")

if __name__ == "__main__":
    main()
