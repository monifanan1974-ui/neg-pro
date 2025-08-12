# backend/anchor_utils.py
# Numeric anchor builder + text generator tuned by persona/risk.

from typing import Optional, Tuple

def _parse_amount(s: Optional[str]) -> Optional[float]:
    if not s: return None
    t = s.replace("£","").replace("€","").replace("$","").replace(",","").lower()
    t = t.replace("k","000")
    try:
        return float(t)
    except Exception:
        return None

def _fmt_currency(raw: Optional[float], symbol: str = "€") -> str:
    if raw is None: return "a market-aligned range"
    v = int(round(raw, -2))  # round to nearest hundred
    # pretty: 78000 -> €78k
    if v % 1000 == 0:
        return f"{symbol}{int(v/1000)}k"
    return f"{symbol}{v:,}"

def compute_anchor(range_low: Optional[str], range_high: Optional[str], target: Optional[str],
                   persona: str = "", risk_tolerance: int = 3, symbol: str = "€") -> Tuple[str, Optional[str]]:
    """
    Returns (anchor_text, anchor_value_str)
    Strategy:
      - If target provided → use it, else mid of (low,high).
      - Persona tuning:
          Dominator: +3–5% premium (assertive).
          Analyst: mid or +1% if proofs exist.
          Friend/Fox: +2%.
      - Risk tolerance (1..5): scales premium ±2%.
    """
    lo = _parse_amount(range_low)
    hi = _parse_amount(range_high)
    tgt = _parse_amount(target)

    base = tgt
    if base is None and lo and hi:
        base = (lo + hi) / 2.0
    if base is None and (lo or hi):
        base = (lo or hi)

    if base is None:
        return "I’m targeting within that range.", None

    persona_l = (persona or "").lower()
    premium = 0.0
    if "dominator" in persona_l: premium = 0.04
    elif "analyst" in persona_l: premium = 0.01
    elif "friend" in persona_l or "fox" in persona_l: premium = 0.02

    # risk adjust (1..5): map to [-0.02 .. +0.02]
    premium += (max(1, min(5, risk_tolerance)) - 3) * 0.01

    anchor_val = base * (1.0 + premium)
    anchor_str = _fmt_currency(anchor_val, symbol=symbol)
    return f"I’m targeting {anchor_str} within that.", anchor_str

