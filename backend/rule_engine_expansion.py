# backend/rule_engine_expansion.py
# Advanced rule engine: parses complex boolean conditions with weights/priority
# Supports: AND, OR, NOT, parentheses; comparators: ==, !=, >=, <=, >, <, contains, in
# Fetches pointers into super_kb.json to assemble recommendations.

from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

Bool = bool
JSON = Dict[str, Any]

_TOK_RE = re.compile(
    r"\s*(?:(AND|OR|NOT)|(\()|(\))|([A-Za-z0-9_\.\-]+)\s*(==|!=|>=|<=|>|<|contains|in)\s*('([^']*)'|\"([^\"]*)\"|\[([^\]]*)\]|[A-Za-z0-9_\.\-]+))",
    re.IGNORECASE
)

def _to_num(x: Any):
    try:
        return float(str(x).replace(",",""))
    except Exception:
        return None

def _split_list_literal(txt: str) -> List[str]:
    items = []
    for part in re.split(r"\s*,\s*", txt.strip()):
        p = part.strip()
        if p.startswith("'") and p.endswith("'"):
            p = p[1:-1]
        if p.startswith('"') and p.endswith('"'):
            p = p[1:-1]
        if p:
            items.append(p)
    return items

class RuleEngineExpansion:
    """
    Evaluate complex conditions against a flat user_data dict.
    - user_data: raw + enriched fields
    - rules_data: KB part having 'ai_triggers' list with condition/fetch/priority/tone_override
    """
    def __init__(self, rules_data: JSON, kb_root: JSON):
        self.rules_data = rules_data or {}
        self.kb_root = kb_root or {}

    # ----- Parser -----
    def _tokenize(self, expr: str) -> List[Tuple[str, ...]]:
        tokens = []
        i = 0
        while i < len(expr):
            m = _TOK_RE.match(expr, i)
            if not m:
                if expr[i].isspace():
                    i += 1
                    continue
                raise ValueError(f"Parse error at: {expr[i:i+20]!r}")
            i = m.end()
            if m.group(1):
                tokens.append(("OP", m.group(1).upper()))
            elif m.group(2):
                tokens.append(("LP", "("))
            elif m.group(3):
                tokens.append(("RP", ")"))
            else:
                lhs = m.group(4)
                op = m.group(5).lower()
                rhs_raw = m.group(6)
                if rhs_raw.startswith("'") or rhs_raw.startswith('"'):
                    rhs = rhs_raw[1:-1]
                elif rhs_raw.startswith("["):
                    rhs = _split_list_literal(rhs_raw[1:-1])
                else:
                    rhs = rhs_raw
                tokens.append(("CMP", lhs, op, rhs))
        return tokens

    def _to_postfix(self, tokens: List[Tuple[str, ...]]) -> List[Tuple[str, ...]]:
        prec = {"NOT": 3, "AND": 2, "OR": 1}
        out: List[Tuple[str, ...]] = []
        stack: List[Tuple[str, ...]] = []
        for t in tokens:
            kind = t[0]
            if kind == "CMP":
                out.append(t)
            elif kind == "OP":
                while stack and stack[-1][0] == "OP" and prec[stack[-1][1]] >= prec[t[1]]:
                    out.append(stack.pop())
                stack.append(t)
            elif kind == "LP":
                stack.append(t)
            elif kind == "RP":
                while stack and stack[-1][0] != "LP":
                    out.append(stack.pop())
                if not stack:
                    raise ValueError("Mismatched parentheses")
                stack.pop()
        while stack:
            if stack[-1][0] in ("LP", "RP"):
                raise ValueError("Mismatched parentheses")
            out.append(stack.pop())
        return out

    # ----- Evaluation -----
    def _value_of(self, key: str, ctx: JSON):
        if key in ctx:
            return ctx[key]
        cur = ctx
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur

    def _cmp(self, lhs_val: Any, op: str, rhs: Any) -> Bool:
        if op == "contains":
            return (str(rhs) in str(lhs_val)) if lhs_val is not None else False
        if op == "in":
            if isinstance(rhs, list):
                return str(lhs_val) in [str(x) for x in rhs]
            return False
        ln = _to_num(lhs_val)
        rn = _to_num(rhs)
        both_num = ln is not None and rn is not None
        if op == "==": return str(lhs_val) == str(rhs) if not both_num else (ln == rn)
        if op == "!=": return str(lhs_val) != str(rhs) if not both_num else (ln != rn)
        if both_num:
            if op == ">=": return ln >= rn
            if op == "<=": return ln <= rn
            if op == ">":  return ln > rn
            if op == "<":  return ln < rn
        return False

    def _eval_postfix(self, pf: List[Tuple[str, ...]], ctx: JSON) -> Bool:
        st: List[Bool] = []
        for t in pf:
            if t[0] == "CMP":
                _, lhs, op, rhs = t
                val = self._value_of(lhs, ctx)
                st.append(self._cmp(val, op, rhs))
            elif t[0] == "OP":
                op = t[1]
                if op == "NOT":
                    a = st.pop() if st else False
                    st.append(not a)
                else:
                    b = st.pop() if st else False
                    a = st.pop() if st else False
                    st.append((a and b) if op == "AND" else (a or b))
        return st[-1] if st else False

    def _match_rule(self, rule: JSON, ctx: JSON) -> Bool:
        expr = (rule.get("condition") or "").strip()
        if not expr:
            return False
        tokens = self._tokenize(expr)
        pf = self._to_postfix(tokens)
        return self._eval_postfix(pf, ctx)

    # ----- Fetch pointers from KB -----
    def _fetch_pointer(self, pointer: str) -> List[Any]:
        if not pointer:
            return []
        parts = pointer.split(".")
        cur: Any = self.kb_root
        if parts[0] == "tactics_by_phase":
            if len(parts) < 3:
                return []
            phase = parts[1]
            tactic_id = parts[2]
            arr = (self.kb_root.get("tactics_by_phase", {}).get(phase) or [])
            for t in arr:
                if t.get("id") == tactic_id:
                    return [t]
            return []
        for p in parts:
            if isinstance(cur, list):
                found = None
                for item in cur:
                    if isinstance(item, dict) and (item.get("id") == p or item.get("name") == p or item.get("title") == p):
                        found = item; break
                cur = found
            elif isinstance(cur, dict):
                if p in cur:
                    cur = cur[p]
                else:
                    val = None
                    for _, v in cur.items():
                        if isinstance(v, list):
                            for item in v:
                                if isinstance(item, dict) and (item.get("id") == p or item.get("name") == p or item.get("title") == p):
                                    val = item; break
                            if val: break
                    cur = val
            else:
                cur = None
            if cur is None:
                return []
        return cur if isinstance(cur, list) else [cur] if cur is not None else []

    def evaluate_all(self, user_ctx: JSON) -> Dict[str, Any]:
        out: Dict[str, Any] = {"matches": [], "recommendations": [], "tone_overrides": []}
        rules = self.kb_root.get("ai_triggers") or []
        for rule in sorted(rules, key=lambda r: int(r.get("priority", 0)), reverse=True):
            try:
                if self._match_rule(rule, user_ctx):
                    fetch_items: List[Any] = []
                    for p in rule.get("fetch", []) or []:
                        fetch_items.extend(self._fetch_pointer(p))
                    if fetch_items:
                        out["matches"].append(rule.get("id"))
                        out["recommendations"].extend(fetch_items)
                    if rule.get("tone_override"):
                        out["tone_overrides"].append(rule["tone_override"])
            except Exception:
                continue
        return out
