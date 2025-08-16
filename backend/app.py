# backend/app.py
from __future__ import annotations
import os, json, uuid, math
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Tuple
from flask import Flask, jsonify, request, send_from_directory, make_response, Response
from flask_cors import CORS

# ----- Optional PDF engine (WeasyPrint). Falls back gracefully if not installed. -----
try:
    from weasyprint import HTML  # pip install weasyprint
    _PDF_AVAILABLE = True
except Exception:
    _PDF_AVAILABLE = False

# ----- Paths -----
BACKEND_DIR  = Path(__file__).resolve().parent
ROOT_DIR     = BACKEND_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
REPORTS_DIR  = BACKEND_DIR / "reports"          # runtime cache (HTML by report_id)
SAVED_DIR    = BACKEND_DIR / "saved_reports"    # "save to profile" store
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SAVED_DIR.mkdir(parents=True, exist_ok=True)

BUILD = "negpro-backend-v9"
REPORTS: Dict[str, str] = {}  # in-memory: report_id -> HTML

def _nocache(resp: Response) -> Response:
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

def _json(data: Any, code: int = 200) -> Response:
    return _nocache(make_response(jsonify(data), code))

def _find_questionnaire() -> Path | None:
    candidates = [
        ROOT_DIR / "questionnaire.json",
        BACKEND_DIR / "questionnaire.json",
        FRONTEND_DIR / "questionnaire.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

# optional: try to use your real engine if present
def _make_engine():
    try:
        from .engine_entrypoint import QuestionnaireEngine  # your integration point
        return QuestionnaireEngine(debug=False)
    except Exception:
        return None

ENGINE = _make_engine()

# ---------- OpenAI Enhancer (optional) ----------
def enhance_with_openai(html_content: str) -> str:
    """
    If OPENAI_API_KEY exists:
      - Smooth, humanize, and slightly restructure the given HTML content.
    If not present or fails:
      - Return the original html_content unchanged.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return html_content
    try:
        import openai
        openai.api_key = api_key
        prompt = (
            "You are a professional negotiation strategist and copywriter.\n"
            "Take the following HTML report content and rewrite it in smooth, premium, human-friendly language.\n"
            "Preserve the facts and intent. Keep valid HTML structure (<h3>, <ul>, <p>, etc.).\n\n"
            f"{html_content}"
        )
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You improve and humanize HTML negotiation reports."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        return resp.choices[0].message["content"]
    except Exception as e:
        print(f"[OpenAI Enhancement Skipped] {e}")
        return html_content

# ---------- Helpers: market range ----------
def _derive_range(low: float|None, high: float|None) -> Tuple[int|None,int|None,int|None,int|None,int|None]:
    """
    Returns (p25, median, p75, anchor, floor) derived from low/high.
    If values missing, returns None placeholders (section will hide gracefully).
    """
    if not (isinstance(low,(int,float)) and isinstance(high,(int,float)) and high>0 and low>0 and high>=low):
        return (None, None, None, None, None)
    p25   = int(round(low + 0.25*(high-low)))
    median= int(round((low+high)/2))
    p75   = int(round(low + 0.75*(high-low)))
    anchor= int(round(p75 + 0.07*(high-low)))  # slightly above p75 as opening anchor
    floor = int(round(low - 0.05*(high-low)))  # walk-away-ish
    return (p25, median, p75, anchor, floor)

# ---------- Premium HTML shell (self-contained, aligns with your theme) ----------
def _html_shell(inner_html: str, title: str = "Strategic Negotiation Report") -> str:
        return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{title}</title>
<style>
    :root {{{{
        --bg:#0b1220; --panel:#151b2d; --ink:#e8ecff; --muted:#9FB1D9;
        --border:#28304a; --brand:#6EA8FF; --brand2:#7BF1A8; --accent:#A78BFA;
        --radius:18px; --shadow: 0 10px 28px rgba(0,0,0,.28);
    }}}}
    html,body{{{{height:100%}}}} body{{{{
        margin:0; background: radial-gradient(1200px 700px at 80% -10%, rgba(110,168,255,0.10), transparent 60%),
                                                 radial-gradient(900px 900px at -20% 10%, rgba(167,139,250,0.08), transparent 55%), var(--bg);
        color:var(--ink); font-family: Inter, system-ui, Segoe UI, Arial; line-height:1.55; padding:28px;
    }}}}
    .wrap{{{{max-width:1120px;margin:0 auto}}}}
    .card{{{{background:linear-gradient(180deg, rgba(21,27,45,.92), rgba(11,18,32,.86));
                 border:1px solid var(--border);border-radius:22px;padding:22px;box-shadow:var(--shadow)}}}}
    h1{{{{margin:0 0 10px 0;font-size:28px}}}} h2,h3{{{{margin:.25rem 0 .5rem 0}}}}
    .meta{{{{color:var(--muted);font-size:13px;margin-bottom:14px}}}}
    .grid{{{{display:grid;gap:18px;grid-template-columns: 1.1fr .9fr}}}}
    @media (max-width: 900px){{{{.grid{{{{grid-template-columns:1fr}}}}}}}}
    /* chips */
    .chips{{{{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}}}}
    .chip{{{{background:#0f1729;border:1px solid var(--border);padding:6px 10px;border-radius:999px;font-size:12px;color:var(--muted)}}}}
    /* range list */
    .list{{{{display:flex;flex-direction:column;gap:10px}}}}
    .row{{{{display:grid;grid-template-columns:140px 1fr 70px;gap:10px;align-items:center}}}}
    .pill{{{{background:#10182a;border:1px solid var(--border);padding:10px 12px;border-radius:14px;color:var(--muted)}}}}
    .bar{{{{position:relative;height:10px;background:#0e1526;border-radius:999px;overflow:hidden;border:1px solid var(--border)}}}}
    .fill{{{{position:absolute;inset:0 0 0 0;transform:scaleX(0);transform-origin:left;animation:grow .9s ease forwards}}}}
    @keyframes grow{{{{to{{{{transform:scaleX(var(--p))}}}}}}}}
    .k{{{{
        background:linear-gradient(90deg, var(--brand), var(--brand2));
        mask:linear-gradient(90deg, #000 50%, rgba(0,0,0,.5) 100%);
        -webkit-mask:linear-gradient(90deg, #000 50%, rgba(0,0,0,.5) 100%);
    }}}}
    .actions{{{{display:flex;gap:10px;margin-top:18px}}}}
    .btn{{{{appearance:none;border:1px solid var(--border);background:#0f1729;color:var(--ink);
             border-radius:12px;padding:10px 14px;cursor:pointer;font-weight:700}}}}
    .btn:hover{{{{filter:brightness(1.05)}}}}
    .section{{{{margin-top:16px}}}}
    details summary{{{{cursor:pointer;color:var(--muted)}}}}
    table{{{{width:100%;border-collapse:collapse}}}} td,th{{{{border-bottom:1px solid var(--border);padding:8px;text-align:right}}}}
</style>
<script>
    // Animate bars based on data-range attributes
    document.addEventListener('DOMContentLoaded', ()=>{{
        document.querySelectorAll('[data-p]').forEach(el=>{{
            const p = Math.max(0, Math.min(1, parseFloat(el.getAttribute('data-p')||'0')));
            el.style.setProperty('--p', p.toString());
        }});
    }});
</script>
</head>
<body>
    <div class=\"wrap\">
        <div class=\"card\">
            {inner_html}
            <div class=\"actions\">
                <button class=\"btn\" onclick=\"window.parent?.NP_Report?.downloadPDF()\">Download PDF</button>
                <button class=\"btn\" onclick=\"window.parent?.NP_Report?.saveToProfile()\">Save to Profile</button>
            </div>
        </div>
    </div>
</body>
</html>"""

# ---------- Render premium report block ----------
def _render_premium_report(data: Dict[str, Any]) -> str:
    # Extract inputs (both mini-form flat and SPA {answers})
    answers = data.get("answers") or data
    industry = str(answers.get("industry", "General"))
    role     = str(answers.get("role", "Professional"))
    country  = str(answers.get("country", ""))
    persona  = str(answers.get("persona", "neutral"))
    tone     = str(answers.get("tone", "neutral"))

    # arrays
    priorities = answers.get("priorities") or []
    if isinstance(priorities, str):
        priorities = [x.strip() for x in priorities.split(",") if x.strip()]
    impact = answers.get("impact") or []
    if isinstance(impact, str):
        impact = [x.strip() for x in impact.split(",") if x.strip()]

    # numbers
    def to_num(x):
        try: return int(float(x))
        except Exception: return None
    low  = to_num(answers.get("salary_low"))
    high = to_num(answers.get("salary_high"))
    target = to_num(answers.get("salary_target"))

    p25, median, p75, anchor, floor = _derive_range(low, high)

    # Build market range rows (hide values gracefully if missing)
    def row(label, value, denom):
        if value is None or low is None or high is None or high==low:
            pill = f"<div class='pill'>—</div>"
            bar  = "<div class='bar'><div class='fill k' data-p='0'></div></div>"
            end  = "<div class='pill'>—</div>"
        else:
            # position bar by percentage of [low..high]
            p = (value - low) / float(high - low)
            pill = f"<div class='pill'>{label}</div>"
            bar  = f"<div class='bar'><div class='fill k' data-p='{max(0,min(1,p))}'></div></div>"
            end  = f"<div class='pill'>{value:,}</div>"
        return f"<div class='row'>{pill}{bar}{end}</div>"

    market_block = ""
    if (low and high) or any(v is not None for v in (p25, median, p75, anchor, floor)):
        market_block = f"""
        <section class="section">
          <h3>Market Range</h3>
          <div class="list">
            {row('p25', p25, high)}
            {row('median', median, high)}
            {row('p75', p75, high)}
            {row('anchor', anchor, high)}
            {row('floor', floor, high)}
          </div>
        </section>
        """

    # Highlights assembled from priorities/impact/persona
    hl_items = []
    if priorities: hl_items.append(f"Focus on {', '.join(priorities[:3])}")
    if impact:     hl_items.append("Lead with quantified achievements")
    hl_items += ["Anchor high within reason", "Invite alignment on a shared goal"]

    highlights = "".join(f"<li>{h}</li>" for h in hl_items)

    # Summary text (simple rule; OpenAI may smooth it)
    summary_parts = []
    if p75 and target:
        if target >= p75:
            summary_parts.append("Anchor near the 75th percentile with two quantified proof points.")
        else:
            summary_parts.append("Anchor slightly above the median with evidence and flexible terms.")
    elif target:
        summary_parts.append("Anchor with a clear target and emphasize mutual value.")
    else:
        summary_parts.append("Use data-backed framing and tie requests to impact.")
    summary = " ".join(summary_parts) + " Expect a decision within 5 business days."

    # Chips for persona/region
    chips = "".join(f"<span class='chip'>{c}</span>" for c in [persona, country] if c)

    # Debug collapsible (to prove binding to answers)
    rows = "".join(
        f"<tr><td>{k}</td><td>{json.dumps(v, ensure_ascii=False)}</td></tr>"
        for k, v in answers.items()
    )
    debug = f"""
    <details class="section"><summary>Debug Snapshot</summary>
      <div class="card" style="margin-top:8px">
        <table><thead><tr><th>Id</th><th>Value</th></tr></thead><tbody>{rows}</tbody></table>
      </div>
    </details>
    """

    # Final block (two-column)
    inner = f"""
      <h1>Strategic Negotiation Report</h1>
      <div class="meta">{country or '—'} • {datetime.utcnow().strftime('%m/%d/%Y')} • Persona: {persona}</div>

      <div class="grid">
        <div>
          {market_block}
        </div>
        <div>
          <section class="section">
            <h3>Highlights</h3>
            <ul>{highlights}</ul>
            <div class="chips">{chips}</div>
          </section>
        </div>
      </div>

      <section class="section">
        <h3>Summary</h3>
        <p>{summary}</p>
      </section>

      {debug}
    """
    return inner

def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    CORS(app)
    app.config["JSON_AS_ASCII"] = False
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    # ---------- Static ----------
    @app.get("/")
    def index():
        idx = FRONTEND_DIR / "index.html"
        if not idx.exists():
            return _json({"error": f"{idx} not found"}, 404)
        return _nocache(send_from_directory(str(FRONTEND_DIR), "index.html"))

    @app.get("/frontend/<path:filename>")
    def serve_frontend(filename: str):
        file_path = FRONTEND_DIR / filename
        if not file_path.exists():
            return _json({"error": f"frontend file not found: {filename}"}, 404)
        return _nocache(send_from_directory(str(FRONTEND_DIR), filename))

    # Legacy fallbacks
    @app.get("/app.js")
    def app_js_fallback():
        f = FRONTEND_DIR / "app.js"
        if not f.exists():
            return _json({"error": "frontend/app.js not found"}, 404)
        return _nocache(send_from_directory(str(FRONTEND_DIR), "app.js"))

    @app.get("/report_embed.js")
    def report_embed_js_fallback():
        f = FRONTEND_DIR / "report_embed.js"
        if not f.exists():
            return _json({"error": "frontend/report_embed.js not found"}, 404)
        return _nocache(send_from_directory(str(FRONTEND_DIR), "report_embed.js"))

    # ---------- Health ----------
    @app.get("/health")
    def health():
        return _json({"ok": True, "build": BUILD, "ts": datetime.utcnow().isoformat() + "Z"})

    # ---------- Demo data for dashboard / analytics ----------
    @app.get("/metrics")
    def metrics():
        return _json({
            "total": 47,
            "success_rate": 0.78,
            "avg_score": 8.4,
            "competencies": {"communication": .85, "strategy": .72, "analysis": .90, "creativity": .68}
        })

    @app.get("/insights/latest")
    def insights_latest():
        return _json({
            "recent": [
                {"label": "Salary Raise", "score": 9.2},
                {"label": "Real-Estate Deal", "score": 7.8},
                {"label": "Business Agreement", "score": 8.9},
            ],
            "recommendations": [
                {"title": "Sharpen evidence", "desc": "Use quantified results and impact phrasing."},
                {"title": "Strengthen self-advocacy", "desc": "Script a firm opener and practice delivery."},
                {"title": "Refine tone control", "desc": "Adjust assertiveness by counterpart type."},
            ],
        })

    @app.post("/coach")
    def coach():
        msg = (request.get_json(force=True) or {}).get("msg", "").lower()
        if "salary" in msg:
            rep = "Use market data to anchor. What range fits your role and city?"
        elif "deadline" in msg:
            rep = "Deadlines add leverage. Define a timebox and a BATNA."
        else:
            rep = "Share one constraint and one opportunity you have now."
        return _json({"reply": rep})

    # ---------- Questionnaire ----------
    @app.get("/questionnaire/schema")
    def questionnaire_schema():
        path = _find_questionnaire()
        if not path:
            return _json({"error": "questionnaire.json not found in project root/backend/frontend"}, 404)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return _json(data)
        except Exception as e:
            return _json({"error": f"failed reading questionnaire.json: {e}"}, 500)

    @app.post("/questionnaire/report")
    def questionnaire_report():
        """
        Accepts either:
          { "answers": {...} }   <-- from SPA stepper
        or direct flat payload from mini-form (both supported).
        Returns:
          201 { ok, report_id, report_url }
        """
        payload = request.get_json(force=True) or {}
        # keep both shapes working
        answers = payload.get("answers") or payload.get("questionnaire") or payload or {}
        if not isinstance(answers, dict):
            return _json({"ok": False, "reason": "answers must be an object"}, 400)

        # 1) Prefer real engine; else render premium fallback from answers
        if ENGINE:
            try:
                out = ENGINE.run(answers)  # expected {"status":"ok","html":"..."} or {"status":"ok","sections":[...]}
                if out.get("status") != "ok":
                    return _json({"ok": False, "reason": out.get("reason", "engine error")}, 500)
                if out.get("html"):
                    content_html = out["html"]
                elif out.get("sections"):
                    # minimal renderer (sections -> HTML)
                    blocks=[]
                    for sec in out["sections"]:
                        heading = sec.get("heading","Section")
                        pts = sec.get("points",[])
                        blocks.append(f"<section class='section'><h3>{heading}</h3><ul>{''.join(f'<li>{p}</li>' for p in pts)}</ul></section>")
                    content_html = "\n".join(blocks)
                else:
                    content_html = _render_premium_report({"answers": answers})
            except Exception as e:
                return _json({"ok": False, "reason": f"engine failed: {e}"}, 500)
        else:
            content_html = _render_premium_report({"answers": answers})

        # 2) Enhance with OpenAI (optional)
        content_html = enhance_with_openai(content_html)

        # 3) Shell + actions, cache, return id & URL
        full_html = _html_shell(content_html)
        rid = uuid.uuid4().hex[:12]
        REPORTS[rid] = full_html
        (REPORTS_DIR / f"{rid}.html").write_text(full_html, encoding="utf-8")

        return _json({"ok": True, "report_id": rid, "report_url": f"/report/{rid}"}, 201)

    @app.get("/report/<rid>")
    def report_page(rid: str):
        html = REPORTS.get(rid)
        if not html:
            file = REPORTS_DIR / f"{rid}.html"
            if file.exists():
                html = file.read_text(encoding="utf-8")
                REPORTS[rid] = html
        if not html:
            return _json({"error": "report not found"}, 404)
        resp = make_response(html, 200)
        resp.mimetype = "text/html"
        return _nocache(resp)

    # ---------- Save to Profile ----------
    @app.post("/reports/save")
    def save_report():
        payload = request.get_json(force=True) or {}
        rid = payload.get("report_id")
        if not rid:
            return _json({"ok": False, "error": "report_id is required"}, 400)

        src = REPORTS_DIR / f"{rid}.html"
        if not src.exists():
            return _json({"ok": False, "error": "report not found"}, 404)

        dst = SAVED_DIR / f"{rid}.html"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

        meta_path = SAVED_DIR / "index.json"
        index = []
        if meta_path.exists():
            try:
                index = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                index = []
        entry = {
            "report_id": rid,
            "profile_id": payload.get("profile_id"),
            "title": payload.get("title") or "Negotiation Report",
            "tags": payload.get("tags") or [],
            "saved_at": datetime.utcnow().isoformat() + "Z",
        }
        index = [e for e in index if e.get("report_id") != rid] + [entry]
        meta_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

        return _json({"ok": True, "saved_path": f"/backend/saved_reports/{rid}.html"})

    # ---------- PDF Export ----------
    @app.get("/report/<rid>.pdf")
    def report_pdf(rid: str):
        html = REPORTS.get(rid)
        if not html:
            file = (REPORTS_DIR / f"{rid}.html")
            if file.exists():
                html = file.read_text(encoding="utf-8")
        if not html:
            return _json({"ok": False, "error": "report not found"}, 404)

        if not _PDF_AVAILABLE:
            return _json({
                "ok": False,
                "error": "PDF exporter not installed on server",
                "fallback_html": f"/report/{rid}"
            }, 501)

        try:
            pdf_bytes = HTML(string=html, base_url=str(ROOT_DIR)).write_pdf()
            resp = make_response(pdf_bytes, 200)
            resp.mimetype = "application/pdf"
            resp.headers["Content-Disposition"] = f'attachment; filename="negotiation_report_{rid}.pdf"'
            return _nocache(resp)
        except Exception as e:
            return _json({"ok": False, "error": f"PDF generation failed: {e}"}, 500)

    return app
