from __future__ import annotations
from typing import Dict, Any, List


class SignalAdapter:
    """
    Normalize raw questionnaire answers into a clean 'signals' dict
    that the rules engine can reason about.
    Supports mapping values as:
      - "anchor_target.target_salary"               (string path)
      - {"path": "anchor_target.target_salary"}     (object with path/signal/target/name)
      - ["a.b", "c.d"]                              (duplicate same answer into multiple paths)
    """

    def __init__(self, signal_map: Dict[str, Any]):
        self.signal_map = signal_map or {}

    # ------------- utils -------------
    def _ensure_list(self, v: Any) -> List[Any]:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]

    def _resolve_mapping_paths(self, mapping_value: Any) -> List[str]:
        """
        Turn a mapping value into list of string paths.
        Accepts string, list[str], or dict with 'path'/'signal'/'target'/'name'.
        Silently drops invalid items.
        """
        if isinstance(mapping_value, str):
            return [mapping_value]

        if isinstance(mapping_value, list):
            return [p for p in mapping_value if isinstance(p, str)]

        if isinstance(mapping_value, dict):
            cand = (
                mapping_value.get("path")
                or mapping_value.get("signal")
                or mapping_value.get("target")
                or mapping_value.get("name")
            )
            if isinstance(cand, list):
                return [p for p in cand if isinstance(p, str)]
            if isinstance(cand, str):
                return [cand]

        return []

    # ------------- main -------------
    def to_signals(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        signals: Dict[str, Any] = {}

        # Map answers -> signals (robust to different mapping formats)
        for answer_key, mapping_val in (self.signal_map or {}).items():
            if answer_key not in answers:
                continue
            value = answers.get(answer_key)
            paths = self._resolve_mapping_paths(mapping_val)
            for path in paths:
                try:
                    containers = signals
                    parts = path.split(".")
                    for p in parts[:-1]:
                        if not isinstance(containers.get(p), dict):
                            containers[p] = {}
                        containers = containers[p]
                    containers[parts[-1]] = value
                except Exception:
                    # Defensive: never break the whole build on a single bad mapping
                    signals.setdefault("_warnings", []).append(
                        f"Invalid map for {answer_key} -> {mapping_val}"
                    )

        # Soft defaults so rendering never explodes
        persona_types = answers.get("persona_types") or answers.get("persona") or []
        if isinstance(persona_types, str):
            persona_types = [persona_types]
        signals.setdefault("persona", {})["types"] = persona_types

        emotions = answers.get("emotions") or []
        if isinstance(emotions, str):
            emotions = [emotions]
        signals["emotions"] = emotions

        # Normalize counterpart style
        cp = signals.setdefault("counterpart_style", {})
        cp.setdefault("communication", answers.get("counterpart_style") or answers.get("counterpart_personality"))
        cp.setdefault("decision_making", answers.get("counterpart_decision_style"))

        # Deadline normalization
        dp = signals.setdefault("deadline_pressure", {})
        if dp.get("urgency_level") is None and answers.get("urgency_level"):
            dp["urgency_level"] = answers["urgency_level"]
        if dp.get("time_to_decision") is None and answers.get("deadline_days") is not None:
            dp["time_to_decision"] = answers["deadline_days"]

        # Culture
        cc = signals.setdefault("cultural_context", {})
        if answers.get("culture_region"):
            cc["region"] = answers["culture_region"]
        if answers.get("culture_context"):
            cc["communication_style"] = answers["culture_context"]

        # BATNA, conflict, deal type
        if "batna_strength" not in signals and answers.get("batna_strength"):
            signals["batna_strength"] = answers["batna_strength"]
        if answers.get("conflict_style"):
            signals["conflict_style"] = answers["conflict_style"]
        if answers.get("deal_type") is not None:
            signals["deal_type"] = answers["deal_type"]

        # Anchor (salary/pricing)
        at = signals.setdefault("anchor_target", {})
        for k in ("target_salary", "min_acceptable", "dream_number"):
            if answers.get(k) is not None and at.get(k) is None:
                at[k] = answers[k]

        return signals
