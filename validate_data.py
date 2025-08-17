#!/usr/bin/env python3
# validate_data.py
import json, sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

def read_json_multi(*candidates):
    for p in candidates:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f), p
    return None, None

def collect_schema_signals(schema):
    sigs = {}
    for ph in schema.get("phases", []):
        for q in ph.get("questions", []):
            exp = q.get("export") or {}
            sig = exp.get("signal")
            if sig:
                sigs[sig] = {"id": q.get("id"), "question": q.get("question")}
    return sigs

def walk_signals_from_rules(node, bag):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "signal" and isinstance(v, str):
                bag.append(v)
            else:
                walk_signals_from_rules(v, bag)
    elif isinstance(node, list):
        for it in node:
            walk_signals_from_rules(it, bag)

def validate_rules_struct(rules):
    errors = []
    ids = []
    for i, r in enumerate(rules if isinstance(rules, list) else []):
        rid = r.get("id")
        if not rid:
            errors.append(f"Rule #{i} missing 'id'")
        else:
            ids.append(rid)
        if not r.get("conditions"):
            errors.append(f"Rule '{rid}' missing 'conditions'")
        if not r.get("recommendations"):
            errors.append(f"Rule '{rid}' missing 'recommendations'")
    dups = [k for k, c in Counter(ids).items() if c > 1]
    if dups:
        errors.append(f"Duplicate rule ids: {dups}")
    return errors

def main():
    # load files (fallbacks)
    questionnaire, q_path = read_json_multi(ROOT/"questionnaire.json")
    if questionnaire is None:
        print("ERROR: questionnaire.json not found", file=sys.stderr)
        sys.exit(2)
    rules, rules_path = read_json_multi(DATA_DIR/"rules-engine.json", ROOT/"rules-engine.json")
    if rules is None:
        print("ERROR: rules-engine.json not found (data/ or root)", file=sys.stderr)
        sys.exit(2)
    signal_map, map_path = read_json_multi(DATA_DIR/"rules_signal_map.json")

    schema_signals = collect_schema_signals(questionnaire)
    rule_signal_list = []
    walk_signals_from_rules(rules, rule_signal_list)
    rule_signals = Counter(rule_signal_list)

    struct_errors = validate_rules_struct(rules if isinstance(rules, list) else [])
    report = {
        "paths": {
            "questionnaire": str(q_path),
            "rules_engine": str(rules_path),
            "rules_signal_map": str(map_path) if map_path else None
        },
        "counts": {
            "schema_signals": len(schema_signals),
            "rule_signal_occurrences": sum(rule_signals.values()),
            "unique_rule_signals": len(rule_signals),
            "rules_total": len(rules if isinstance(rules, list) else []),
        },
        "errors": struct_errors,
        "warnings": [],
        "diffs": {
            "signals_in_rules_not_in_schema": sorted(set(rule_signals) - set(schema_signals)),
            "signals_in_schema_not_in_rules": sorted(set(schema_signals) - set(rule_signals)),
        }
    }

    if signal_map:
        # basic check that all map keys exist either in schema or rules usage
        map_keys = set(signal_map.keys()) if isinstance(signal_map, dict) else set()
        unknown_in_map = sorted(map_keys - (set(schema_signals) | set(rule_signals)))
        if unknown_in_map:
            report["warnings"].append(f"Signals in map but unknown to schema/rules: {unknown_in_map}")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    has_errors = bool(struct_errors)
    # treat hard inconsistencies as non-zero exit
    if has_errors:
        sys.exit(1)

if __name__ == "__main__":
    main()
