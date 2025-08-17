# scripts/diag_stage1_helpers.py
# Utilities for Stage 1 diagnostics:
# 1) Print mapping of export.signal -> question_id (+ question text).
# 2) Generate an answers skeleton JSON with all signal-bearing questions.

from __future__ import annotations
import json, os, sys
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUESTIONNAIRE_PATHS = [
    os.path.join(ROOT, "questionnaire.json"),
    os.path.join(ROOT, "data", "questionnaire.json"),
    os.path.join(ROOT, "backend", "questionnaire.json"),
    os.path.join(ROOT, "configs", "questionnaire.json"),
]

def _ensure_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

def _load_schema() -> Dict[str, Any]:
    for p in QUESTIONNAIRE_PATHS:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    print("[ERROR] questionnaire.json not found in common paths.")
    sys.exit(1)

def _collect_questions(schema: dict) -> List[dict]:
    phases = _ensure_list(schema.get("phases"))
    out: List[dict] = []
    for ph in phases:
        out.extend(_ensure_list(ph.get("questions")))
    return out

def _signals_map(schema: dict) -> Dict[str, Dict[str, str]]:
    """
    Returns { signal_name: { 'id': question_id, 'question': question_text } }
    """
    out: Dict[str, Dict[str, str]] = {}
    for q in _collect_questions(schema):
        qid = q.get("id")
        export_meta = (q.get("export") or {})
        sig = export_meta.get("signal")
        if sig and qid:
            out[sig] = {"id": qid, "question": q.get("question", "")}
    return out

def cmd_print_map():
    schema = _load_schema()
    smap = _signals_map(schema)
    print(json.dumps(smap, ensure_ascii=False, indent=2))

def cmd_make_skeleton(out_path: str):
    schema = _load_schema()
    smap = _signals_map(schema)
    answers = {}
    # initialize with empty values so you can fill in
    for sig, meta in smap.items():
        qid = meta["id"]
        answers[qid] = ""  # empty; fill later
    payload = {"answers": answers}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] Wrote answers skeleton to: {out_path}")

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Helpers for Stage 1 diagnostics.")
    ap.add_argument("--print-map", action="store_true", help="Print signal → question_id map (JSON).")
    ap.add_argument("--make-skeleton", metavar="PATH", help="Write an answers skeleton JSON to PATH.")
    args = ap.parse_args()

    if args.print_map:
        cmd_print_map()
        return
    if args.make_skeleton:
        cmd_make_skeleton(args.make_skeleton)
        return

    print("Usage examples:")
    print("  python scripts/diag_stage1_helpers.py --print-map")
    print("  python scripts/diag_stage1_helpers.py --make-skeleton answers.local.json")

if __name__ == "__main__":
    main()
