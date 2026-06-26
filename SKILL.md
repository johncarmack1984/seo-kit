---
name: seo-kit
description: Audit and improve SEO + GEO (LLM answer-engine citation) for a set of owned surfaces (sites, GitHub repos, profiles) using real data. Use when asked to audit, optimize, or measure a site's search visibility, Core Web Vitals, structured data, keyword/entity positioning, or whether LLMs surface and correctly identify a person/brand. Free Tier-0 providers work out of the box; paid tiers are opt-in stubs.
---

# seo-kit

A real-data SEO + GEO toolkit. It runs a set of providers against a surface and produces a prioritized audit. The design rule: the free Tier-0 core does about 80% of the value with no spend, and every paid source is an opt-in stub that is promoted only after the free pass proves it is needed.

## When to use

- "Audit example.com for SEO / GEO."
- "Is my site readable by LLM answer engines?" (the JS-gap + structured-data checks)
- "What are my real Search Console queries / Core Web Vitals?"
- "Does an LLM surface me and not confuse me with the famous John Carmack?" (Tier 2 GEO probe, once promoted)

## Run it

```bash
uv sync                                  # base deps (keyless crawl works now)
uv run seo-kit providers                 # list providers, tiers, env readiness (no secrets printed)
uv run seo-kit audit example.com --only crawl   # keyless structural pass
uv run seo-kit audit example.com     # full enabled set
```

Reports are written to `reports/<surface>-<timestamp>.md` and `.json`.

Optional capabilities install as extras (kept out of the base so the keyless audit stays fast):

```bash
uv sync --extra render     # rendered-DOM crawl (exact JS-gap %); then: uv run playwright install chromium
uv sync --extra google     # Search Console; then one-time: uv run seo-kit auth gsc
uv sync --extra trends     # Google Trends
```

## Phases (the workflow this skill follows)

1. Instrument - connect data sources per surface (see `.env.example`, `config.toml`, `surfaces.toml`).
2. Discover - pull real queries / volumes / trends + an LLM-citation baseline; build the keyword + entity map.
3. Audit - run the providers; rank findings by impact x effort.
4. Optimize - apply fixes (titles, Person schema, prerender, README/profile keywords, internal links, GEO-citable content).
5. Measure - re-run on a cadence; attribute by trend.

## Providers and tiers

- Tier 0 (free, implemented): `crawl` (on-page + render-gap), `psi` (Core Web Vitals), `gsc` (Search Console), `github` (repo signals + traffic), `bing` (Bing Webmaster, also feeds ChatGPT search), `trends` (Google Trends).
- Tier 1 (stub): `dataforseo` / `serper` - real SERP positions + search volume.
- Tier 2 (stub): `geo_probe` - LLM citation + entity-disambiguation scoring.
- Tier 3 (stub): `ahrefs` / `semrush` - backlinks + competitor gap.

## Promoting a stubbed tier

1. Implement the provider's `fetch` (the class docstring + `stub_contract` give the exact API call).
2. Add its keys to `.env` (mirror to a secrets manager; never commit them).
3. Flip its flag to `true` in `config.toml`.

Until then a stubbed provider raises `ProviderNotEnabled`, and the report lists it under "Available if promoted" with what it would add. Stubbed signals are always labeled, never silently skipped.

## Limitations (state these in any output)

- Search Console lags about 2 days and spans 16 months; early data on low-traffic pages is thin.
- All keyword volumes (once Tier 1 is on) are modeled estimates, not truth.
- LinkedIn has no real SEO API; that surface is heuristic only.
- GEO probes are non-deterministic and model-version dependent; measure trends across repeated runs, not single answers.
- SEO feedback loops are weeks to months and confounded; attribute by trend, not instant causation.
