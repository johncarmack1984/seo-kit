"""Tier 2 - GEO / LLM citation + entity-disambiguation probes.

Asks each keyed answer engine about the surface's niche + entity, then scores
(a) surfaced - is the handle/work mentioned, (b) conflated - is the answer about
a namesake instead (a site whose owner shares a famous namesake's name), (c) cited - did a web-grounded engine cite the surface. Perplexity is
the GEO-relevant one (it searches the web + returns citations); the others
reflect parametric/training knowledge.

Cheap models, max_tokens capped, bounded to a small probe set. All plain httpx.
TODO: move markers + probes into surfaces.toml so this generalizes past the hardcoded POC surface.
"""
from __future__ import annotations

import httpx

from .base import Provider, ProviderResult, Tier

SURFACE_MARKERS = ["example-handle", "example.com"]
NAMESAKE_MARKERS = ["the famous namesake", "namesake flagship product"]

PROBES = [
    "Who is example-handle on GitHub, and what do they build?",
    "There is an engineer who runs example.com (not the famous namesake). What can you tell me about them?",
    "Name people known for this niche who also publish open source.",
]


class GeoProbeProvider(Provider):
    name = "geo_probe"
    tier = Tier.GEO

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        res = ProviderResult(provider=self.name, tier=self.tier)
        engines = self._engines()
        if not engines:
            res.status = "skipped"
            res.find("low", "geo.no_key", "no GEO engine key (PERPLEXITY/OPENAI/ANTHROPIC/GEMINI); skipping.")
            return res

        total_surfaced = total_conflated = 0
        for ename, caller in engines.items():
            surfaced = conflated = cited = 0
            details: list[str] = []
            for p in PROBES:
                try:
                    answer, citations = caller(p)
                except httpx.HTTPStatusError as e:
                    code = e.response.status_code
                    tag = {429: "rate-limited", 503: "overloaded"}.get(code, f"HTTP {code}")
                    details.append(f"[{p[:30]}...] {tag}")
                    continue
                except Exception as e:  # noqa: BLE001 - one engine/prompt failing must not sink the rest
                    details.append(f"[{p[:30]}...] error: {type(e).__name__}")
                    continue
                low = (answer or "").lower()
                is_surfaced = any(m in low for m in SURFACE_MARKERS)
                is_conflated = (not is_surfaced) and any(m in low for m in NAMESAKE_MARKERS)
                is_cited = any(any(m in (c or "").lower() for m in SURFACE_MARKERS) for c in citations)
                surfaced += is_surfaced
                conflated += is_conflated
                cited += is_cited
                details.append(f"[{p[:34]}...] {'surfaced' if is_surfaced else ('CONFLATED' if is_conflated else 'absent')}")
            total_surfaced += surfaced
            total_conflated += conflated
            res.signal(ename, f"surfaced {surfaced}/{len(PROBES)}, conflated {conflated}, cited {cited}",
                       note="; ".join(details))

        if total_conflated:
            res.find("high", "geo.conflation",
                     f"LLMs conflated you with the famous John Carmack on {total_conflated} probe(s) - the disambiguation gap is real.")
        if total_surfaced == 0:
            res.find("high", "geo.invisible",
                     "No engine surfaced your handle/work on any probe - you are invisible to answer engines for your niche today.")
        return res

    def _engines(self) -> dict:
        e = {}
        if self.env.get("PERPLEXITY_API_KEY"):
            e["perplexity"] = self._perplexity
        if self.env.get("OPENAI_API_KEY"):
            e["openai"] = self._openai
        if self.env.get("ANTHROPIC_API_KEY"):
            e["anthropic"] = self._anthropic
        if self.env.get("GEMINI_API_KEY"):
            e["gemini"] = self._gemini
        return e

    def _perplexity(self, prompt: str):
        r = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {self.env['PERPLEXITY_API_KEY']}"},
            json={"model": "sonar", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
            timeout=60.0,
        )
        r.raise_for_status()
        j = r.json()
        answer = j["choices"][0]["message"]["content"]
        raw = j.get("citations") or j.get("search_results") or []
        cits = [c if isinstance(c, str) else c.get("url", "") for c in raw]
        return answer, cits

    def _openai(self, prompt: str):
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.env['OPENAI_API_KEY']}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"], []

    def _anthropic(self, prompt: str):
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.env["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 500, "messages": [{"role": "user", "content": prompt}]},
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"], []

    def _gemini(self, prompt: str):
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={self.env['GEMINI_API_KEY']}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"], []
