"""Tier 0 - PageSpeed Insights (Core Web Vitals). Needs PAGESPEED_API_KEY."""
from __future__ import annotations

import httpx

from .base import Provider, ProviderResult, Tier

PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


class PsiProvider(Provider):
    name = "psi"
    tier = Tier.FREE
    requires_env = ["PAGESPEED_API_KEY"]

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        res = ProviderResult(provider=self.name, tier=self.tier)
        key = self.env.get("PAGESPEED_API_KEY")
        if not key:
            res.status = "skipped"
            res.find("medium", "psi.no_key", "PAGESPEED_API_KEY not set; skipping Core Web Vitals.")
            return res

        params = [("url", surface.url), ("key", key), ("strategy", "mobile"), ("category", "PERFORMANCE")]
        with httpx.Client(timeout=90.0) as c:
            r = c.get(PSI, params=params)
            r.raise_for_status()
            data = r.json()

        lh = data.get("lighthouseResult", {})
        audits = lh.get("audits", {})
        score = (lh.get("categories", {}).get("performance", {}) or {}).get("score")
        res.signal("performance_score", round(score * 100) if score is not None else None)
        for metric_id, label in [
            ("largest-contentful-paint", "LCP"),
            ("cumulative-layout-shift", "CLS"),
            ("total-blocking-time", "TBT"),
            ("speed-index", "SpeedIndex"),
        ]:
            res.signal(label, audits.get(metric_id, {}).get("displayValue"))

        # Real-user field data, including INP (the 2024 CWV that replaced FID).
        field = data.get("loadingExperience", {}).get("metrics", {})
        inp = field.get("INTERACTION_TO_NEXT_PAINT", {})
        if inp:
            res.signal("INP_field_ms", inp.get("percentile"), note="real-user p75")

        if score is not None and score < 0.9:
            res.find("medium", "psi.performance", f"Mobile performance score {round(score * 100)} (<90).")
        return res
