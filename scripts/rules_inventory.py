# scripts/rules_inventory.py
# Scan rules-engine.json to inventory keys/strings and suggest a simple mapping
# Usage:
#   python scripts/rules_inventory.py --scan
#   python scripts/rules_inventory.py --make-map
# Outputs:
#   scripts/rules_inventory_report.json
#   data/rules_signal_map.json  (when --make-map is used)

from __future__ import annotations
import json, os, argparse, re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_CANDIDATES = [
    os.path.join(ROOT, "rules-engine.json"),
    os.path.join(ROOT, "data", "rules-engine.json"),
    os.path.join(ROOT, "backend", "rules-engine.json"),
    os.path.join(ROOT, "configs", "rules-engine.json"),
]

# Known questionnaire signals (from your schema)
KNOWN_SIGNALS = [
    "fear_core_text","emotion_dominant","negotiation_type","goal_primary","leverage_main",
    "walkaway_limit_type","target_salary","target_bonus_percentage","key_benefits","anxiety_rating",
    "conflict_style","counterpart_style","counterpart_power","counterpart_walkaway_signals",
    "prior_offer_status","relationship_importance","deadline_type","culture_region",
    "market_sources","current_challenges","preferred_communication"
]

OUT_REPORT = os.path.join(ROOT, "scripts", "rules_inventory_report.json")
OUT_MAP    = os.path.join(ROOT, "data", "rules_signal_map.json")

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

def load_rules() -> Any:
    for p in RULES_CANDIDATES:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[INFO] Using rules file: {p}")
            return data, p
    raise FileNotFoundError("rules-engine.json not found in common paths.")

def tokens(s: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(s or "") if t]

def walk_collect(node: Any, path: List[str], key_counter: Counter, str_counter: Counter, samples: Dict[str, List[str]]):
    if isinstance(node, dict):
        for k, v in node.items():
            key_counter[k] += 1
            samples.setdefault(k, [])
            if len(samples[k]) < 5:
                samples[k].append(".".join(path + [k]))
            walk_collect(v, path + [k], key_counter, str_counter, samples)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            walk_collect(item, path + [f"[{i}]"], key_counter, str_counter, samples)
    elif isinstance(node, str):
        # collect free strings (rule literals, labels, etc.)
        for tk in set(tokens(node)):
            str_counter[tk] += 1

def build_mapping_suggestions(key_counter: Counter, str_counter: Counter) -> Dict[str, Dict[str, List[str]]]:
    """
    Very simple heuristic: for each known signal, try to find keys/strings that share word tokens.
    """
    suggestions: Dict[str, Dict[str, List[str]]] = {}
    # pre-tokenize all keys
    key_tokens_map: Dict[str, Set[str]] = {k: set(tokens(k)) for k in key_counter.keys()}
    # and consider high-frequency strings as "concept words"
    frequent_words = {w for (w, c) in str_counter.most_common(200)}

    for sig in KNOWN_SIGNALS:
        stoks = set(tokens(sig))
        key_hits: List[Tuple[int, str]] = []
        for k, ktoks in key_tokens_map.items():
            score = len(stoks & ktoks)
            if score > 0:
                key_hits.append((score, k))
        key_hits.sort(key=lambda x: (-x[0], x[1]))

        # also suggest words from strings that overlap with signal tokens
        word_hits = sorted([w for w in frequent_words if w in stoks])

        suggestions[sig] = {
            "key_candidates": [k for _, k in key_hits[:10]],
            "word_hints": word_hits
        }
    return suggestions

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true", help="Create inventory report")
    parser.add_argument("--make-map", action="store_true", help="Create suggested mapping file")
    args = parser.parse_args()

    rules, used_path = load_rules()

    key_counter: Counter = Counter()
    str_counter: Counter = Counter()
    key_samples: Dict[str, List[str]] = {}

    walk_collect(rules, [], key_counter, str_counter, key_samples)

    if args.scan:
        report = {
            "rules_path": used_path,
            "unique_keys": len(key_counter),
            "top_keys": key_counter.most_common(100),
            "unique_words_in_strings": len(str_counter),
            "top_words": str_counter.most_common(100),
            "samples_per_key": key_samples,
        }
        os.makedirs(os.path.dirname(OUT_REPORT), exist_ok=True)
        with open(OUT_REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[OK] Inventory written to: {OUT_REPORT}")

    if args.make_map:
        suggestions = build_mapping_suggestions(key_counter, str_counter)
        # final JSON structure: { "mapping": {signal: {"key_candidates":[], "word_hints":[]}}, "note": "..."}
        mapping_file = {
            "note": "This is an auto-suggested mapping between questionnaire signals and rule vocabulary. Review/edit as needed.",
            "mapping": suggestions
        }
        os.makedirs(os.path.dirname(OUT_MAP), exist_ok=True)
        with open(OUT_MAP, "w", encoding="utf-8") as f:
            json.dump(mapping_file, f, indent=2, ensure_ascii=False)
        print(f"[OK] Suggested map written to: {OUT_MAP}")

if __name__ == "__main__":
    main()
