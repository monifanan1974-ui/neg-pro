# backend/market_enricher.py
# Real-time-ish enrichment via pluggable sources.
# Offline-friendly: falls back to local-data.json medians if external fetchers are disabled.

from typing import Optional, Dict, Any, Tuple, List

class MarketEnricher:
    def __init__(self, local_market: Dict[str, Any], sources_enabled: bool = False):
        """
        local_market: dict from local-data.json like:
          { "comp_benchmarks": { "roles": { "Senior Editor|UK": {"p25":"£72k","median":"£78k","p75":"£84k"} } } }
        sources_enabled: if you wire real fetchers, flip to True.
        """
        self.local = local_market or {}
        self.sources_enabled = sources_enabled

    def _from_local(self, role: str, country: str) -> Optional[Dict[str, str]]:
        roles = (self.local.get("comp_benchmarks", {}) or {}).get("roles", {})
        key = f"{role}|{country}"
        return roles.get(key)

    def _normalize_currency(self, v: Optional[str]) -> Optional[str]:
        if not v: return None
        s = str(v).strip().replace(" ", "")
        return s

    def infer_range(self, role: str, country: str) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """
        Returns (low, high, meta) where low/high are strings like "£74k", meta has quality + references.
        """
        # 1) Local fallback
        loc = self._from_local(role, country)
        if loc:
            meta = {
                "source": "local-data.json",
                "quality": 0.75,
                "refs": ["local:comp_benchmarks.roles"]
            }
            p25 = self._normalize_currency(loc.get("p25"))
            p75 = self._normalize_currency(loc.get("p75"))
            return p25, p75, meta

        # 2) External (optional; stubs). Keep deterministic offline.
        if self.sources_enabled:
            # TODO: implement Glassdoor/Levels/BLS adapters
            pass

        # No data
        return None, None, {"source": "none", "quality": 0.0, "refs": []}

