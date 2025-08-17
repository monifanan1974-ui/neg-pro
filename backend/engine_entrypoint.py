from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .signal_adapter import SignalAdapter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

RULES_PATHS = [
    DATA / "rules-engine.json",
    ROOT / "rules-engine.json",
]
MAP_PATHS = [
    DATA / "rules_signal_map.json",
    ROOT / "rules_signal_map.json",
]

def _read_json_first(paths: List[Path]) -> Tuple[Dict[str, Any], str]:
    for p in paths:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f), str(p)
    return {}, "<missing>"

def _norm_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v) for v in x]
    return [str(x)]

class QuestionnaireEngine:
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.rules, self.rules_path = _read_json_first(RULES_PATHS)
        self.signal_map, self.map_path = _read_json_first(MAP_PATHS)
        self.adapter = SignalAdapter(self.signal_map)

        if not isinstance(self.rules.get("rules"), list):
            self.rules["rules"] = []

    # ---------- Matching ----------
    def _match_condition(self, value: Any, cond: Dict[str, Any]) -> float:
        """
        Return a match factor in [0,1] for a single condition.
        Supports: equals / in / range / defined
        """
        if cond.get("status") == "defined":
            return 1.0 if value not in (None, "", []) else 0.0

        if "equals" in cond:
            return 1.0 if str(value) == str(cond["equals"]) else 0.0

        if "in" in cond:
            return 1.0 if str(value) in {str(v) for v in cond["in"]} else 0.0

        if "range" in cond and isinstance(value, (int, float)):
            lo, hi = cond["range"]
            return 1.0 if (lo <= float(value) <= hi) else 0.0

        if "min_items" in cond and isinstance(value, list):
            return 1.0 if len(value) >= int(cond["min_items"]) else 0.0

        return 0.0

    def _score_rule(self, signals: Dict[str, Any], rule: Dict[str, Any]) -> float:
        conds = rule.get("conditions", {})
        if not conds:
            return 0.0

        total_w = 0.0
        acc = 0.0
        for sig_path, cfg in conds.items():
            # resolve nested signal path, e.g. "counterpart_style.decision_making"
            parts = sig_path.split(".")
            cur = signals
            for p in parts:
                cur = (cur or {}).get(p) if isinstance(cur, dict) else None
            weight = float(cfg.get("weight", 1.0))
            m = self._match_condition(cur, cfg)
            acc += m * weight
            total_w += weight

        return acc / total_w if total_w > 0 else 0.0

    def _activate_rules(self, signals: Dict[str, Any]) -> List[Dict[str, Any]]:
        active: List[Dict[str, Any]] = []
        for rule in self.rules.get("rules", []):
            score = self._score_rule(signals, rule)
            threshold = float(rule.get("activation_threshold", 0.6))
            if score >= threshold:
                active.append({
                    "id": rule.get("rule_id"),
                    "title": rule.get("title", rule.get("rule_id", "rule")),
                    "family": rule.get("family", "general"),
                    "score": round(score, 3),
                    "tactics": rule.get("output_tactics", []),
                    "reasoning": rule.get("reasoning", ""),
                })
        active.sort(key=lambda r: r["score"], reverse=True)
        return active

    # ---------- Rendering ----------
    def _pill(self, text: str) -> str:
        return f'<span class="pill">{text}</span>'

    def _baseline_pack(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        # Always-present, decent content even with zero matches.
        persona = ", ".join(_norm_list((signals.get("persona") or {}).get("types"))) or "-"
        emotions = ", ".join(_norm_list(signals.get("emotions"))) or "-"
        region = (signals.get("cultural_context") or {}).get("region", "—")
        conflict = signals.get("conflict_style", "-")

        openers = [
            "Start with a concise value statement tied to market context.",
            "Offer a data-backed anchor and pause for their view.",
            "Invite alignment on the shared goal before diving into numbers."
        ]
        counters = [
            "If they say 'budget is tight' → propose a performance-based structure.",
            "If they lowball → bridge with ROI and credible proof.",
            "If they challenge market data → align on sources, then re-anchor."
        ]
        micro = [
            "Use a 3–5 second strategic pause after your anchor.",
            "Label emotions you notice to reduce friction.",
            "Ask one high-leverage question per objection."
        ]
        play = [
            "Opening → Lowball → Bridge with proof → Agree on middle ground.",
            "Opening → Budget constraint → Performance triggers → Review timeline.",
            "Opening → Data challenge → Source alignment → Re-state anchor."
        ]

        return {
            "snapshot": {
                "region": region, "persona": persona, "emotions": emotions, "conflict": conflict
            },
            "highlights": [
                "Use data-backed framing and tie requests to impact.",
                "Keep tone professional; aim for collaborative language.",
                "Make timing explicit; suggest a decision window of ~5 business days."
            ],
            "openers": openers,
            "counters": counters,
            "micro": micro,
            "play": play
        }

    def _render_html(self, answers: Dict[str, Any], signals: Dict[str, Any], matches: List[Dict[str, Any]]) -> str:
        # Snapshot
        persona = ", ".join(_norm_list((signals.get("persona") or {}).get("types"))) or "-"
        emotions = ", ".join(_norm_list(signals.get("emotions"))) or "-"
        region = (signals.get("cultural_context") or {}).get("region", "—")
        conflict = signals.get("conflict_style", "-")

        base = self._baseline_pack(signals)
        hl = base["highlights"]
        if matches:
            # Enrich highlights from matched rules
            for m in matches[:5]:
                if m["tactics"]:
                    hl.append(f"{m['title']}: " + ", ".join(m["tactics"][:3]))
                elif m["reasoning"]:
                    hl.append(m["title"] + " — " + m["reasoning"])

        pills = " ".join([
            self._pill(f"Persona: {persona or '-'}"),
            self._pill(f"Emotions: {emotions or '-'}"),
            self._pill(f"Region: {region}"),
        ])

        match_rows = "".join(
            f"<li><b>{m['title']}</b> &middot; score {m['score']}<br>"
            f"<span class='muted'>{m.get('reasoning','')}</span>"
            f"{('<br><span class=\"muted\">' + ', '.join(m['tactics']) + '</span>') if m['tactics'] else ''}"
            f"</li>"
            for m in matches
        ) or "<li class='muted'>No specific rules matched; using a robust default plan.</li>"

        html = f"""
<div class="np-report">
  <h2>Negotiation Strategy Report</h2>
  <div class="meta">{pills}</div>

  <section>
    <h3>Snapshot</h3>
    <div class="card">
      <div>Region: <b>{base['snapshot']['region']}</b> &nbsp;·&nbsp;
           Type: <b>custom</b> &nbsp;·&nbsp;
           Conflict style: <b>{base['snapshot']['conflict']}</b></div>
    </div>
  </section>

  <section>
    <h3>Highlights</h3>
    <ul>
      {''.join(f'<li>{h}</li>' for h in hl)}
    </ul>
  </section>

  <section>
    <h3>Opening Options (ready to say)</h3>
    <ul>
      {''.join(f'<li>{t}</li>' for t in base['openers'])}
    </ul>
  </section>

  <section>
    <h3>Counters You’ll Need</h3>
    <ul>
      {''.join(f'<li>{t}</li>' for t in base['counters'])}
    </ul>
  </section>

  <section>
    <h3>Micro-tactics</h3>
    <ul>
      {''.join(f'<li>{t}</li>' for t in base['micro'])}
    </ul>
  </section>

  <section>
    <h3>Play-ahead (what likely happens next)</h3>
    <ul>
      {''.join(f'<li>{t}</li>' for t in base['play'])}
    </ul>
  </section>

  <details class="debug">
    <summary>Debug Snapshot</summary>
    <div><b>Matches:</b> {len(matches)}</div>
    <ol>{match_rows}</ol>
    <div class="muted">Rules: {self.rules_path} · Map: {self.map_path}</div>
  </details>
</div>

<style>
.np-report {{ color: #dbe8ff; }}
.np-report h2 {{ margin: 0.25rem 0 0.75rem; }}
.np-report .meta {{ margin: 0 0 1rem; }}
.np-report section {{ margin: 1rem 0 1.25rem; }}
.np-report .card {{
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px; padding: 0.75rem 1rem;
  box-shadow: 0 8px 20px rgba(0,0,0,0.3);
}}
.np-report ul {{ margin: 0.25rem 0 0 1.25rem; }}
.np-report .pill {{
  display: inline-block; padding: .25rem .6rem; margin-right: .4rem;
  border-radius: 999px; background: linear-gradient(90deg,#0ea5ea,#2563eb);
  color: #fff; font-size: .8rem;
}}
.np-report .muted {{ color: #9fb2cc; font-size: .9rem; }}
.np-report details.debug {{ margin-top: .75rem; }}
</style>
"""
        return html

    # ---------- Public API ----------
    def run(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        try:
            signals = self.adapter.to_signals(answers or {})
            matches = self._activate_rules(signals)
            html = self._render_html(answers, signals, matches)
            return {
                "status": "ok",
                "matches": matches,
                "signals": signals if self.debug else {},
                "html": html
            }
        except Exception as ex:
            return {"status": "error", "reason": str(ex)}
