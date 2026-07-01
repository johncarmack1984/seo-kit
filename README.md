# seo-kit

A real-data SEO and GEO (generative-engine optimization) audit toolkit you point at any site by URL. It measures how a surface is seen by three audiences at once and turns the gaps into a ranked punch list:

1. **Search crawlers** (Google, Bing): titles, structured data, Core Web Vitals, sitemaps.
2. **Platform-internal search** (GitHub, recruiter search): repo topics, descriptions, keyword hygiene.
3. **LLM answer engines** (the GEO layer): is the content even readable without JavaScript, and does an LLM surface and correctly identify you.

The guiding rule: the **free Tier-0 core delivers most of the value with zero spend**, and every **paid source is opt-in**. Nothing paid runs, or needs an account, until you turn it on.

## Two ways to run it

- **Portable (zero config):** pass a raw URL (`seo-kit audit https://example.com`). The URL-only providers (crawl, psi) run and give a universal technical/on-page audit on any site; the providers that need per-target config skip cleanly, so portable mode never spends. This makes seo-kit a skill you can drop on any repo's site.
- **Saved surface (full depth):** add the target to `surfaces.toml` with its per-target config (Search Console property, GitHub repo, seed keywords, GEO entity markers/probes) to unlock the keyword/SERP, Search Console, GitHub, and GEO/LLM-citation providers.

## Why it exists

Most "AI SEO" tooling either hallucinates numbers (keyword volumes with no data source) or hides everything behind a subscription. seo-kit pairs the model with real data: Search Console, PageSpeed, Bing, GitHub, and Google Trends are all free and official. The model's job is synthesis and prioritization, not inventing metrics.

## Architecture

Every data source is a `Provider` behind one interface. The orchestrator runs the enabled ones, collects ranked findings, and writes a markdown + JSON report. A target is either a raw URL (synthesized on the fly) or a `surfaces.toml` entry; providers that lack the config a URL cannot supply (Search Console property, repo, seed keywords, GEO entity) skip cleanly and say what to add.

```
config.toml      which providers run (Tier 0 on; paid tiers opt-in)
surfaces.toml    optional per-target config (url, gsc property, github repo, seed keywords, GEO entity, positioning)
.env             secrets (gitignored; mirror to a secrets manager)
seokit/
  config.py      surface model + raw-URL synthesis
  providers/     crawl, psi, gsc, github, bing, trends, dataforseo, serper, geo_probe  +  paid stubs
  audit.py       orchestrator
  report.py      markdown + json, labels stubbed tiers honestly
  cli.py         seo-kit audit <url|surface> | providers | auth gsc
```

| Tier | Providers | Cost | State |
|------|-----------|------|-------|
| 0 | crawl, psi, gsc, github, bing, trends | free | implemented |
| 1 | dataforseo, serper | cheap pay-as-you-go | implemented |
| 2 | geo_probe (Perplexity/OpenAI/Anthropic/Gemini) | usage | implemented |
| 3 | ahrefs, semrush | subscription | stub |

## Quickstart

```bash
uv sync
cp .env.example .env                            # fill Tier-0 keys (Search Console OAuth client, PageSpeed, Bing, GitHub)
uv run seo-kit audit https://example.com        # any URL: crawl + psi run, config-needing providers skip
uv run seo-kit audit https://example.com --only crawl   # no keys needed for this one
uv run seo-kit audit example.com            # a saved surface: full configured set
```

The crawl provider alone, with no keys, will tell you whether your site is a client-rendered shell that LLM crawlers cannot read, and whether it ships any structured data. That is usually the highest-leverage finding.

## Honesty about limits

Search Console lags about two days and only spans 16 months. Keyword volumes from any tool are modeled estimates. LinkedIn has no real SEO API. GEO probe results are non-deterministic and shift with model versions, so they are read as trends across repeated runs, not single answers. SEO feedback loops are weeks to months and confounded; improvements are attributed by trend, not instant causation.

## License

MIT.
