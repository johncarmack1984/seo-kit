"""Tier 0 - Bing Webmaster Tools. Needs BING_WEBMASTER_API_KEY + a verified site.

Bing also powers ChatGPT search, so this doubles as an answer-engine signal.
The API is strict about the siteUrl matching a verified property in the same
account; on a mismatch it returns an error, which we surface rather than crash.
"""
from __future__ import annotations

import httpx

from .base import Provider, ProviderResult, Tier

BASE = "https://ssl.bing.com/webmaster/api.svc/json"


class BingProvider(Provider):
    name = "bing"
    tier = Tier.FREE
    requires_env = ["BING_WEBMASTER_API_KEY"]

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        res = ProviderResult(provider=self.name, tier=self.tier)
        key = self.env.get("BING_WEBMASTER_API_KEY")
        if not key:
            res.status = "skipped"
            res.find("low", "bing.no_key", "BING_WEBMASTER_API_KEY not set; skipping Bing data.")
            return res

        with httpx.Client(timeout=30.0) as c:
            r = c.get(f"{BASE}/GetRankAndTrafficStats", params={"apikey": key, "siteUrl": surface.url})
            if r.status_code != 200:
                res.signal("bing", f"HTTP {r.status_code}")
                res.find("low", "bing.error", f"Bing API returned {r.status_code} (is the site verified for this key?).")
                return res
            rows = r.json().get("d", [])
            res.signal("rank_traffic_points", len(rows) if isinstance(rows, list) else "n/a")

            q = c.get(f"{BASE}/GetQueryStats", params={"apikey": key, "siteUrl": surface.url})
            if q.status_code == 200:
                qrows = q.json().get("d", [])
                res.signal("query_rows", len(qrows) if isinstance(qrows, list) else "n/a")
        return res
