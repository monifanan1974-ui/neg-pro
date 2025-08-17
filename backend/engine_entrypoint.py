from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .signal_adapter import SignalAdapter


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RULES_PATH = DATA_DIR / "rules-engine.json"
MAP_PATH = DATA_DIR / "rules_signal_map.json"


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, (tuple, set)):
        return list(x)
    return [x]


def _csv(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, (list, tuple, set)):
        return ", ".join(str(v) for v in x)
    return str(x)


def _list_intersects(a: Any, b: Any) -> bool:
    la = {str(v).strip().lower() for v in _as_list(a)}
    lb = {str(v).strip().lower() for v in _as_list(b)}
    return not la.isdisjoint(lb)


class QuestionnaireEngine:
    """
    Loads the signal map + rules, builds a normalized context from answers,
    matches rules, and renders a compact HTML report.
    """

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.signal_map = self._load_json(MAP_PATH, default={})
        rules_blob = self._load_json(RULES_PATH, default={"rules": []})
        self.rules: List[Dict[str, Any]] = rules_blob.get("rules", [])
        self.adapter = SignalAdapter(self.signal_map)

    # ---------- IO ----------
    def _load_json(self, path: Path, default: Any) -> Any:
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            if self.debug:
                print(f"[engine] JSON file not found: {path}")
            return default
        except Exception as e:
            if self.debug:
                print(f"[engine] Failed to load {path}: {e}")
            return default

    # ---------- matching ----------
    def _match_rule(self, rule: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Very simple matcher:
          - persona_any: list of persona types (any match)
          - emotions_any: list of emotions (any match)
          - tags_any: list of tags (any match)

        A rule passes if all declared clauses pass (AND across clauses).
        """
        cond = rule.get("conditions", {}) or {}

        persona_types = (ctx.get("persona", {}) or {}).get("types", [])
        emotions = ctx.get("emotions", []) or []
        tags = ctx.get("tags", []) or []

        checks = []
        why: Dict[str, Any] = {}

        if "persona_any" in cond:
            ok = _list_intersects(persona_types, cond["persona_any"])
            checks.append(ok)
            why["persona_any"] = {"have": persona_types, "want": cond["persona_any"], "ok": ok}

        if "emotions_any" in cond:
            ok = _list_intersects(emotions, cond["emotions_any"])
            checks.append(ok)
            why["emotions_any"] = {"have": emotions, "want": cond["emotions_any"], "ok": ok}

        if "tags_any" in cond:
            ok = _list_intersects(tags, cond["tags_any"])
            checks.append(ok)
            why["tags_any"] = {"have": tags, "want": cond["tags_any"], "ok": ok}

        # If no conditions are declared, consider it non-matching (avoid catch-all).
        if not cond:
            return False, {"reason": "no_conditions"}

        matched = all(checks) if checks else False
        return matched, why

    # ---------- render ----------
    def _render_html(self, answers: Dict[str, Any], ctx: Dict[str, Any], hits: List[Dict[str, Any]]) -> str:
        persona_types = (ctx.get("persona", {}) or {}).get("types", [])
        emotions = ctx.get("emotions", []) or []
        tags = ctx.get("tags", []) or []

        # Build recommendation cards
        cards: List[str] = []
        for r in hits:
            recs = _as_list(r.get("recommendations"))
            title = r.get("title") or r.get("id") or "Recommendation"
            body = ""
            if recs:
                body = "".join(f"<li>{str(item)}</li>" for item in recs)
                body = f"<ul class='rec-list'>{body}</ul>"
            cards.append(
                f"""
                <div class="card">
                  <div class="card-title">{title}</div>
                  <div class="card-body">{body}</div>
                  <div class="card-meta">Rule: {r.get('id','-')} • Tags: {_csv(r.get('tags'))}</div>
                </div>
                """
            )

        cards_html = "\n".join(cards) if cards else "<div class='muted'>No specific recommendations matched the current context.</div>"

        # Minimal, business-lean styling (MVP-93 palette compatible)
        html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Negotiation Strategy Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --bg: #0b1220;
  --panel: #121a2a;
  --border: #1e2a43;
  --text: #e6f0ff;
  --muted: #9fb3d9;
  --accent: #5aa9ff;
  --accent-2: #7c5cff;
  --glow: 0 10px 30px rgba(90,169,255,0.25);
}}
body {{
  margin:0; padding:32px 24px; background: radial-gradient(1200px 600px at 70% -10%, #152036 0%, #0b1220 60%) fixed, var(--bg);
  color: var(--text); font: 16px/1.6 Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}}
.container {{ max-width: 1024px; margin: 0 auto; }}
.h1 {{ font-size: 34px; font-weight: 800; letter-spacing: .2px; margin: 8px 0 4px; }}
.sub {{ color: var(--muted); margin-bottom: 24px; }}
.header {{
  display:flex; align-items:center; justify-content:space-between; gap: 16px; margin-bottom: 20px;
}}
.badges {{ display:flex; gap: 8px; flex-wrap: wrap; }}
.badge {{
  background: linear-gradient(180deg, #12203a, #10192b);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 10px; border-radius: 10px; font-size: 12px; opacity:.95;
}}
.grid {{ display:grid; grid-template-columns: 1fr; gap: 16px; }}
@media(min-width: 800px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
.card {{
  background: linear-gradient(180deg, #0f1728, #0e1524);
  border: 1px solid var(--border); border-radius: 14px; padding: 18px 16px; box-shadow: var(--glow);
}}
.card-title {{ font-weight: 700; margin-bottom: 6px; color: #eaf2ff; }}
.card-meta {{ color: var(--muted); font-size: 12px; margin-top: 8px; }}
.rec-list {{ padding-left: 18px; margin: 6px 0 0; }}
.kv {{ display:flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
.kv .k {{ color: var(--muted); }}
.muted {{ color: var(--muted); }}
.hr {{ height: 1px; background: linear-gradient(90deg, transparent, #1c2741 20%, #1c2741 80%, transparent); margin: 18px 0; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <div class="h1">Negotiation Strategy Report</div>
        <div class="sub">A tailored brief derived from your questionnaire.</div>
        <div class="badges">
          <span class="badge">Persona: {_csv(persona_types) or "-"}</span>
          <span class="badge">Emotions: {_csv(emotions) or "-"}</span>
          <span class="badge">Tags: {_csv(tags) or "-"}</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Snapshot</div>
      <div class="kv">
        <span class="k">Region:</span><span>{answers.get("culture_region", "-")}</span>
        <span class="k">Type:</span><span>{answers.get("negotiation_type", "-")}</span>
        <span class="k">Conflict style:</span><span>{answers.get("conflict_style", "-")}</span>
      </div>
    </div>

    <div class="hr"></div>

    <div class="grid">
      {cards_html}
    </div>

    <div class="hr"></div>
    <div class="muted">Build: engine v1 • Matches: {len(hits)}</div>
  </div>
</body>
</html>"""
        return html

    # ---------- public API ----------
    def run(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry: answers -> context -> rule matches -> HTML
        Returns: {"status":"ok","html":..., "matched": [...], "context": {...}}
        """
        try:
            ctx = self.adapter.build_context(answers or {})

            matches: List[Dict[str, Any]] = []
            for r in self.rules:
                ok, why = self._match_rule(r, ctx)
                if ok:
                    r_copy = dict(r)
                    if self.debug:
                        r_copy["_why"] = why
                    matches.append(r_copy)

            html = self._render_html(answers, ctx, matches)
            return {
                "status": "ok",
                "html": html,
                "matched": [m.get("id") for m in matches],
                "context": ctx,
            }
        except Exception as e:
            if self.debug:
                raise
            return {"status": "error", "reason": str(e)}
