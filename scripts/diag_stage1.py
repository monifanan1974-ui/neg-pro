# scripts/diag_stage1.py
# Stage 1 Diagnostics — measure coverage & missing signals before refactors.
# Usage:
#   python scripts/diag_stage1.py --answers answers.json
# If answers not provided, will try ./answers.local.json; otherwise runs with empty answers.

from __future__ import annotations
import json
import os
import sys
import argparse
from collections import Counter, OrderedDict
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_OUT = os.path.join(ROOT, "scripts", "diag_stage1_report.json")

SEARCH_CANDIDATES = [
    ".", "data", "backend", "configs"
]

def find_file(basenames: List[str]) -> str:
    """Search common folders for the first existing file from basenames."""
    for folder in SEARCH_CANDIDATES:
        for base in basenames:
            path = os.path.join(ROOT, folder, base)
            if os.path.exists(path):
                return path
    return ""

def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

def collect_all_questions(schema: dict) -> List[dict]:
    phases = ensure_list(schema.get("phases"))
    all_q: List[dict] = []
    for p in phases:
        all_q.extend(ensure_list(p.get("questions")))
    return all_q

def collect_signals_from_schema(schema: dict) -> Dict[str, dict]:
    """
    Returns: { signal_name: {id, question} }
    signal is taken from question.export.signal (if exists).
    """
    result: Dict[str, dict] = {}
    for q in collect_all_questions(schema):
        qid = q.get("id")
        export_meta = (q.get("export") or {})
        sig = export_meta.get("signal")
        if sig and qid:
            result[sig] = {"id": qid, "question": q.get("question")}
    return result

def answer_coverage(schema: dict, answers: dict) -> dict:
    questions = collect_all_questions(schema)
    total = len(questions)
    answered_ids: List[str] = []
    for q in questions:
        qid = q.get("id")
        if not qid:
            continue
        if qid in answers and answers[qid] not in ("", None, []):
            answered_ids.append(qid)

    signals_map = collect_signals_from_schema(schema)
    covered_signals = [s for s, meta in signals_map.items() if meta.get("id") in answered_ids]
    missing_signals = sorted(set(signals_map.keys()) - set(covered_signals))

    return {
        "questions_total": total,
        "questions_answered": len(answered_ids),
        "questions_coverage_pct": (len(answered_ids) / total * 100.0) if total else 0.0,
        "signals_total": len(signals_map),
        "signals_covered": len(covered_signals),
        "signals_covered_pct": (len(covered_signals) / max(1, len(signals_map)) * 100.0),
        "covered_signal_names": covered_signals,
        "missing_signal_names": missing_signals,
        "answered_ids": answered_ids,
    }

def count_signal_frequency_in_rules(rules_json: Any) -> Counter:
    """
    Count appearances of dict key 'signal' with string value anywhere in rules JSON.
    This works as an 'importance proxy' (more mentions = more impact).
    """
    freq = Counter()
    def walk(node: Any):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "signal" and isinstance(v, str):
                    freq[v] += 1
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(rules_json)
    return freq

def extract_rule_signal_sets(rules_json: Any) -> List[set]:
    """
    Heuristic: search for structures like {"all": [{"signal":"x"}, {"signal":"y"}]} or
    {"any": [{"signal":"x"}, ...]} etc., and extract the set of signals referenced.
    """
    sets: List[set] = []

    def extract_from_condition(node: Any) -> List[set]:
        res: List[set] = []
        if not isinstance(node, dict):
            return res
        for key in ("all", "any", "none"):
            if key in node and isinstance(node[key], list):
                group = set()
                for sub in node[key]:
                    if isinstance(sub, dict):
                        if "signal" in sub and isinstance(sub["signal"], str):
                            group.add(sub["signal"])
                        nested_sets = extract_from_condition(sub)
                        for ns in nested_sets:
                            group |= ns
                if group:
                    res.append(group)
        if "signal" in node and isinstance(node["signal"], str):
            res.append({node["signal"]})
        return res

    def walk(node: Any):
        if isinstance(node, dict):
            sets.extend(extract_from_condition(node))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(rules_json)
    uniq = []
    seen = set()
    for s in sets:
        key = tuple(sorted(s))
        if key not in seen and s:
            seen.add(key)
            uniq.append(s)
    return uniq

