"""Tier 0 - Google Trends (relative interest for seed keywords). No key.

Needs the 'trends' extra (pytrends). pytrends is unofficial and rate-limited;
a 429 surfaces as an error result rather than crashing the audit.
"""
from __future__ import annotations

from .base import Provider, ProviderResult, Tier


class TrendsProvider(Provider):
    name = "trends"
    tier = Tier.FREE

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        res = ProviderResult(provider=self.name, tier=self.tier)
        kws = surface.seed_keywords[:5]
        if not kws:
            res.status = "skipped"
            res.find("low", "trends.no_seeds", "surface has no seed_keywords.")
            return res
        try:
            from pytrends.request import TrendReq
        except ImportError:
            res.status = "skipped"
            res.find("low", "trends.no_dep", "install the 'trends' extra (pytrends) to pull Google Trends.")
            return res

        py = TrendReq(hl="en-US", tz=360)
        py.build_payload(kws, timeframe="today 12-m")
        iot = py.interest_over_time()
        if iot is not None and not iot.empty:
            means = {k: round(float(iot[k].mean()), 1) for k in kws if k in iot.columns}
            ranked = sorted(means.items(), key=lambda kv: -kv[1])
            res.signal("avg_interest_12m", [f"{k}: {v}" for k, v in ranked], note="0-100 relative")
        else:
            res.find("low", "trends.empty", "Trends returned no data for the seed set (try broader terms).")
        return res
