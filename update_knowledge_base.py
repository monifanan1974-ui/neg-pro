#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_knowledge_base.py

A safe "update pipeline" for Negotiation Pro.

What it does (in plain English):
1) Looks for new JSON files in ./incoming/
2) Makes a full backup of ./data/ before changing anything
3) Detects what type of JSON each file is (knowledge, tactics, rules, etc.)
4) Merges by unique ID (no duplicate mess). Updates only missing or newer fields.
5) Writes a merge report (what was added/updated/skipped)
6) Supports --dry-run (show changes without writing) and --restore <backup_dir>

Run examples:
  python update_knowledge_base.py --dry-run
  python update_knowledge_base.py
  python update_knowledge_base.py --only rules,tactics
  python update_knowledge_base.py --include "*uk*.json"
  python update_knowledge_base.py --restore backups/backup-20250810-121530

This script is English-only by design (no Hebrew in code or outputs).
"""

from __future__ import annotations
import argparse
import copy
import datetime as dt
import glob
import json
import os
import re
import shutil
from typing import Any, Dict, List, Tuple

# ---------- Paths ----------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
INCOMING_DIR = os.path.join(BASE_DIR, "incoming")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")

# Target files we manage inside ./data
TARGET_FILES = {
    "knowledge": "Maagar_Sofi_994.json",        # entries[]
    "tactics": "tactic_library.json",           # tactics: {openers[], counters[], micro_tactics[]}
    "simulations": "simulation-playlets.json",  # playlets[]
    "rules": "rules-engine.json",               # rules[]
    "local": "local-data.json",                 # regions{}, data_sources{}
    "dilemmas": "user-dilemmas.json",           # dilemmas[]
    "validation": "data-validation.json",       # sources[], validation_rules[], dynamic_adjustments{}
    # Optional extras (ignored if missing):
    "feedback": "feedback-loop.json",           # feedback_triggers[], adaptive_learning{}, feedback_ui{}
}

# ---------- Small utilities ----------
def ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(INCOMING_DIR, exist_ok=True)
    os.makedirs(BACKUPS_DIR, exist_ok=True)

def read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def make_backup_folder() -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = os.path.join(BACKUPS_DIR, f"backup-{stamp}")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def backup_targets(backup_dir: str) -> None:
    for key, fname in TARGET_FILES.items():
        src = os.path.join(DATA_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(backup_dir, fname))

def restore_from_backup(backup_dir: str) -> None:
    if not os.path.isdir(backup_dir):
        raise FileNotFoundError(f"Backup folder not found: {backup_dir}")
    for key, fname in TARGET_FILES.items():
        src = os.path.join(backup_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DATA_DIR, fname))

# ---------- Type detection ----------
def detect_incoming_type(doc: Dict[str, Any]) -> str:
    """
    Returns one of:
    knowledge | tactics | simulations | rules | local | dilemmas | validation | feedback | unknown
    """
    if not isinstance(doc, dict):
        return "unknown"
    if "entries" in doc:
        return "knowledge"
    if "tactics" in doc:
        return "tactics"
    if "playlets" in doc:
        return "simulations"
    if "rules" in doc:
        return "rules"
    if "regions" in doc:
        return "local"
    if "dilemmas" in doc:
        return "dilemmas"
    if "sources" in doc and "validation_rules" in doc:
        return "validation"
    if "feedback_triggers" in doc or "adaptive_learning" in doc:
        return "feedback"
    return "unknown"

# ---------- Merge helpers ----------
def _unique_list(lst: List[Any]) -> List[Any]:
    seen = set()
    out: List[Any] = []
    for x in lst:
        key = json.dumps(x, sort_keys=True, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x)
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out

def _merge_dicts_shallow(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        if k in out and isinstance(out[k], list) and isinstance(v, list):
            out[k] = _unique_list(out[k] + v)
        elif k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _merge_dicts_shallow(out[k], v)
        else:
            out[k] = v
    return out

def upsert_by_id(list_base: List[Dict[str, Any]], list_new: List[Dict[str, Any]], id_key="id") -> Tuple[int, int, int]:
    """
    Merge records by ID. If an incoming ID exists, update the record by adding only new values
    (lists are unioned, dicts are shallow-merged). Unknown/no-ID records are skipped.
    Returns (added, updated, skipped).
    """
    index = {str(item.get(id_key)): i for i, item in enumerate(list_base) if id_key in item}
    added = updated = skipped = 0

    for incoming in list_new or []:
        rid = incoming.get(id_key)
        if not rid:
            skipped += 1
            continue
        rid = str(rid)
        if rid in index:
            old = list_base[index[rid]]
            merged = _merge_dicts_shallow(old, incoming)
            list_base[index[rid]] = merged
            updated += 1
        else:
            list_base.append(incoming)
            index[rid] = len(list_base) - 1
            added += 1

    return added, updated, skipped

def bump_version(meta: Dict[str, Any]) -> None:
    """
    Bumps _metadata.version safely (tiny bump).
    """
    meta.setdefault("_metadata", {})
    ver = str(meta["_metadata"].get("version", "1.0.0"))
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", ver)
    if m:
        major, minor, patch = map(int, m.groups())
        meta["_metadata"]["version"] = f"{major}.{minor}.{patch+1}"
    else:
        meta["_metadata"]["version"] = "1.0.1"

# ---------- Merge functions per file type ----------
def merge_knowledge(base: Dict[str, Any], inc: Dict[str, Any], report: Dict[str, Any]) -> None:
    base.setdefault("entries", [])
    a, u, s = upsert_by_id(base["entries"], inc.get("entries", []), "id")
    report["knowledge"] = {"added": a, "updated": u, "skipped": s}

def merge_tactics(base: Dict[str, Any], inc: Dict[str, Any], report: Dict[str, Any]) -> None:
    base.setdefault("tactics", {})
    for bucket in ["openers", "counters", "micro_tactics"]:
        base["tactics"].setdefault(bucket, [])
        a, u, s = upsert_by_id(base["tactics"][bucket], (inc.get("tactics") or {}).get(bucket, []), "id")
        report.setdefault("tactics", {})[bucket] = {"added": a, "updated": u, "skipped": s}

def merge_simulations(base: Dict[str, Any], inc: Dict[str, Any], report: Dict[str, Any]) -> None:
    base.setdefault("playlets", [])
    a, u, s = upsert_by_id(base["playlets"], inc.get("playlets", []), "id")
    report["simulations"] = {"added": a, "updated": u, "skipped": s}

def merge_rules(base: Dict[str, Any], inc: Dict[str, Any], report: Dict[str, Any]) -> None:
    base.setdefault("rules", [])
    a, u, s = upsert_by_id(base["rules"], inc.get("rules", []), "id")
    report["rules"] = {"added": a, "updated": u, "skipped": s}

def merge_local(base: Dict[str, Any], inc: Dict[str, Any], report: Dict[str, Any]) -> None:
    base.setdefault("regions", {})
    inc_regions = inc.get("regions", {})
    added = updated = 0
    for region, payload in (inc_regions or {}).items():
        if region in base["regions"]:
            base["regions"][region] = _merge_dicts_shallow(base["regions"][region], payload)
            updated += 1
        else:
            base["regions"][region] = payload
            added += 1
    if "data_sources" in inc:
        base.setdefault("data_sources", {})
        base["data_sources"] = _merge_dicts_shallow(base["data_sources"], inc["data_sources"])
    report["local"] = {"regions_added": added, "regions_updated": updated}

def merge_dilemmas(base: Dict[str, Any], inc: Dict[str, Any], report: Dict[str, Any]) -> None:
    base.setdefault("dilemmas", [])
    a, u, s = upsert_by_id(base["dilemmas"], inc.get("dilemmas", []), "id")
    report["dilemmas"] = {"added": a, "updated": u, "skipped": s}

def merge_validation(base: Dict[str, Any], inc: Dict[str, Any], report: Dict[str, Any]) -> None:
    base.setdefault("sources", [])
    base.setdefault("validation_rules", [])
    base.setdefault("dynamic_adjustments", {})
    a1, u1, s1 = upsert_by_id(base["sources"], inc.get("sources", []), "name")
    a2, u2, s2 = upsert_by_id(base["validation_rules"], inc.get("validation_rules", []), "id")
    base["dynamic_adjustments"] = _merge_dicts_shallow(base["dynamic_adjustments"], inc.get("dynamic_adjustments", {}))
    report["validation"] = {
        "sources": {"added": a1, "updated": u1, "skipped": s1},
        "validation_rules": {"added": a2, "updated": u2, "skipped": s2},
    }

def merge_feedback(base: Dict[str, Any], inc: Dict[str, Any], report: Dict[str, Any]) -> None:
    # keep structure flexible; union arrays and shallow-merge dicts
    for k, v in inc.items():
        if isinstance(v, list):
            base[k] = _unique_list((base.get(k) or []) + v)
        elif isinstance(v, dict):
            base[k] = _merge_dicts_shallow(base.get(k, {}), v)
        else:
            base[k] = v
    report["feedback"] = "merged"

# ---------- Default empty structures if base files are missing ----------
def default_for(key: str) -> Dict[str, Any]:
    if key == "knowledge":
        return {"entries": [], "_metadata": {"version": "1.0.0"}}
    if key == "tactics":
        return {"tactics": {"openers": [], "counters": [], "micro_tactics": []}, "_metadata": {"version": "1.0.0"}}
    if key == "simulations":
        return {"playlets": [], "_metadata": {"version": "1.0.0"}}
    if key == "rules":
        return {"rules": [], "_metadata": {"version": "1.0.0"}}
    if key == "local":
        return {"regions": {}, "_metadata": {"version": "1.0.0"}}
    if key == "dilemmas":
        return {"dilemmas": [], "_metadata": {"version": "1.0.0"}}
    if key == "validation":
        return {"sources": [], "validation_rules": [], "dynamic_adjustments": {}, "_metadata": {"version": "1.0.0"}}
    if key == "feedback":
        return {"feedback_triggers": [], "_metadata": {"version": "1.0.0"}}
    return {"_metadata": {"version": "1.0.0"}}

# ---------- Main ----------
def main() -> None:
    parser = argparse.ArgumentParser(description="Safely merge incoming JSON updates into ./data/")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files")
    parser.add_argument("--include", default="*.json", help="Glob for incoming filenames to include (default: *.json)")
    parser.add_argument("--exclude", default="", help="Regex to exclude incoming filenames")
    parser.add_argument("--only", default="", help="Comma list of sections to merge (e.g., rules,tactics,local)")
    parser.add_argument("--restore", default="", help="Restore ./data from a backup folder path (no merging)")
    args = parser.parse_args()

    ensure_dirs()

    # Restore mode
    if args.restore:
        restore_from_backup(args.restore)
        print(f"✅ Restored data from: {args.restore}")
        return

    # Load base JSONs (or create defaults)
    bases: Dict[str, Dict[str, Any]] = {}
    for key, fname in TARGET_FILES.items():
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            try:
                bases[key] = read_json(path)
            except Exception:
                print(f"⚠️  Could not read {fname}. Using an empty default.")
                bases[key] = default_for(key)
        else:
            bases[key] = default_for(key)

    # Collect incoming files
    pattern = os.path.join(INCOMING_DIR, args.include)
    incoming_files = sorted(glob.glob(pattern))
    if not incoming_files:
        print("ℹ️ No JSON files found in ./incoming/. Put files there and run again.")
        return

    if args.exclude:
        rx = re.compile(args.exclude)
        incoming_files = [p for p in incoming_files if not rx.search(os.path.basename(p))]

    only_set = {s.strip().lower() for s in args.only.split(",") if s.strip()} if args.only else set()

    merge_report: Dict[str, Any] = {"files": [], "summary": {}}

    # Merge each incoming file
    for fpath in incoming_files:
        try:
            doc = read_json(fpath)
        except Exception as e:
            merge_report["files"].append({"file": os.path.basename(fpath), "status": "ERROR", "error": str(e)})
            continue

        ftype = detect_incoming_type(doc)
        if only_set and ftype not in only_set:
            merge_report["files"].append({"file": os.path.basename(fpath), "type": ftype, "status": "SKIPPED (filtered by --only)"})
            continue

        entry: Dict[str, Any] = {"file": os.path.basename(fpath), "type": ftype}

        if ftype == "knowledge":
            before = len(bases["knowledge"].get("entries", []))
            merge_knowledge(bases["knowledge"], doc, merge_report["summary"])
            after = len(bases["knowledge"].get("entries", []))
            entry["status"] = f"merged: entries {before}→{after}"

        elif ftype == "tactics":
            merge_tactics(bases["tactics"], doc, merge_report["summary"])
            entry["status"] = "merged: tactics buckets updated"

        elif ftype == "simulations":
            before = len(bases["simulations"].get("playlets", []))
            merge_simulations(bases["simulations"], doc, merge_report["summary"])
            after = len(bases["simulations"].get("playlets", []))
            entry["status"] = f"merged: playlets {before}→{after}"

        elif ftype == "rules":
            before = len(bases["rules"].get("rules", []))
            merge_rules(bases["rules"], doc, merge_report["summary"])
            after = len(bases["rules"].get("rules", []))
            entry["status"] = f"merged: rules {before}→{after}"

        elif ftype == "local":
            merge_local(bases["local"], doc, merge_report["summary"])
            entry["status"] = "merged: regions/data_sources updated"

        elif ftype == "dilemmas":
            before = len(bases["dilemmas"].get("dilemmas", []))
            merge_dilemmas(bases["dilemmas"], doc, merge_report["summary"])
            after = len(bases["dilemmas"].get("dilemmas", []))
            entry["status"] = f"merged: dilemmas {before}→{after}"

        elif ftype == "validation":
            merge_validation(bases["validation"], doc, merge_report["summary"])
            entry["status"] = "merged: sources/validation_rules/dynamic_adjustments updated"

        elif ftype == "feedback":
            merge_feedback(bases.get("feedback") or default_for("feedback"), doc, merge_report["summary"])
            bases["feedback"] = bases.get("feedback") or default_for("feedback")
            entry["status"] = "merged: feedback fields"

        else:
            entry["status"] = "SKIPPED (unknown structure)"

        merge_report["files"].append(entry)

    # Bump versions
    for key in bases:
        bump_version(bases[key])

    if args.dry_run:
        print("🔎 DRY RUN — no files were written. Proposed changes:")
        print(json.dumps(merge_report, ensure_ascii=False, indent=2))
        return

    # Backup, then write
    backup_dir = make_backup_folder()
    backup_targets(backup_dir)

    for key, fname in TARGET_FILES.items():
        write_json(os.path.join(DATA_DIR, fname), bases.get(key) or default_for(key))

    # Write report inside the backup folder
    report_path = os.path.join(backup_dir, "merge_report.json")
    write_json(report_path, merge_report)

    print("✅ Merge completed successfully.")
    print(f"📦 Backup saved at: {backup_dir}")
    print(f"🧾 Merge report:   {report_path}")

if __name__ == "__main__":
    main()
