"""Tier 1 - DataForSEO: real Google Ads monthly search volume for seed keywords.

One batched live call (cheap). Needs DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD.
"""
from __future__ import annotations

import httpx

from .base import Provider, ProviderResult, Tier

ENDPOINT = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"
US_LOCATION = 2840


class DataForSeoProvider(Provider):
    name = "dataforseo"
    tier = Tier.SERP
    requires_env = ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"]

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        res = ProviderResult(provider=self.name, tier=self.tier)
        login, password = self.env.get("DATAFORSEO_LOGIN"), self.env.get("DATAFORSEO_PASSWORD")
        if not (login and password):
            res.status = "skipped"
            res.find("low", "dataforseo.no_key", "DATAFORSEO_LOGIN/PASSWORD not set; skipping.")
            return res
        kws = surface.seed_keywords[:20]
        if not kws:
            res.status = "skipped"
            return res

        body = [{"keywords": kws, "location_code": US_LOCATION, "language_code": "en"}]
        with httpx.Client(timeout=90.0) as c:
            r = c.post(ENDPOINT, auth=(login, password), json=body)
            r.raise_for_status()
            data = r.json()

        tasks = data.get("tasks") or []
        rows = (tasks[0].get("result") or []) if tasks else []
        ranked = sorted(
            ((x.get("keyword"), x.get("search_volume") or 0, x.get("competition"), x.get("cpc")) for x in rows),
            key=lambda t: -(t[1] or 0),
        )
        res.signal("keyword_volumes", [f"{k}: {v}/mo (comp={c}, cpc={p})" for k, v, c, p in ranked])
        if data.get("cost"):
            res.signal("api_cost_usd", data["cost"])
        zero = [k for k, v, *_ in ranked if not v]
        if zero:
            res.find("low", "dataforseo.zero_volume", f"{len(zero)} seed terms show ~0 volume: {', '.join(zero)}")
        return res
