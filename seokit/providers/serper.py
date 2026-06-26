"""Tier 1 - Serper.dev: live Google SERP position for the surface per seed keyword.

One cheap query per keyword. Needs SERPER_API_KEY.
"""
from __future__ import annotations

from urllib.parse import urlparse

import httpx

from .base import Provider, ProviderResult, Tier

ENDPOINT = "https://google.serper.dev/search"


class SerperProvider(Provider):
    name = "serper"
    tier = Tier.SERP
    requires_env = ["SERPER_API_KEY"]

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        res = ProviderResult(provider=self.name, tier=self.tier)
        key = self.env.get("SERPER_API_KEY")
        if not key:
            res.status = "skipped"
            res.find("low", "serper.no_key", "SERPER_API_KEY not set; skipping.")
            return res

        domain = urlparse(surface.url).netloc.replace("www.", "")
        kws = surface.seed_keywords[:10]
        positions: list[str] = []
        with httpx.Client(timeout=30.0, headers={"X-API-KEY": key, "Content-Type": "application/json"}) as c:
            for kw in kws:
                r = c.post(ENDPOINT, json={"q": kw, "gl": "us", "hl": "en"})
                if r.status_code != 200:
                    positions.append(f"{kw}: HTTP {r.status_code}")
                    continue
                organic = r.json().get("organic", [])
                hit = next((o for o in organic if domain in (o.get("link") or "")), None)
                positions.append(f"{kw}: #{hit['position']}" if hit else f"{kw}: not in top {len(organic)}")

        res.signal("serp_positions", positions)
        if not any("#" in p for p in positions):
            res.find("medium", "serper.unranked",
                     f"{domain} ranks for none of the seed keywords (expected for a new/niche personal site; "
                     "this is the baseline to move).")
        return res
