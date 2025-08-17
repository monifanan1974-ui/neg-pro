#!/usr/bin/env python3
# smoke_test.py
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.engine_entrypoint import QuestionnaireEngine  # uses your engine
# If your engine expects data/ files, ensure they exist per your project

def minimal_answers_from_questionnaire(qfile: Path):
    with qfile.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    answers = {}
    for ph in schema.get("phases", []):
        for q in ph.get("questions", []):
            qid = q.get("id")
            typ = q.get("answerType")
            if not qid: 
                continue
            if typ == "single_choice":
                opts = q.get("options", [])
                if opts:
                    answers[qid] = opts[0].get("value")
            elif typ == "multiple_choice":
                opts = q.get("options", [])
                if opts:
                    answers[qid] = [opts[0].get("value")]
            elif typ == "rating_scale":
                answers[qid] = q.get("scaleMin", 1)
            else:
                answers[qid] = "test"
    return answers

def main():
    qfile = ROOT / "questionnaire.json"
    if not qfile.exists():
        print("ERROR: questionnaire.json not found", file=sys.stderr)
        sys.exit(2)

    # Build minimal answers (you can replace with a fixture file)
    answers = minimal_answers_from_questionnaire(qfile)

    engine = QuestionnaireEngine(debug=True)
    res = engine.run(answers)

    if res.get("status") != "ok":
        print(json.dumps(res, indent=2))
        print("SMOKE: engine status not ok", file=sys.stderr)
        sys.exit(1)

    html = res.get("html") or ""
    matched = res.get("matched_rules") or res.get("rules_matched") or []
    if not html.strip():
        print("SMOKE: empty HTML", file=sys.stderr)
        sys.exit(1)
    if isinstance(matched, list) and len(matched) == 0:
        print("SMOKE: no matched rules — check mappings/signals", file=sys.stderr)
        # still fail — we expect at least one hit
        sys.exit(1)

    print("SMOKE: OK")
    sys.exit(0)

if __name__ == "__main__":
    main()
