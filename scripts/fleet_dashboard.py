"""Render the private fleet dashboard (dashboard.johncarmack.com) as one page.

Reads each surface's synced report history (hist/<id>/*.json, the same
directory the fleet workflow already builds for trend rendering), pulls the
latest snapshot's numbers through seokit.trend's own extractor so the page and
the graphs can never disagree, and writes a self-contained index.html that
embeds the per-surface trend SVGs (served beside it under /fleet/) plus the
two public flagship trends by absolute URL.

Usage: uv run python scripts/fleet_dashboard.py --hist-dir hist --out index.html \
           --surfaces "vegify.app orreryhq.com ..."
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from seokit.trend import load_series

FLAGSHIPS = [
    ("seo-kit.johncarmack.com", "https://seo-kit.johncarmack.com/trend-seo-kit.svg"),
    ("johncarmack.com", "https://johncarmack.com/audits/trend-johncarmack-com.svg"),
]

# Metric key -> short chip label, in display order. Absent keys don't render.
CHIPS = [
    ("psi_score", "PSI"),
    ("geo_surfaced", "GEO surfaced"),
    ("geo_cited", "GEO cited"),
    ("geo_conflated", "conflated"),
    ("serp_ranked", "SERP ranked"),
    ("gsc_impressions", "GSC impr 28d"),
    ("gsc_clicks", "GSC clicks 28d"),
    ("gh_stars", "stars"),
]

_CSS = """
  :root { --bg: #faf9f7; --ink: #21201d; --muted: #6d685e; --card: #ffffff; --edge: #dcd9d2; --accent: #a36a10; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #151312; --ink: #e8e5de; --muted: #a29c90; --card: #1d1a18; --edge: #2e2b27; --accent: #d99a2b; }
  }
  * { box-sizing: border-box; }
  body { font: 15px/1.5 ui-sans-serif, system-ui, sans-serif; background: var(--bg); color: var(--ink); margin: 2rem auto; max-width: 1240px; padding: 0 1rem; }
  h1 { font-size: 1.3rem; margin: 0 0 .25rem; }
  h2 { font-size: 1.05rem; color: var(--accent); margin: 2rem 0 .75rem; }
  .meta { color: var(--muted); font-size: .85rem; margin: 0 0 1rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(560px, 1fr)); gap: 1rem; }
  .card { background: var(--card); border: 1px solid var(--edge); border-radius: 8px; padding: 1rem; }
  .card h3 { margin: 0 0 .5rem; font-size: 1rem; }
  .chips { display: flex; flex-wrap: wrap; gap: .35rem .5rem; margin: 0 0 .75rem; padding: 0; list-style: none; }
  .chips li { font: 12px ui-monospace, Menlo, monospace; color: var(--muted); border: 1px solid var(--edge); border-radius: 999px; padding: .1rem .55rem; }
  .chips b { color: var(--ink); font-weight: 600; }
  .card img { width: 100%; height: auto; border-radius: 4px; }
"""


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def _card(name: str, img_src: str, metrics: dict[str, float] | None, note: str = "") -> str:
    chips = ""
    if metrics:
        items = [
            f"<li>{escape(label)} <b>{_fmt(metrics[key])}</b></li>"
            for key, label in CHIPS
            if key in metrics
        ]
        chips = f'<ul class="chips">{"".join(items)}</ul>' if items else ""
    note_html = f'<p class="meta">{escape(note)}</p>' if note else ""
    return (
        f'<div class="card"><h3>{escape(name)}</h3>{note_html}{chips}'
        f'<img src="{escape(img_src)}" alt="audit trend for {escape(name)}" loading="lazy"></div>'
    )


def render(hist_dir: Path, surfaces: list[str]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fleet_cards = []
    for s in surfaces:
        snaps = load_series(hist_dir / s, s)
        latest = snaps[-1].metrics if snaps else None
        audited = f"{len(snaps)} audits" if snaps else "no reports yet"
        fleet_cards.append(_card(s, f"/fleet/{s}/trend-{s}.svg", latest, audited))
    flagship_cards = [
        _card(name, url, None, "history + numbers on the public graph") for name, url in FLAGSHIPS
    ]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>seo fleet dashboard</title>
<style>{_CSS}</style></head><body>
<h1>seo fleet dashboard</h1>
<p class="meta">Generated {stamp} by the audit-fleet run. Fleet graphs update daily (11:38 UTC); flagship graphs are the live public ones.</p>
<h2>Fleet</h2>
<div class="grid">{"".join(fleet_cards)}</div>
<h2>Flagships</h2>
<div class="grid">{"".join(flagship_cards)}</div>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hist-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--surfaces", required=True, help="space-separated surface ids")
    args = ap.parse_args()
    html = render(Path(args.hist_dir), args.surfaces.split())
    Path(args.out).write_text(html)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
