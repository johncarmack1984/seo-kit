---
name: seo-kit
description: Audit and improve SEO + GEO (LLM answer-engine citation) for ANY site using real data. Point it at a URL and it runs providers to produce a prioritized punch list across on-page/technical SEO, Core Web Vitals, structured data, keyword/entity positioning, and whether LLM answer engines surface and correctly identify a person/brand. Use when asked to audit, optimize, or measure a site's search or LLM visibility. Free Tier-0 providers work on any URL with no config; deeper per-target checks add config; paid tiers are opt-in.
---

# seo-kit

A real-data SEO + GEO toolkit you point at any site. It runs a set of providers against a target and produces a prioritized audit. Design rule: the free Tier-0 core does about 80% of the value with no spend, and every paid source is opt-in.

It works in two modes:

- **Portable (zero config):** pass a raw URL. The URL-only providers (`crawl` for on-page + render-gap, `psi` for Core Web Vitals) run immediately and give a universal technical/on-page audit. Providers that need per-target config skip cleanly and tell you what to add, so portable mode never spends even with paid tiers enabled. This is what makes seo-kit a skill you can drop on any repo's site.
- **Saved surface (full depth):** add the target to `surfaces.toml` with its per-target config (Search Console property, GitHub repo, seed keywords, GEO entity markers/probes). That unlocks the keyword/SERP, Search Console, GitHub, and GEO/LLM-citation providers for that target.

## When to use

- "Audit https://example.com for SEO / GEO." (any site, by URL)
- "Is my site readable by LLM answer engines?" (the JS-gap + structured-data checks)
- "What are my real Search Console queries / Core Web Vitals?" (needs the GSC property configured)
- "Does an LLM surface this person/brand and not confuse them with a namesake?" (the GEO probe, with entity config)

## Run it

Installed as a global command (`seo-kit`), so it runs from any repo and reads its keys/config from this repo:

```bash
seo-kit providers                         # list providers, tiers, env readiness (no secrets printed)
seo-kit audit https://example.com         # ANY url: crawl + psi run; config-needing providers skip
seo-kit audit https://example.com --only crawl   # keyless structural pass only
seo-kit audit example.com             # a saved surface id: full configured set
```

The target is a raw URL (portable mode) or a `surfaces.toml` id (saved-surface mode). Reports are written to `reports/<target>-<timestamp>.md` and `.json` in this repo. (Developing in the repo itself? prefix `uv run`.)

One-time setup (from this repo root):

```bash
uv tool install --editable ".[google,trends]"   # the global 'seo-kit' command (editable: tracks this repo's source + keys)
seo-kit auth gsc                                 # one-time Search Console OAuth consent (caches a token)
```

The `render` extra (rendered-DOM crawl for the exact JS-gap %) is heavy (Playwright); add it only when needed: reinstall with `".[google,trends,render]"`, then `uv run playwright install chromium`.

## Configuring a target for full depth

Add a `[[surface]]` to `surfaces.toml`. Only `id` + `url` are required (portable mode, saved). Each extra field unlocks a provider for that target:

- `gsc_property` -> Search Console queries (`sc-domain:<domain>` or a URL-prefix property).
- `github_repo` -> GitHub repo topics / description / traffic signals.
- `seed_keywords` -> keyword volume (`dataforseo`), SERP position (`serper`), interest over time (`trends`).
- `surface_markers` + `namesake_markers` + `geo_probes` + `cite_domains` -> the GEO probe (does an answer engine surface this entity, conflate it with a namesake, cite it). Without `surface_markers` + `geo_probes` the GEO probe skips, so it never runs one target's probes against another.
- `positioning` -> a steer for the content / keyword layer.

## Phases (the workflow this skill follows)

1. Instrument - point at a URL (portable), or add a surface for depth (see `.env.example`, `config.toml`, `surfaces.toml`).
2. Discover - pull real queries / volumes / trends + an LLM-citation baseline; build the keyword + entity map.
3. Audit - run the providers; rank findings by impact x effort.
4. Optimize - apply fixes (titles, schema, prerender, README/profile keywords, internal links, GEO-citable content).
5. Measure - re-run on a cadence; attribute by trend.

## Providers and tiers

- Tier 0 (free, implemented): `crawl` (on-page + render-gap, url-only), `psi` (Core Web Vitals, url-only), `gsc` (Search Console, needs `gsc_property`), `github` (repo signals, needs `github_repo`), `bing` (Bing Webmaster, also feeds ChatGPT search), `trends` (Google Trends, needs `seed_keywords`).
- Tier 1 (implemented, pay-as-you-go): `dataforseo` (search volume) / `serper` (SERP position) - need `seed_keywords` + keys.
- Tier 2 (implemented, usage-priced): `geo_probe` - LLM citation + entity-disambiguation; needs the GEO entity config + an engine key (Perplexity/OpenAI/Anthropic/Gemini).
- Tier 3 (stub): `ahrefs` / `semrush` - backlinks + competitor gap.

## Promoting a stubbed tier

1. Implement the provider's `fetch` (the class docstring + `stub_contract` give the exact API call).
2. Add its keys to `.env` (mirror to a secrets manager; never commit them).
3. Flip its flag to `true` in `config.toml`.

Until then a stubbed provider raises `ProviderNotEnabled`, and the report lists it under "Available if promoted" with what it would add. Stubbed signals are always labeled, never silently skipped.

## Limitations (state these in any output)

- Search Console lags about 2 days and spans 16 months; early data on low-traffic pages is thin.
- Keyword volumes are modeled estimates, not truth.
- LinkedIn has no real SEO API; that surface is heuristic only.
- GEO probes are non-deterministic and model-version dependent; measure trends across repeated runs, not single answers.
- SEO feedback loops are weeks to months and confounded; attribute by trend, not instant causation.
