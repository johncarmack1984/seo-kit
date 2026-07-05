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
- Review amendment (2026-07-05, human gate): targeting kept, casualty reverted. Title is now "seo-kit - real-data SEO + generative engine optimization audits" (63 chars): "real-data" is the differentiator answer engines should quote and "SEO" keeps the category explicit; "CLI" lives in the meta description and the literal "GEO audit" phrase stays covered by the H1. Doctrine gained positioning invariants so relevance wins stop deleting positioning copy.

## 2026-07-05 — baseline reset (human)

- Past is prologue: all pre-baseline readings (system-construction noise: partial runs, pre-title, pre-bing, pre-gates) cleared from HEAD and from the S3 audits/ prefix; they remain in git history. `seo-kit-20260705T041225Z` is t=0: final site state (title experiment merged 2026-07-05T03:07Z, bing live, audits gate up, all providers).
- Title experiment (PR #6) scored for crawl at t=0: new title serves in server HTML, zero crawl findings. Confirmed.
- Reads-after (from merge 2026-07-05T03:07Z): bing=2026-07-08, gsc=2026-07-12, geo_probe:perplexity=2026-07-19, serper=2026-08-02. serper and the GEO category probes will also carry the public-flip discontinuity; attribute accordingly.

## 2026-07-05 — optimize/2026-07-05 (score pass)

- Scored the baseline-reset Reads-after dates against today (2026-07-05): none have passed (bing 07-08, gsc 07-12, geo_probe:perplexity 07-19, serper 08-02 all still ahead). Nothing matured. `serper:serper.unranked` is frozen - it's the metric targeted by the still-open-horizon title experiment (merged today), so it is not actionable again until 2026-08-02 regardless of what today's readings show. `gsc.no_data` is inherent pipeline lag, not a fix-able finding, per the latency table's own note ("zero impressions may mean not reindexed yet").
- Target: `dataforseo.zero_volume` (`seo-reports/seo-kit-20260705T041225Z.json`) - "1 seed terms show ~0 volume: open source SEO audit CLI" - corroborated by `trends.avg_interest_12m` showing the same term at 0.0 (12-month average), the weakest of all 5 seeds by a wide margin (next-lowest is "GEO audit tool" at 1.3 interest / 30/mo volume). The latency table classifies dataforseo/trends as "input for choices, never a scoreboard" - this is exactly that choice.
- Change: `seo-kit.toml` - removed `"open source SEO audit CLI"` from `seed_keywords`, leaving the 4 seeds that all show measured demand (480, 30, 10, 10 /mo). No other keys touched.
- Expected movement + horizon: not a scoreboard metric - dataforseo/trends are inputs, never judged directly. Expected effect is measurement hygiene: the `dataforseo.zero_volume` finding stops recurring on the next `dataforseo`/`trends`/`serper` run (reflects the config change immediately, same as `crawl`), and `serper`'s seed list narrows from 5 to 4 demand-validated terms. No claim of SERP or GEO movement is made for this change.
- Verify: localhost crawl audit against the (unmodified) site reported zero findings ("No issues flagged by the enabled providers"); `uv run pytest -q` 23 passed.
- Reads-after: n/a (no scoreboard metric targeted; this is a seed-list hygiene change, confirmed on the next dataforseo/trends/serper run whenever it lands).
