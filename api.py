בטח, הבנתי את הנקודה. אתה מסכים עם ההיגיון שלי, אבל רוצה שנגיע ישר לפתרון הסופי בלי לעבור דרך שלבי האבחון הנוספים. מקובל עליי.

בוא נניח שהשינוי בקובץ api.py אכן לא נשמר כראוי או שיש בעיה אחרת בסביבה, ונגיש פתרון מקיף יותר שמתמודד עם כל הבעיות בנתיבי הייבוא בבת אחת.

הבעיה המרכזית בפרויקטים של פייתון עם תיקיות משנה היא שצריך "ליידע" את פייתון על מבנה הפרויקט. יש שתי דרכים לעשות זאת:

תיקון הייבוא (Imports): לוודא שכל ייבוא מציין את הנתיב המלא מהתיקייה הראשית (למשל, from backend.module import ...).

הוספת קובץ __init__.py: יצירת קובץ ריק בשם __init__.py בכל תיקיית משנה הופכת אותה ל"חבילה" (package) שפייתון יכול לייבא ממנה.

הפתרון המלא משלב את שתי הגישות.

הפתרון המלא לבעיות הייבוא (Import)

בצע את הפעולות הבאות לפי הסדר.

פעולה מס' 1: ודא שקיים קובץ backend/__init__.py

הקובץ הזה חיוני. אם הוא לא קיים, צור אותו. הוא יכול להיות ריק לחלוטין.

צור קובץ חדש בנתיב: backend/__init__.py

השאר אותו ריק ושמור אותו.

פעולה מס' 2: החלף את כל תוכן הקובץ api.py

הקוד הבא כולל את תיקוני הנתיבים. הוא זהה לקוד מהתשובות הקודמות, אך חשוב לוודא שזו הגרסה המדויקת שרצה אצלך.

✅ עדכן את הקובץ api.py:

code
Python
download
content_copy
expand_less

--- START OF FILE api.py ---
# api.py
from __future__ import annotations
import os
import sys
from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS

# Add the project root to the Python path to help with module resolution
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(HERE)
sys.path.insert(0, ROOT)

DATA_DIR = os.path.join(ROOT, "data")
FRONTEND_DIR  = os.path.join(ROOT, "frontend")

# Corrected imports to include the 'backend' package prefix
from backend.engine_entrypoint import QuestionnaireEngine
from backend.feedback_store import FeedbackStore

# Serve static files from the frontend directory
app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)
feedback_store = FeedbackStore(data_dir=DATA_DIR)

