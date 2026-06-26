# seo-kit

A real-data SEO and GEO (generative-engine optimization) audit toolkit. It measures how a surface is seen by three audiences at once and turns the gaps into a ranked punch list:

1. **Search crawlers** (Google, Bing): titles, structured data, Core Web Vitals, sitemaps.
2. **Platform-internal search** (GitHub, recruiter search): repo topics, descriptions, keyword hygiene.
3. **LLM answer engines** (the GEO layer): is the content even readable without JavaScript, and does an LLM surface and correctly identify you.

The guiding rule: the **free Tier-0 core delivers most of the value with zero spend**, and every **paid source is an opt-in stub** that you promote only after the free pass proves it is worth it. Nothing paid runs, or needs an account, until you turn it on.

## Why it exists

Most "AI SEO" tooling either hallucinates numbers (keyword volumes with no data source) or hides everything behind a subscription. seo-kit pairs the model with real data: Search Console, PageSpeed, Bing, GitHub, and Google Trends are all free and official. The model's job is synthesis and prioritization, not inventing metrics.

## Architecture

Every data source is a `Provider` behind one interface. The orchestrator runs the enabled ones, collects ranked findings, and writes a markdown + JSON report. Paid providers are stubs that raise `ProviderNotEnabled` carrying a promotion contract, so the report can say exactly what turning them on would add.

```
config.toml      which providers run (Tier 0 on; paid tiers off/stubbed)
surfaces.toml    the targets (url, gsc property, github repo, seed keywords, positioning)
.env             secrets (gitignored; mirror to a secrets manager)
seokit/
  providers/     crawl, psi, gsc, github, bing, trends  +  paid stubs
  audit.py       orchestrator
  report.py      markdown + json, labels stubbed tiers honestly
  cli.py         seo-kit audit | providers | auth gsc
```

| Tier | Providers | Cost | State |
|------|-----------|------|-------|
| 0 | crawl, psi, gsc, github, bing, trends | free | implemented |
| 1 | dataforseo, serper | cheap pay-as-you-go | stub |
| 2 | geo_probe (Perplexity/OpenAI/Anthropic) | usage | stub |
| 3 | ahrefs, semrush | subscription | stub |

## Quickstart

```bash
uv sync
cp .env.example .env          # fill Tier-0 keys (Search Console OAuth client, PageSpeed, Bing, GitHub)
uv run seo-kit audit example.com --only crawl   # no keys needed for this one
uv run seo-kit audit example.com                # full enabled set
```

The crawl provider alone, with no keys, will tell you whether your site is a client-rendered shell that LLM crawlers cannot read, and whether it ships any structured data. That is usually the highest-leverage finding.

## Honesty about limits

Search Console lags about two days and only spans 16 months. Keyword volumes from any tool are modeled estimates. LinkedIn has no real SEO API. GEO probe results are non-deterministic and shift with model versions, so they are read as trends across repeated runs, not single answers. SEO feedback loops are weeks to months and confounded; improvements are attributed by trend, not instant causation.

## License

MIT.
