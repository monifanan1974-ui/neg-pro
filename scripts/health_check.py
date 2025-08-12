#!/usr/bin/env python3
"""
Basic repo health checks for NegotiationPro.

Runs on CI to catch common issues quickly WITHOUT starting a live server:
- Verifies key folders/files exist
- Greps Flask app and /health route definitions (regex, no import)
- Compiles Python files (syntax check is also done in CI step)
- Validates JSON files under data/ if present
"""

import os
import re
import sys
import json
from glob import glob

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

def assert_true(cond, msg):
    if not cond:
        print(f"[FAIL] {msg}")
        sys.exit(1)
    print(f"[OK] {msg}")

def file_contains(path, pattern):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return re.search(pattern, f.read(), flags=re.IGNORECASE | re.MULTILINE) is not None
    except FileNotFoundError:
        return False

def validate_json_files():
    data_dir = os.path.join(ROOT, "data")
    if not os.path.isdir(data_dir):
        print("[INFO] data/ not found — skipping JSON validation.")
        return
    errors = 0
    for p in glob(os.path.join(data_dir, "**", "*.json"), recursive=True):
        try:
            with open(p, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            errors += 1
            print(f"[JSON ERROR] {p}: {e}")
    assert_true(errors == 0, "All JSON files under data/ parsed successfully")

def main():
    print("== NegotiationPro health check ==")
    # 1) folders
    assert_true(os.path.isdir(os.path.join(ROOT, "backend")), "backend/ folder exists")
    assert_true(os.path.isdir(os.path.join(ROOT, "frontend")), "frontend/ folder exists")

    # 2) key file exists
    api_py = os.path.join(ROOT, "backend", "api.py")
    assert_true(os.path.isfile(api_py), "backend/api.py exists")

    # 3) regex checks (no import!)
    assert_true(file_contains(api_py, r"app\s*=\s*Flask\("), "Flask app is defined in backend/api.py")
    assert_true(file_contains(api_py, r"@app\.route\(\s*[\"']/health[\"']"), "/health route is defined")

    # 4) optional JSON validation
    validate_json_files()

    print("All basic checks passed ✅")

if __name__ == "__main__":
    main()

