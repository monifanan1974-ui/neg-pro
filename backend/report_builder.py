# backend/report_builder.py
# Stable HTML via report.html template; data from JSON Playbooks;
# LLM writes only two small slots: executive_summary + strategic_highlights.

from __future__ import annotations
import os, re, json
from datetime import date, timedelta
from typing import Dict, Any, Optional, List

# ---- optional LLM (slots only) ----
try:
    import openai
    _OPENAI_OK = True
except Exception:
    _OPENAI_OK = False

def _biz_days_from_today(n: int) -> date:
    # simple approx: skip weekends
    d = date.today()
    added = 0
    while added < n:
        d = d + timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d

def _format_by(d: date) -> str:
    return d.strftime("%b %d, %Y")

def _to_number(x):
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return float(x)
        s=str(x).replace(",","")
        if s.endswith("k") or s.endswith("K"):
            return float(s[:-1]) * 1000.0
        return float(s)
    except Exception:
        return None

def _fmt_gbp(n):
    if n is None: return "—"
    v=round(float(n)/100.0)*100.0
    return f"£{int(round(v/1000.0))}k" if v>=1000 else f"£{int(v)}"

def _answers_snapshot(engine_out: Dict[str,Any]) -> Dict[str,Any]:
    prof=(engine_out.get("debug") or {}).get("profile") or {}
    ans=(engine_out.get("answers") or {})
    return {
        "role": prof.get("role") or ans.get("target_title") or "",
        "country": prof.get("country") or ((ans.get("culture") or {}).get("country")) or "UK",
        "industry": prof.get("industry") or ans.get("industry") or "",
        "seniority": prof.get("seniority") or ans.get("seniority") or "",
        "persona": prof.get("persona") or ans.get("counterpart_persona") or "Analyst / Data-driven"
    }

def _numbers_from_engine(engine_out: Dict[str,Any]) -> Dict[str,Any]:
    prof=(engine_out.get("debug") or {}).get("profile") or {}
    m=(engine_out.get("metrics") or {})
    # Fallback to answers if metrics not provided
    if not m:
        ans = engine_out.get("answers") or {}
        monetary = ((ans.get("goals") or {}).get("monetary")) or {}
        m = {
            "range_low": monetary.get("range_low"),
            "range_high": monetary.get("range_high"),
            "anchor_value": monetary.get("target_salary"),
        }
    country=(prof.get("country") or "UK").strip()
    low=_to_number(m.get("range_low")); high=_to_number(m.get("range_high")); anchor=_to_number(m.get("anchor_value"))
    median=(low+high)/2.0 if (low is not None and high is not None) else (anchor or low or high)
    return {"country": country, "p25":low, "median":median, "p75":high, "anchor":anchor}

def _load_template_html() -> str:
    for p in [
        os.path.join(os.getcwd(),"report.html"),
        os.path.join(os.path.dirname(__file__),"report.html"),
        os.path.join(os.path.dirname(__file__),"templates","report.html"),
    ]:
        try:
            with open(p,"r",encoding="utf-8") as f: return f.read()
        except Exception:
            continue
    raise FileNotFoundError("report.html template not found (backend/templates/).")

def _inject_report_data(tpl: str, data: Dict[str,Any]) -> str:
    blob=json.dumps(data, ensure_ascii=False)
    pat=re.compile(r"const\s+reportData\s*=\s*\{.*?\};", re.S)
    rep=f"const reportData = {blob};"
    if pat.search(tpl): return pat.sub(rep, tpl, count=1)
    return tpl + f"\n<script>\n{rep}\n</script>\n"

def make_chart_data(engine_out: Dict[str,Any], extras: Optional[Dict[str,Any]]=None)->Dict[str,Any]:
    m=(engine_out.get("metrics") or {})
    if not m:
        ans = engine_out.get("answers") or {}
        monetary = ((ans.get("goals") or {}).get("monetary")) or {}
        m = {"range_low": monetary.get("range_low"), "range_high": monetary.get("range_high"), "anchor_value": monetary.get("target_salary")}
    return {"currency":"£","salary":{"low":_to_number(m.get("range_low")),"anchor":_to_number(m.get("anchor_value")),"high":_to_number(m.get("range_high"))}}

