# backend/playbook_loader.py
# Load & select role/region playbooks from backend/packs/*.json

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

PLAYBOOK_DIR = None  # filled by _find_dir


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _find_dir() -> str:
    global PLAYBOOK_DIR
    if PLAYBOOK_DIR and os.path.isdir(PLAYBOOK_DIR):
        return PLAYBOOK_DIR
    here = os.path.dirname(__file__)
    for name in ("packs", "playbooks", "data_packs"):
        cand = os.path.join(here, name)
        if os.path.isdir(cand):
            PLAYBOOK_DIR = cand
            return cand
    PLAYBOOK_DIR = os.path.join(here, "packs")
    os.makedirs(PLAYBOOK_DIR, exist_ok=True)
    return PLAYBOOK_DIR


def _score(pack: Dict[str, Any], role: str, country: str, industry: str, seniority: str) -> int:
    meta = pack.get("meta") or {}
    score = 0

    role_keywords = [_norm(x) for x in meta.get("role_keywords", [])]
    if any(k in _norm(role) for k in role_keywords):
        score += 3

    regions = [_norm(x) for x in meta.get("regions", [])]
    if any(k in _norm(country) for k in regions):
        score += 2

    industries = [_norm(x) for x in meta.get("industries", [])]
    if any(k in _norm(industry) for k in industries):
        score += 1

    seniority_list = [_norm(x) for x in meta.get("seniority", [])]
    if any(k in _norm(seniority) for k in seniority_list):
        score += 1

    return score


def load_all() -> List[Dict[str, Any]]:
    base = _find_dir()
    out: List[Dict[str, Any]] = []
    for fn in sorted(os.listdir(base)):
        if fn.lower().endswith(".json"):
            p = os.path.join(base, fn)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["_source_path"] = p
                out.append(data)
            except Exception:
                continue
    return out


def select_best(inputs: Dict[str, Any]) -> Dict[str, Any]:
    packs = load_all()
    if not packs:
        return {"meta": {"id": "default"}}

    role = _norm(inputs.get("role") or inputs.get("target_title"))
    country = _norm(inputs.get("country"))
    industry = _norm(inputs.get("industry"))
    seniority = _norm(inputs.get("seniority"))

    best = None
    best_score = -1
    for p in packs:
        sc = _score(p, role, country, industry, seniority)
        if sc > best_score:
            best = p
            best_score = sc

    if best is None or best_score <= 0:
        for p in packs:
            if _norm((p.get("meta") or {}).get("id")) == "default":
                return p
        return packs[0]

    return best