def estimate_potential_rule_matches(present_signals: set, rule_signal_sets: List[set]) -> Dict[str, int]:
    full = partial = zero = 0
    for s in rule_signal_sets:
        inter = present_signals & s
        if len(inter) == len(s):
            full += 1
        elif len(inter) > 0:
            partial += 1
        else:
            zero += 1
    return {"full": full, "partial": partial, "zero": zero, "total_sets": len(rule_signal_sets)}

def main():
    ap = argparse.ArgumentParser(description="Stage 1 diagnostics: coverage & missing signals.")
    ap.add_argument("--answers", help="Path to answers JSON (exported from frontend).", default=None)
    args = ap.parse_args()

    # Locate core files in common folders
    questionnaire_path = find_file(["questionnaire.json", "questionnaire.schema.json"])
    rules_path = find_file(["rules-engine.json", "rules-engine.fixed.json", "rules.json"])

    errors = []
    if not questionnaire_path:
        errors.append("questionnaire.json not found in: ./, data/, backend/, configs/")
    if not rules_path:
        errors.append("rules-engine.json not found in: ./, data/, backend/, configs/")

    if errors:
        print("[ERROR] " + " | ".join(errors))
        print("Hint: if your files are elsewhere, run with explicit paths or move/copy them, e.g.:")
        print("  cp data/rules-engine.json ./rules-engine.json    # if it exists under data/")
        print("  cp data/questionnaire.json ./questionnaire.json  # if it exists under data/")
        sys.exit(1)

    # Load JSONs
    try:
        schema = load_json(questionnaire_path)
    except Exception as e:
        print(f"[ERROR] Failed to read questionnaire: {questionnaire_path} ({e})")
        sys.exit(1)

    try:
        rules = load_json(rules_path)
    except Exception as e:
        print(f"[ERROR] Failed to read rules engine: {rules_path} ({e})")
        sys.exit(1)

    # Load answers
    answers_path = args.answers or os.path.join(ROOT, "answers.local.json")
    if os.path.exists(answers_path):
        try:
            answers = load_json(answers_path)
        except Exception as e:
            print(f"[WARN] answers file invalid: {e}")
            answers = {}
    else:
        print("[INFO] No answers file found, proceeding with empty answers.")
        answers = {}

    # If file contains {"answers": {...}} take the inner object
    if isinstance(answers, dict) and "answers" in answers and isinstance(answers["answers"], dict):
        answers = answers["answers"]

    # Compute coverage
    cov = answer_coverage(schema, answers if isinstance(answers, dict) else {})

    # Importance of signals by frequency in rules
    freq = count_signal_frequency_in_rules(rules)
    top_missing = []
    for sig in cov["missing_signal_names"]:
        top_missing.append({
            "signal": sig,
            "approx_importance": freq.get(sig, 0),
        })
    top_missing.sort(key=lambda x: (-x["approx_importance"], x["signal"]))

    # Potential matches (heuristic)
    present_signals = set(cov.get("covered_signal_names", []))
    rule_signal_sets = extract_rule_signal_sets(rules)
    potential = estimate_potential_rule_matches(present_signals, rule_signal_sets)

    report = OrderedDict([
        ("paths", {
            "questionnaire": questionnaire_path,
            "rules_engine": rules_path,
            "answers": answers_path
        }),
        ("coverage", cov),
        ("signal_frequency_top5", sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:5]),
        ("top_missing_signals", top_missing[:10]),
        ("potential_rule_matches", potential),
    ])

    # Save report
    os.makedirs(os.path.dirname(REPORT_OUT), exist_ok=True)
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Console summary
    print("\n=== Stage 1 Diagnostics ===")
    print(f"Questions answered: {cov['questions_answered']} / {cov['questions_total']}  ({cov['questions_coverage_pct']:.1f}%)")
    print(f"Signals covered:   {cov['signals_covered']} / {cov['signals_total']}    ({cov['signals_covered_pct']:.1f}%)")
    print(f"Potential rule matches (heuristic): full={potential['full']}, partial={potential['partial']}, zero={potential['zero']} (of {potential['total_sets']})")
    if top_missing:
        print("\nTop missing signals by importance:")
        for item in top_missing[:8]:
            print(f"  - {item['signal']}  (importance≈{item['approx_importance']})")
    print(f"\nFull JSON report written to: {REPORT_OUT}\n")

if __name__ == "__main__":
    main()
