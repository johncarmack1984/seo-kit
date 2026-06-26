"""Tier 0 - on-page + render-gap crawler (keyless).

Fetches the raw server HTML (what non-JS crawlers and most LLM bots see) and,
if Playwright is installed, the rendered DOM. The gap between them is the single
most important signal for an SPA: content that only exists after JS is largely
invisible to LLM answer engines and weaker for classic SEO.

Also pulls robots.txt + sitemap.xml and checks head-tag hygiene.
"""
from __future__ import annotations

import json
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .base import Provider, ProviderResult, Tier

UA = "Mozilla/5.0 (compatible; seo-kit/0.1; +https://github.com/johncarmack1984/seo-kit)"


def _text_words(soup: BeautifulSoup) -> int:
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.extract()
    return len(soup.get_text(" ", strip=True).split())


def _jsonld_types(soup: BeautifulSoup) -> list[str]:
    types: list[str] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for node in data.get("@graph", [data]) if isinstance(data, dict) else data:
            if isinstance(node, dict) and node.get("@type"):
                t = node["@type"]
                types.extend(t if isinstance(t, list) else [t])
    return types


def _meta(soup: BeautifulSoup, **attrs) -> str | None:
    tag = soup.find("meta", attrs=attrs)
    return tag.get("content") if tag else None


class CrawlProvider(Provider):
    name = "crawl"
    tier = Tier.FREE

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        res = ProviderResult(provider=self.name, tier=self.tier)
        url = surface.url

        with httpx.Client(follow_redirects=True, timeout=20.0, headers={"User-Agent": UA}) as client:
            r = client.get(url)
            raw_html = r.text
            res.signal("final_url", str(r.url))
            res.signal("status", r.status_code)
            soup = BeautifulSoup(raw_html, "html.parser")

            # --- head-tag hygiene ---
            title = (soup.title.string or "").strip() if soup.title else ""
            res.signal("title", title)
            res.signal("title_len", len(title))
            if not title:
                res.find("high", "title.missing", "No <title> in server HTML.")
            elif not (15 <= len(title) <= 65):
                res.find("low", "title.length", f"Title is {len(title)} chars (aim 15-65).")

            desc = _meta(soup, attrs={"name": "description"}) or _meta(soup, name="description")
            res.signal("meta_description", desc or "")
            if not desc:
                res.find("medium", "description.missing", "No meta description.")

            canonical = soup.find("link", rel="canonical")
            res.signal("canonical", canonical.get("href") if canonical else None)
            if not canonical:
                res.find("low", "canonical.missing", "No rel=canonical link.")

            res.signal("html_lang", soup.html.get("lang") if soup.html else None)
            res.signal("og_tags", len(soup.find_all("meta", property=lambda v: v and v.startswith("og:"))))
            res.signal("twitter_tags", len(soup.find_all("meta", attrs={"name": lambda v: v and v.startswith("twitter:")})))
            res.signal("h1_raw", [h.get_text(strip=True) for h in soup.find_all("h1")])

            # --- the SPA / render gap (keyless headline signal) ---
            raw_words = _text_words(BeautifulSoup(raw_html, "html.parser"))
            raw_jsonld = _jsonld_types(BeautifulSoup(raw_html, "html.parser"))
            res.signal("raw_html_words", raw_words)
            res.signal("jsonld_types_raw", raw_jsonld)
            if not raw_jsonld:
                res.find("high", "schema.missing",
                         "No JSON-LD structured data in server HTML (no Person/ProfilePage entity for Google or LLMs).")

            rendered_words = self._rendered_words_jsonld(url, res)

            if rendered_words is not None and rendered_words > 0:
                gap = 1 - (raw_words / rendered_words)
                res.signal("rendered_html_words", rendered_words)
                res.signal("js_gap_ratio", round(gap, 3))
                if gap >= 0.5:
                    res.find("high", "render.spa_shell",
                             f"{gap:.0%} of page content is JS-only (server HTML has {raw_words} words, "
                             f"rendered has {rendered_words}). Non-JS crawlers and most LLM bots see almost nothing. "
                             "Prerender / SSG the routes.")
            elif raw_words < 120:
                res.find("high", "render.thin_shell",
                         f"Server HTML has only {raw_words} words of text - looks like an unprerendered SPA shell "
                         "(install the 'render' extra to quantify the JS-gap precisely).")

            # --- robots.txt + sitemap.xml ---
            self._robots_sitemap(client, url, res)

        return res

    def _rendered_words_jsonld(self, url: str, res: ProviderResult) -> int | None:
        """Optional: render with Playwright (extra) to measure the JS-gap."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            res.signal("rendered", "skipped (install 'render' extra for the JS-gap)")
            return None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(user_agent=UA)
                page.goto(url, wait_until="networkidle", timeout=30000)
                html = page.content()
                browser.close()
            soup = BeautifulSoup(html, "html.parser")
            res.signal("jsonld_types_rendered", _jsonld_types(soup))
            res.signal("h1_rendered", [h.get_text(strip=True) for h in soup.find_all("h1")])
            return _text_words(soup)
        except Exception as e:  # noqa: BLE001
            res.signal("rendered", f"error: {type(e).__name__}")
            return None

    def _robots_sitemap(self, client: httpx.Client, url: str, res: ProviderResult) -> None:
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        try:
            rb = client.get(urljoin(base, "/robots.txt"))
            res.signal("robots_txt", "ok" if rb.status_code == 200 else f"{rb.status_code}")
            if rb.status_code == 200 and "sitemap" not in rb.text.lower():
                res.find("low", "robots.no_sitemap", "robots.txt does not reference a sitemap.")
        except httpx.HTTPError:
            res.signal("robots_txt", "unreachable")
        try:
            sm = client.get(urljoin(base, "/sitemap.xml"))
            if sm.status_code == 200:
                res.signal("sitemap_urls", sm.text.count("<loc>"))
            else:
                res.signal("sitemap_xml", f"{sm.status_code}")
                res.find("medium", "sitemap.missing", "No /sitemap.xml (200).")
        except httpx.HTTPError:
            res.signal("sitemap_xml", "unreachable")
