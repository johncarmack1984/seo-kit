"""Tier 2 - GEO / LLM citation + entity-disambiguation probes.

Asks each keyed answer engine the surface's probe questions, then scores
(a) surfaced - is the entity's handle/work mentioned, (b) conflated - is the
answer about a namesake instead, (c) cited - did a web-grounded engine cite the
surface. Perplexity is the GEO-relevant one (it searches the web + returns
citations); the others reflect parametric/training knowledge.

Per-target config comes from the Surface (set in surfaces.toml): surface_markers,
namesake_markers (optional), geo_probes, cite_domains (optional; defaults to the
surface domain). With no markers/probes the provider skips, so it never runs one
target's probes against another.

Cheap models, max_tokens capped, bounded to the surface's probe set. All httpx.
"""
from __future__ import annotations

from urllib.parse import urlparse

import httpx

from .base import Provider, ProviderResult, Tier


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

        markers = [m.lower() for m in surface.surface_markers]
        probes = surface.geo_probes
        if not markers or not probes:
            res.status = "skipped"
            res.find("low", "geo.no_config",
                     "set surface_markers + geo_probes on the surface (surfaces.toml) to run GEO probes; skipping.")
            return res
        namesakes = [m.lower() for m in surface.namesake_markers]
        cite_domains = [d.lower() for d in (surface.cite_domains or [urlparse(surface.url).netloc.replace("www.", "")])]

        total_surfaced = total_conflated = 0
        for ename, caller in engines.items():
            surfaced = conflated = cited = 0
            details: list[str] = []
            for p in probes:
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
                is_surfaced = any(m in low for m in markers)
                is_conflated = (not is_surfaced) and bool(namesakes) and any(m in low for m in namesakes)
                is_cited = any(any(d in (c or "").lower() for d in cite_domains) for c in citations)
                surfaced += is_surfaced
                conflated += is_conflated
                cited += is_cited
                details.append(f"[{p[:34]}...] {'surfaced' if is_surfaced else ('CONFLATED' if is_conflated else 'absent')}")
            total_surfaced += surfaced
            total_conflated += conflated
            res.signal(ename, f"surfaced {surfaced}/{len(probes)}, conflated {conflated}, cited {cited}",
                       note="; ".join(details))

        if total_conflated:
            res.find("high", "geo.conflation",
                     f"answer engines conflated the surface with a namesake on {total_conflated} probe(s) - the disambiguation gap is real.")
        if total_surfaced == 0:
            res.find("high", "geo.invisible",
                     "no engine surfaced the entity's handle/work on any probe - invisible to answer engines for this niche today.")
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
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.env['GEMINI_API_KEY']}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"], []
