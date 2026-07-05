---
name: seo-kit
description: Audit and improve SEO + GEO (LLM answer-engine citation) for ANY site using real data. Point it at a URL and it runs providers to produce a prioritized punch list across on-page/technical SEO, Core Web Vitals, structured data, keyword/entity positioning, and whether LLM answer engines surface and correctly identify a person/brand. Use when asked to audit, optimize, or measure a site's search or LLM visibility. Free Tier-0 providers work on any URL with no config; `seo-kit setup` scaffolds per-repo config for full depth; paid tiers are opt-in.
compatibility: Requires Python 3.12+ and uv. Provider API keys are optional environment variables (see .env.example); the keyless crawl audit works with none.
---

# seo-kit

A real-data SEO + GEO toolkit you point at any site. It runs a set of providers against a target and produces a prioritized audit. Design rule: the free Tier-0 core does about 80% of the value with no spend, and every paid source is opt-in.

It is modular: the `seo-kit` command is installed globally, machine-level config (secrets, provider enablement) lives in the tool home (this repo), and each audited repo carries its own `seo-kit.toml` — scaffolded by `seo-kit setup` — holding that repo's surface config and report history.

It works in three modes:

- **Portable (zero config):** pass a raw URL. The URL-only providers (`crawl` for on-page + render-gap, `psi` for Core Web Vitals) run immediately and give a universal technical/on-page audit. Providers that need per-target config skip cleanly and tell you what to add, so portable mode never spends even with paid tiers enabled. This is what makes seo-kit a skill you can drop on any repo's site.
- **Per-repo (the setup function):** run `seo-kit setup` inside a repo to scaffold `seo-kit.toml` there, then fill its per-target config (Search Console property, GitHub repo, seed keywords, GEO entity markers/probes). That unlocks the keyword/SERP, Search Console, GitHub, and GEO/LLM-citation providers for that repo's site, and its reports land in the repo itself.
- **Global registry:** targets with no repo of their own (someone else's site, a naming experiment) go in the tool home's `surfaces.toml` with the same fields.

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
seo-kit setup                             # in a target repo: scaffold its seo-kit.toml (see below)
seo-kit audit example.com                 # a configured surface id: full set for that target
seo-kit trend example.com                 # Measure phase: metric timeseries table + SVG from the report history
```

The target is a raw URL (portable mode) or a surface id; ids resolve local-first (the nearest `seo-kit.toml` walking up from cwd, then the tool home's `surfaces.toml`). Reports for a per-repo surface land in that repo's `reports_dir` (default `seo-reports/`); everything else goes to `reports/` in the tool home. (Developing in the tool repo itself? prefix `uv run`.)

One-time setup (the clone is the tool home; run from its root):

```bash
uv tool install --editable ".[google,trends]"   # the global 'seo-kit' command (editable: tracks this repo's source + keys)
seo-kit auth gsc                                 # one-time Search Console OAuth consent (caches a token)
mkdir -p ~/.claude/skills/seo-kit && ln -s "$(pwd)/SKILL.md" ~/.claude/skills/seo-kit/SKILL.md   # register this skill (skip if installed via /plugin)
```

Keys are ordinary environment variables (names in `.env.example`): set them in the tool home's `.env`, your shell, or Claude Code's `settings.json` `env` block — already-set variables win over `.env`. Every key is optional; a provider missing its key skips and says what to add.

The `render` extra (rendered-DOM crawl for the exact JS-gap %) is heavy (Playwright); add it only when needed: reinstall with `".[google,trends,render]"`, then `uv run playwright install chromium`.

## Per-repo setup (the setup function; run once per repo)

When asked to set up or deeply audit a repo's site, from anywhere inside that repo:

1. `seo-kit setup` — scaffolds `seo-kit.toml` at the repo root. It infers the mechanical fields: `url` from CNAME or package.json homepage (pass it explicitly if inference fails: `seo-kit setup https://example.com`), `github_repo` from the origin remote, and pre-forms `gsc_property` commented out (uncomment once the property is verified in Search Console).
2. Fill the semantic fields the CLI cannot infer — read the repo (README, docs, positioning notes) and write `positioning`, `seed_keywords`, and the GEO entity block (`surface_markers`, `namesake_markers`, `geo_probes`, `cite_domains`). This is the judgment step: do it, then show the user the file to confirm before spending on keyed providers.
3. `seo-kit audit <id>` — the id setup printed. Reports land in the repo's `seo-reports/` (configurable via `reports_dir` under `[seokit]`), so the audit history travels with the repo for the Measure phase.

`seo-kit.toml` is safe to commit: it holds no secrets (keys stay in the tool home's `.env`).

## Surface fields (same in seo-kit.toml and surfaces.toml)

Only `id` + `url` are required. Each extra field unlocks a provider for that target:

- `gsc_property` -> Search Console queries (`sc-domain:<domain>` or a URL-prefix property).
- `github_repo` -> GitHub repo topics / description / traffic signals.
- `providers` -> optional allowlist: only these providers apply to this surface (a repo-only surface keeps site-only providers like `psi`/`gsc` out). Empty = no restriction. Outside the allowlist a provider doesn't run even if named in `--only`.
- `seed_keywords` -> keyword volume (`dataforseo`), SERP position (`serper`), interest over time (`trends`).
- `surface_markers` + `namesake_markers` + `geo_probes` + `cite_domains` -> the GEO probe (does an answer engine surface this entity, conflate it with a namesake, cite it). Without `surface_markers` + `geo_probes` the GEO probe skips, so it never runs one target's probes against another.
- `positioning` -> a steer for the content / keyword layer.

## Where config lives (the modular layout)

- Tool home (this repo): `.env` secrets, optional `config.toml` provider overrides (`cp config.toml.example config.toml`; built-in defaults are Tier 0 on, paid tiers off), `secrets/` OAuth token cache, `surfaces.toml` global registry. Machine-level, shared by every target.
- Each audited repo: `seo-kit.toml` (surfaces + `reports_dir`) and its `seo-reports/`. Repo-level, committed with the repo.
- Resolution order for `seo-kit audit <target>`: nearest `seo-kit.toml` id -> tool-home `surfaces.toml` id -> raw URL synthesis.

## Phases (the workflow this skill follows)

1. Instrument - point at a URL (portable), or run the per-repo setup above for depth (keys: `.env.example`; provider on/off: `config.toml`).
2. Discover - pull real queries / volumes / trends + an LLM-citation baseline; build the keyword + entity map.
3. Audit - run the providers; rank findings by impact x effort.
4. Optimize - apply fixes (titles, schema, prerender, README/profile keywords, internal links, GEO-citable content).
5. Measure - re-run on a cadence; attribute by trend. `seo-kit trend <id>` renders the committed report history as a per-metric table + small-multiples SVG (gaps stay gaps; partial runs contribute only what they measured).

## Providers and tiers

- Tier 0 (free, implemented): `crawl` (on-page + render-gap, url-only), `psi` (Core Web Vitals, url-only), `gsc` (Search Console, needs `gsc_property`), `github` (repo signals, needs `github_repo`), `bing` (Bing Webmaster, also feeds ChatGPT search), `trends` (Google Trends, needs `seed_keywords`).
- Tier 1 (implemented, pay-as-you-go): `dataforseo` (search volume) / `serper` (SERP position) - need `seed_keywords` + keys.
- Tier 2 (implemented, usage-priced): `geo_probe` - LLM citation + entity-disambiguation; needs the GEO entity config + an engine key (Perplexity/OpenAI/Anthropic/Gemini).
- Tier 3 (stub): `ahrefs` / `semrush` - backlinks + competitor gap.

## Enabling paid tiers

Tiers 1-2 are implemented but off by default. To opt in: add the keys to `.env` (never commit them), then `cp config.toml.example config.toml` (if absent) and flip the tier's flags to `true`.

Tier 3 (ahrefs, semrush) is stubbed. To promote one: implement its `fetch` (the class docstring + `stub_contract` give the exact API call), add its key, flip its flag. Until then a stubbed provider raises `ProviderNotEnabled`, and the report lists it under "Available if promoted" with what it would add. Stubbed signals are always labeled, never silently skipped.

## Limitations (state these in any output)

- Search Console lags about 2 days and spans 16 months; early data on low-traffic pages is thin.
- Keyword volumes are modeled estimates, not truth.
- LinkedIn has no real SEO API; that surface is heuristic only.
- GEO probes are non-deterministic and model-version dependent; measure trends across repeated runs, not single answers.
- SEO feedback loops are weeks to months and confounded; attribute by trend, not instant causation.
