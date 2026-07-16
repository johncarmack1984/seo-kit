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

## 2026-07-05 — optimize/2026-07-05 (re-propose, PR #24 verdict)

- Score before act: checked all `Reads-after:` dates in the entry above against today (2026-07-05) - none have passed (earliest is bing=2026-07-08). Nothing matured; no experiment to score this run.
- Prior PR #24 (same finding, same change) was closed unmerged 2026-07-05 for an unsigned commit ("Unverified commit is unmergeable"), with an explicit owner comment: "The seed-list change is welcome back under the new commit discipline." Per the closed-unmerged-PR-is-a-verdict doctrine, that comment is the invitation required to re-propose - this run does so via the signed commit tool (`mcp__github_file_ops__commit_files`), not raw `git commit`.
- Target: `dataforseo.zero_volume` (`seo-reports/seo-kit-20260705T041225Z.json`, still current at this run): "1 seed terms show ~0 volume: open source SEO audit CLI", corroborated by `trends.avg_interest_12m` for the same term at 0.0 (12-month average), the weakest of 5 seeds by a wide margin (next-lowest: "GEO audit tool" at 1.3 interest / 30/mo volume, vs. this term's 0/mo, 0.0 interest). Higher-ranked findings remain frozen/non-actionable: `serper.unranked` is the metric of the in-flight title experiment (frozen until 2026-08-02); `gsc.no_data` is inherent pipeline lag, not fixable.
- Change: `seo-kit.toml` - removed `"open source SEO audit CLI"` from `seed_keywords`, leaving the 4 seeds that all show measured demand (480, 30, 10, 10 /mo via dataforseo). No other keys touched.
- Expected movement + horizon: not a scoreboard metric - `dataforseo`/`trends` are inputs, never judged directly (per the latency table). Expected effect is measurement hygiene only: `dataforseo.zero_volume` stops recurring on the next `dataforseo` run, and `serper`'s seed list narrows from 5 to 4 demand-validated terms. No SERP or GEO movement is claimed for this change.
- Verify: localhost crawl audit against the site (unmodified by this PR) reports zero findings; `uv run pytest -q` 23 passed.

## 2026-07-05 — public flip (human)

- Repository went public (confirmed 2026-07-05T07:0xZ; anonymous API access verified, 9 topics visible). This is the predicted discontinuity for the slow lanes: serper and the GEO category probes measure a public repo from this date. Attribute movement after this point to the flip before crediting any single content change.

## 2026-07-16 — loop repair (human)

- Diagnosis: zero optimizer PRs since 2026-07-05 despite daily green runs. The 2026-07-13 run exhausted its 40-turn budget (error_max_turns), left an empty `optimize/2026-07-13` branch, and failed with no alerting; runs since concluded without writing the verdicts they owed. Root cause was a doctrine conflict: "score before you act" demands a verdict log entry, while "if nothing is actionable, do nothing - no PR, no log entry" reads as forbidding the PR that entry needs; the agent resolved it toward silence. A second gap: `gsc=` Reads-after dates can never be scored from CI inputs (the audits/latest.json tripwire excludes gsc).
- Changes: doctrine now states a matured verdict alone requires a log-entry-only PR (do-nothing narrowed to nothing-matured-AND-nothing-actionable); gsc verdicts score from committed milestone reports or record `awaiting local audit` once; the workflow prompt names the score-first duty; max-turns 40 -> 80; a failure step now opens an issue when a run dies; the empty orphan branch deleted.
- Owed verdicts outstanding for the next run to score: bing (matured 2026-07-08, current reading: rank_traffic_points 9, query_rows 0), gsc (matured 2026-07-12, no committed post-maturity milestone yet -> expect `awaiting local audit`). serper and the GEO category probes stay frozen to ~2026-08-02 with the public-flip discontinuity noted on 2026-07-05.
- Independent reading, same day (from a local full-slice audit, not CI): perplexity produced the surface's first citation (surfaced 1/5, cited 1); parametric engines still name-only. Not a verdict - the geo_probe:perplexity window (2026-07-19) has not passed - but the trend direction is right.
