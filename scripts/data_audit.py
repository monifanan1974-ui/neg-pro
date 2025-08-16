# scripts/data_audit.py
# Simple, project-specific data auditor for ./data
# Usage: python scripts/data_audit.py

import json, os, csv, sys
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)

def summarize_json(name, obj):
    info = {"type": type(obj).__name__, "size": None, "keys": None}
    if isinstance(obj, list):
        info["size"] = len(obj)
        # guess item keys
        if obj and isinstance(obj[0], dict):
            key_counts = Counter()
            for it in obj[:200]:
                if isinstance(it, dict):
                    key_counts.update(it.keys())
            info["keys"] = [k for k,_ in key_counts.most_common()]
    elif isinstance(obj, dict):
        info["keys"] = list(obj.keys())
    return info

def check_super_kb(name, obj):
    issues = []
    if not isinstance(obj, dict):
        issues.append("❌ super_kb.json אמור להיות אוביקט JSON (dict).")
        return issues
    ca = obj.get("culture_advice", {})
    if not isinstance(ca, dict):
        issues.append("❌ 'culture_advice' חסר או לא אוביקט.")
    else:
        for bucket in ["high_context","low_context"]:
            arr = ca.get(bucket, [])
            if not isinstance(arr, list) or not arr:
                issues.append(f"⚠️ culture_advice.{bucket} ריק/חסר.")
            else:
                # duplicate hints?
                dup = [k for k,v in Counter([str(x).strip().lower() for x in arr]).items() if v>1]
                if dup:
                    issues.append(f"⚠️ {bucket}: יש כפילויות: {dup[:5]}")
    return issues

def check_playlets(name, obj):
    issues = []
    if not isinstance(obj, (list,dict)):
        issues.append("❌ simulation-playlets.json אמור להיות List או Dict עם רשימת playlets.")
        return issues
    items = obj if isinstance(obj,list) else obj.get("playlets",[])
    ids = []
    for it in items:
        if not isinstance(it, dict):
            issues.append("❌ פריט שאינו אוביקט.")
            continue
        pid = it.get("id")
        if not pid:
            issues.append("⚠️ playlet בלי id.")
        else:
            ids.append(pid)
        if "steps" not in it or not isinstance(it["steps"], (list,dict)):
            issues.append(f"⚠️ playlet {pid or '?'} ללא steps תקינים.")
    # id uniqueness
    dups = [k for k,v in Counter(ids).items() if v>1]
    if dups:
        issues.append(f"❌ מזהים כפולים: {dups}")
    return issues

def check_dilemmas(name, obj):
    issues = []
    items = obj if isinstance(obj,list) else obj.get("dilemmas",[])
    if not isinstance(items, list):
        issues.append("❌ user-dilemmas.json אמור להכיל רשימה.")
        return issues
    for it in items:
        if not isinstance(it, dict):
            issues.append("❌ פריט שאינו אוביקט.")
            continue
        if not it.get("id"):
            issues.append("⚠️ דילמה בלי id.")
        if not it.get("text"):
            issues.append(f"⚠️ דילמה {it.get('id','?')} בלי text.")
        if "recommended_actions" not in it:
            issues.append(f"⚠️ דילמה {it.get('id','?')} בלי recommended_actions.")
        if "mitigation" not in it:
            issues.append(f"⚠️ דילמה {it.get('id','?')} בלי mitigation.")
    return issues

def audit_file(path):
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    report = [f"📄 {name}"]
    if ext == ".json":
        obj, err = load_json(path)
        if err:
            report.append(f"❌ JSON לא תקין: {err}")
            return "\n".join(report)
        summary = summarize_json(name, obj)
        report.append(f"סוג: {summary['type']}, גודל/כמות פריטים: {summary.get('size')}, מפתחות: {summary.get('keys')}")
        # project-specific checks
        if name == "super_kb.json":
            for i in check_super_kb(name, obj): report.append(i)
        elif name == "simulation-playlets.json":
            for i in check_playlets(name, obj): report.append(i)
        elif name == "user-dilemmas.json":
            for i in check_dilemmas(name, obj): report.append(i)
        else:
            # generic: look for version/updated_at
            if isinstance(obj, dict):
                if "version" not in obj:
                    report.append("ℹ️ חסר 'version' (מומלץ).")
                if "updated_at" not in obj:
                    report.append("ℹ️ חסר 'updated_at' (מומלץ).")
    elif ext in [".csv"]:
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(next(reader) for _ in range(1))  # header only
            report.append(f"CSV מזוהה. כותרות (שורה ראשונה): {rows[0] if rows else '—'}")
        except Exception as e:
            report.append(f"❌ CSV לא קריא: {e}")
    else:
        try:
            size = os.path.getsize(path)
            report.append(f"קובץ {ext or 'ללא סיומת'} ({size} bytes). בדיקה ידנית מומלצת.")
        except:  # noqa
            report.append("קובץ לא מזוהה (בדיקה ידנית).")
    return "\n".join(report)

def main():
    if not os.path.isdir(DATA_DIR):
        print(f"❌ לא נמצאה תיקיית data בנתיב: {DATA_DIR}")
        sys.exit(1)
    files = sorted([os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR)])
    if not files:
        print("ℹ️ התיקייה ריקה.")
        return
    print(f"🔎 בודק {len(files)} קבצים בתיקיית data:\n")
    for p in files:
        if os.path.isdir(p): 
            print(f"📁 תיקייה פנימית: {os.path.basename(p)} — לדלג/לבדוק ידנית.\n")
            continue
        print(audit_file(p))
        print("-"*60)

if __name__ == "__main__":
    main()
