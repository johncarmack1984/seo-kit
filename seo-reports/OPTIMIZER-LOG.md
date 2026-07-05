# Optimizer log

One entry per optimizer PR: date, finding targeted, change, expected movement + horizon. The daily optimizer reads this before acting — it is the loop's memory. Notes on whether past predictions came true belong here too.

## 2026-07-05 — bootstrap (human)

- Baseline state: crawl clean, PSI 100, GEO surfaced 4/20 probes (name-only), 0 citations, 1 conflation observed in one run (not yet signal), SERP unranked on all seeds, GSC at zero (property hours old), repo private (topics + homepage set).
- Known pending causes, no action warranted: repo public flip (expected to move GEO category probes + SERP), GSC lag (~2 days), site indexing (sitemap submitted via robots.txt only).
- Open proposals for humans: none.

## 2026-07-05 — optimize/2026-07-05

- Note: `audits/latest.json` 404'd this run (S3/CloudFront publish step in `.github/workflows/audit.yml` hadn't landed a copy yet); fell back to the committed `seo-reports/seo-kit-20260705T*.json` history per the input order.
- Target: `serper:serper.unranked` (seo-kit.johncarmack.com ranks for none of the seed keywords) - narrowed to its root cause: `seed_keywords[0]` in `seo-kit.toml`, "generative engine optimization tool", is the seed with by far the highest measured demand (dataforseo 480/mo vs 30/mo next; trends avg_interest_12m 42.3 vs 9.1 next) yet the exact phrase "generative engine optimization" appeared nowhere in the page's crawlable title/meta/og/twitter text (only inside the JSON-LD description string).
- Change: `site/index.html` - `<title>`, `og:title`, `twitter:title` reworded from "seo-kit - real-data SEO + GEO audit CLI" to "seo-kit - generative engine optimization (GEO) audit CLI" (56 chars, within the crawl provider's 15-65 aim). No other copy touched; meta description and H1 left as-is for the next pass.
- Expected movement + horizon: title/meta relevance for "generative engine optimization tool" improves first (visible next `crawl` run); any `serper` SERP-position movement is a multi-week-to-month SEO lag - do not expect it before 3+ weekly `serper` runs trend the same direction.
- Verify: localhost crawl audit against the modified page reported zero findings ("No issues flagged by the enabled providers"), `title_len: 56`; `uv run pytest -q` 23 passed.