# --- Static File Routing ---
@app.route('/')
def serve_root():
    """Serves the main index.html file."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    """Serves other static files like CSS, JS, or JSON."""
    return send_from_directory(app.static_folder, path)


# --- API Endpoints ---
@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "NegotiationPro API"}), 200

@app.post("/questionnaire/report")
def questionnaire_report():
    payload = request.get_json(silent=True) or {}
    answers = payload.get("questionnaire") or payload.get("answers") or {}
    if not isinstance(answers, dict) or not answers:
        return jsonify({"status": "error", "reason": "No answers provided in the expected format."}), 400

    engine = QuestionnaireEngine(debug=os.getenv("DEBUG", "true").lower() in ("1", "true", "yes"))
    result = engine.run(answers)
    http_status = 200 if (result.get("status") == "ok" and result.get("html")) else 500
    return jsonify(result), http_status

@app.post("/feedback")
def feedback():
    payload = request.get_json(silent=True) or {}
    feedback_store.add(payload)
    return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200

@app.get("/feedback/stats")
def feedback_stats():
    return jsonify({"status": "ok", "aggregate": feedback_store.aggregate()}), 200


# --- Main Execution ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "y")
    print("==== NegotiationPro API ====")
    print(f"Listening on http://localhost:{port} (Debug={debug})")
    print(f"Serving static files from: {FRONTEND_DIR}")
    app.run(host="0.0.0.0", port=port, debug=debug)

הוספתי גם הוספה של ספריית השורש לנתיב החיפוש של פייתון (sys.path.insert) כגיבוי, למקרה שסביבת העבודה שלך צריכה עזרה נוספת במציאת התיקיות.

פעולה מס' 3: תקן את הייבוא בתוך engine_entrypoint.py

זוהי הבעיה הבאה שהייתה צצה. קבצים בתוך backend צריכים לייבא אחד את השני עם נקודה (.) לפניהם, כדי לציין שהם באותה חבילה.

✅ עדכן את הקובץ backend/engine_entrypoint.py:

code
Python
download
content_copy
expand_less
IGNORE_WHEN_COPYING_START
IGNORE_WHEN_COPYING_END
--- START OF FILE backend/engine_entrypoint.py ---
# backend/engine_entrypoint.py
# Questionnaire → Engine glue.
# Maps answers using questionnaire_mapper, evaluates rules, and builds the HTML report.
from __future__ import annotations
import os, json, traceback, re
from typing import Dict, Any, Optional

# Use relative imports with '.' for modules within the same package
from .questionnaire_mapper import map_questionnaire_to_inputs
from .rule_engine_expansion import RuleEngineExpansion
from .report_builder import build_report_html

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA_DIR = os.path.join(ROOT, "data")

def _load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        traceback.print_exc()
        return {}

_num_re = re.compile(r"[\d\.]+")
def _to_num(x) -> Optional[float]:
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    s = str(x)
    m = _num_re.findall(s.replace(",", ""))
    if not m: return None
    try:
        return float(m[0])
    except Exception:
        return None

def _calc_readiness(mapped: Dict[str, Any]) -> int:
    score = 40
    if ((mapped.get("leverage") or {}).get("alternatives_BATNA")): score += 25
    ms = mapped.get("market_sources") or []
    score += min(20, max(0, (len(ms) - 1) * 10))
    proofs = (mapped.get("leverage") or {}).get("value_proofs") or []
    if len(proofs) >= 2: score += 15
    elif proofs: score += 7
    if ((mapped.get("leverage") or {}).get("time_constraints")): score += 5
    return max(35, min(95, score))

def _profile_slice(mapped: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "persona": (mapped.get("counterpart_persona") or "neutral"),
        "country": (mapped.get("culture") or {}).get("country") or "UK",
        "context_level": (mapped.get("culture") or {}).get("context_level") or "low",
        "power": mapped.get("counterpart_power") or "peer",
        "user_style": mapped.get("user_style") or "Analytical"
    }

def _metrics_from_mapped(mapped: Dict[str, Any]) -> Dict[str, Any]:
    m = (mapped.get("goals") or {}).get("monetary") or {}
    low = _to_num(m.get("range_low"))
    high = _to_num(m.get("range_high"))
    anchor = _to_num(m.get("target_salary"))
    # If only low/high exist, pick anchor near high (p75)
    if anchor is None and (low is not None or high is not None):
        anchor = high or low
    return {"range_low": low, "range_high": high, "anchor_value": anchor}

class QuestionnaireEngine:
    def __init__(self, kb_path: Optional[str] = None, schema_map_path: Optional[str] = None, debug: bool = False):
        self.debug = debug
        kb_path = kb_path or os.path.join(DATA_DIR, "super_kb.json")
        self.kb = _load_json(kb_path)
        self.rules = self.kb
        self.schema_map_path = schema_map_path or os.path.join(DATA_DIR, "schema_map.v127.json")

    def _load_schema_map(self) -> Dict[str, str]:
        m = _load_json(self.schema_map_path)
        return m if isinstance(m, dict) else {}

    def run(self, raw_answers: Dict[str, Any]) -> Dict[str, Any]:
        try:
            schema_map = self._load_schema_map()
            mapped = map_questionnaire_to_inputs(raw_answers or {}, schema_map=schema_map)

            # Evaluate rules (recommendations + tone overrides)
            rexp = RuleEngineExpansion(rules_data=self.rules, kb_root=self.kb)
            fired = rexp.evaluate_all(mapped)

            # Priorities / readiness
            priorities = (mapped.get("priorities_ranked") or ["salary","title","flexibility"])[:3]
            priorities = [str(x).strip().title() for x in priorities]
            readiness = _calc_readiness(mapped)

            # Build an engine_out object that report_builder expects
            engine_out = {
                "debug": {"profile": _profile_slice(mapped)},
                "answers": mapped,                 # so report builder can snapshot context
                "metrics": _metrics_from_mapped(mapped)  # for charts/market merge
            }

            rep = build_report_html(engine_out, extras={
                "priorities": priorities,
                "readiness": readiness,
                "fired_rules": fired
            })
            return {
                "status": "ok",
                "engine": "qengine",
                "html": rep.get("html"),
                "chart_data": rep.get("chart_data"),
                "rules_fired": fired,
                "profile": engine_out["debug"]["profile"]
            }
        except Exception as e:
            if self.debug:
                traceback.print_exc()
            return {"status": "error", "reason": f"{type(e).__name__}: {e}"}
מה לעשות עכשיו

ודא שקיים קובץ ריק בנתיב backend/__init__.py.

החלף את כל התוכן של api.py בקוד מפעולה מס' 2.

החלף את כל התוכן של backend/engine_entrypoint.py בקוד מפעולה מס' 3.

שמור את כל הקבצים.

הרץ את הפקודה בטרמינל: python api.py

אני בטוח שהפעם השגיאה תתקדם. סביר להניח שנקבל שגיאת ייבוא חדשה מקובץ אחר בתוך backend, וזה סימן שאנחנו מתקדמים בתיקון שרשרת הייבוא. שלח לי את הפלט החדש.