# ---- Playbook loader (lightweight inline to keep file self-contained) ----
def select_best(profile: Dict[str,Any]) -> Dict[str,Any]:
    # Minimal demo playbook; real project can load from files.
    persona = (profile.get("persona") or "").lower()
    country = (profile.get("country") or "UK")
    if country.upper() in ("UK","GB","GBR","UNITED KINGDOM"):
        A = {
            "label": "Scenario A — Senior Editor (London, GBP)",
            "p25": "£36k", "median": "£48k", "p75": "£58k",
            "anchor": "£58k", "floor": "£50k",
            "fallback": "£52–54k + 6-month review to £58k on KPIs."
        }
        B = {
            "label": "Scenario B — Expanded Scope (Lead/Head)",
            "p25": "£60k", "median": "£68k", "p75": "£75k",
            "anchor": "£71k", "floor": "£64k",
            "fallback": "£66–68k + 6-month KPI review."
        }
    else:
        A = {"label":"Scenario A","p25":"—","median":"—","p75":"—","anchor":"—","floor":"—","fallback":""}
        B = {}
    summary = "Anchoring near the 75th percentile with two quantified proof points. Expect a decision within 5 business days."
    highlights = [
        "Anchor high within reason",
        "Invite alignment on a shared goal"
    ]
    return {"marketA":A,"marketB":B,"summary":summary,"highlights":highlights}

def _fmt_market_block(A: Dict[str,Any]) -> Dict[str,Any]:
    return {
        "label": A.get("label","Scenario A"),
        "p25": _fmt_gbp(_to_number(A.get("p25"))),
        "median": _fmt_gbp(_to_number(A.get("median"))),
        "p75": _fmt_gbp(_to_number(A.get("p75"))),
        "anchor": _fmt_gbp(_to_number(A.get("anchor"))),
        "floor": _fmt_gbp(_to_number(A.get("floor"))),
        "fallback": A.get("fallback","")
    }

def _build_report_data(engine_out: Dict[str,Any], extras: Optional[Dict[str,Any]]) -> Dict[str,Any]:
    profile = _answers_snapshot(engine_out)
    playbook = select_best(profile)
    A_raw = (playbook.get("marketA") or {})
    B_raw = (playbook.get("marketB") or {})
    user_nums = _numbers_from_engine(engine_out)
    A_merged = {
        "label": A_raw.get("label") or "Scenario A",
        "p25": user_nums["p25"] if user_nums["p25"] is not None else A_raw.get("p25"),
        "median": user_nums["median"] if user_nums["median"] is not None else A_raw.get("median"),
        "p75": user_nums["p75"] if user_nums["p75"] is not None else A_raw.get("p75"),
        "anchor": user_nums["anchor"] if user_nums["anchor"] is not None else A_raw.get("anchor"),
        "floor": A_raw.get("floor"),
        "fallback": A_raw.get("fallback","")
    }
    A_fmt = _fmt_market_block(A_merged)
    B_fmt = _fmt_market_block(B_raw) if B_raw else {"label":"Scenario B","p25":"—","median":"—","p75":"—","anchor":"—","floor":"—","fallback":"—"}

    by = _format_by(_biz_days_from_today(5))
    data = {
        "meta": {
            "region": profile.get("country","UK"),
            "currencySymbol": "£",
            "date": _format_by(date.today()),
            "counterpartPersona": profile.get("persona","neutral"),
            "yourPosture": "Warm, data-led"
        },
        "marketA": A_fmt,
        "marketB": B_fmt,
        "useScenarioB": False,
        "summary": playbook.get("summary",""),
        "highlights": playbook.get("highlights", []),
        "kpis": [
            {"label":"Decision window","value":"5 days","sub":"deadline shown below"},
            {"label":"Currency","value":"GBP (£)","sub":"keep consistent"},
            {"label":"Persona","value": profile.get("persona","neutral"), "sub":"aligned"}
        ],
        "evidence": [],
        "pairs": [],
        "trades": [],
        "batna": {"scenarioA_floor": A_fmt.get("floor"), "scenarioB_floor": B_fmt.get("floor"), "days": 5, "deadline": by, "plan": ""},
        "sources": []
    }

    # extras slots
    extras = extras or {}
    data["priorities"] = extras.get("priorities") or ["Salary","Title","Flexibility"]
    data["readiness"] = int(extras.get("readiness") or 70)

    return data

def build_report_html(engine_out: Dict[str,Any], extras: Optional[Dict[str,Any]] = None) -> Dict[str,Any]:
    data = _build_report_data(engine_out, extras)
    tpl = _load_template_html()
    html = _inject_report_data(tpl, data)
    return {"html": html, "chart_data": make_chart_data(engine_out, extras), "engine": "template+playbook+slots"}
