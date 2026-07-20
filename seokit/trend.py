"""Measure phase: metric timeseries from a surface's committed report history.

Reads the JSON reports the audit writes (reports_dir/<id>-<stamp>.json),
extracts a fixed set of trend metrics, and renders a small-multiples SVG —
one mini line panel per metric, shared time axis — because the metrics share
no scale (a 0-100 PSI score next to raw impressions). The SVG carries its own
prefers-color-scheme styles so it reads on light and dark when embedded via
<img> (the site, the GitHub README). Partial reports (e.g. a --only run)
contribute only the metrics they measured; gaps break the line rather than
fabricating continuity.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Fixed panel order (identity is positional; color stays constant per mode).
METRICS: list[tuple[str, str]] = [
    ("psi_score", "PageSpeed score, mobile (0-100)"),
    ("geo_surfaced", "GEO probes surfaced (all engines)"),
    ("geo_conflated", "GEO namesake conflations"),
    ("geo_cited", "GEO probes cited"),
    ("serp_ranked", "Seed keywords ranked in SERP"),
    ("gsc_clicks", "Search Console clicks (28d)"),
    ("gsc_impressions", "Search Console impressions (28d)"),
    ("gh_stars", "GitHub stars"),
    ("gh_views", "GitHub repo views (14d)"),
]

# TRIPWIRE (mirrors the one in .github/workflows/audit.yml): the report slice
# published under audits/ is kept gsc-free at audit time by the --only list, but
# the derived trend artifacts are built from a history dir that is also seeded
# with the committed seo-reports/*.json — and those DO carry Search Console
# data. Anything bound for the public bucket drops these metrics first.
PRIVATE_METRICS: frozenset[str] = frozenset({"gsc_clicks", "gsc_impressions"})

_GEO = re.compile(r"surfaced (\d+)/(\d+), conflated (\d+), cited (\d+)")


@dataclass
class Snapshot:
    stamp: datetime
    metrics: dict[str, float]


def _signals(result: dict) -> dict:
    return {s["key"]: s["value"] for s in result.get("signals", [])}


def extract_metrics(report: dict) -> dict[str, float]:
    """Pull the trend metrics out of one report's JSON; absent providers -> absent keys."""
    out: dict[str, float] = {}
    for r in report.get("results", []):
        if r.get("status") != "ok":
            continue
        sig = _signals(r)
        p = r.get("provider")
        if p == "psi" and sig.get("performance_score") is not None:
            out["psi_score"] = float(sig["performance_score"])
        elif p == "gsc":
            if sig.get("total_clicks_28d") is not None:
                out["gsc_clicks"] = float(sig["total_clicks_28d"])
            if sig.get("total_impressions_28d") is not None:
                out["gsc_impressions"] = float(sig["total_impressions_28d"])
        elif p == "github":
            if sig.get("stars") is not None:
                out["gh_stars"] = float(sig["stars"])
            if isinstance(sig.get("views_14d"), (int, float)):
                out["gh_views"] = float(sig["views_14d"])
        elif p == "serper" and isinstance(sig.get("serp_positions"), list):
            out["serp_ranked"] = float(sum(1 for s in sig["serp_positions"] if "#" in str(s)))
        elif p == "geo_probe":
            surfaced = conflated = cited = 0
            matched = False
            for v in sig.values():
                m = _GEO.search(str(v))
                if m:
                    matched = True
                    surfaced += int(m.group(1))
                    conflated += int(m.group(3))
                    cited += int(m.group(4))
            if matched:
                out["geo_surfaced"] = float(surfaced)
                out["geo_conflated"] = float(conflated)
                out["geo_cited"] = float(cited)
    return out


def load_series(reports_dir: Path, surface_id: str) -> list[Snapshot]:
    snaps: list[Snapshot] = []
    for p in sorted(reports_dir.glob(f"{surface_id}-*.json")):
        stamp_raw = p.stem[len(surface_id) + 1 :]
        try:
            stamp = datetime.strptime(stamp_raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        try:
            report = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        snaps.append(Snapshot(stamp=stamp, metrics=extract_metrics(report)))
    return snaps


def public_slice(snaps: list[Snapshot]) -> list[Snapshot]:
    """Drop the metrics that must never reach the public audits/ slice (see PRIVATE_METRICS)."""
    return [
        Snapshot(stamp=s.stamp, metrics={k: v for k, v in s.metrics.items() if k not in PRIVATE_METRICS})
        for s in snaps
    ]


def series_json(snaps: list[Snapshot], surface_id: str) -> dict:
    """The same series the SVG plots, as data: one object per reading, oldest first.

    This is the optimizer's history input. It exists so a verdict can quote a past
    reading instead of reconstructing it from the log's prose — the failure that
    produced a fabricated 2026-07-16 conflation value in PR #42.
    """
    return {
        "surface": surface_id,
        "metrics": {k: label for k, label in METRICS if any(k in s.metrics for s in snaps)},
        "series": [
            {
                "stamp": s.stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **{k: s.metrics[k] for k, _ in METRICS if k in s.metrics},
            }
            for s in snaps
        ],
    }


# --- SVG rendering -----------------------------------------------------------

W = 720
PANEL_H = 70
PLOT_H = 34
LABEL_H = 22  # panel label row; the plot band starts below it so a max-value dot can't collide
PAD_TOP = 46
PAD_BOTTOM = 30
X0, X1 = 16, W - 116
VAL_X = X1 + 12

# Literal colors, overridden wholesale in the dark block: CSS custom properties
# render inconsistently in SVG-as-image contexts (Quick Look et al.), so no var().
_CSS = """
  .bg   { fill: #faf9f7; }
  text { font: 12px ui-sans-serif, system-ui, sans-serif; fill: #21201d; }
  .muted { fill: #6d685e; font-size: 11px; }
  .val { font-family: ui-monospace, Menlo, monospace; }
  .grid { stroke: #dcd9d2; stroke-width: 1; }
  .line { stroke: #a36a10; stroke-width: 2; fill: none; }
  .dot  { fill: #a36a10; stroke: #faf9f7; stroke-width: 2; }
  @media (prefers-color-scheme: dark) {
    .bg   { fill: #151312; }
    text { fill: #e8e5de; }
    .muted { fill: #a29c90; }
    .grid { stroke: #2e2b27; }
    .line { stroke: #b57e1c; }
    .dot  { fill: #b57e1c; stroke: #151312; }
  }
"""


def _fmt_val(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def _runs(points: list[tuple[int, float | None]]) -> list[list[tuple[int, float]]]:
    """Split into runs of consecutive present values; a gap breaks the line."""
    runs: list[list[tuple[int, float]]] = []
    cur: list[tuple[int, float]] = []
    for i, v in points:
        if v is None:
            if cur:
                runs.append(cur)
            cur = []
        else:
            cur.append((i, v))
    if cur:
        runs.append(cur)
    return runs


def render_svg(snaps: list[Snapshot], surface_id: str) -> str:
    stamps = [s.stamp for s in snaps]
    t0, t1 = min(stamps), max(stamps)
    span = max((t1 - t0).total_seconds(), 1.0)
    # Sub-two-day histories need times, not just dates, on the axis.
    axis_fmt = "%b %d %H:%M" if span < 48 * 3600 else "%b %d"

    def x_at(t: datetime) -> float:
        return X0 + (X1 - X0) * ((t - t0).total_seconds() / span)

    panels = [(k, label) for k, label in METRICS if any(k in s.metrics for s in snaps)]
    height = PAD_TOP + len(panels) * PANEL_H + PAD_BOTTOM

    out: list[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" '
        f'height="{height}" role="img" aria-labelledby="t d">'
    )
    out.append(f'<title id="t">seo-kit audit trend for {surface_id}</title>')
    out.append(
        f'<desc id="d">Small-multiple line charts of audit metrics across {len(snaps)} '
        f"audits from {t0:%Y-%m-%d} to {t1:%Y-%m-%d}. Data: the seo-reports directory.</desc>"
    )
    out.append(f"<style>{_CSS}</style>")
    # The panel paints its own background (site --bg, both schemes): the media
    # query tracks the VIEWER's scheme, not the page behind the SVG, so a
    # transparent panel goes unreadable the moment a dark-mode user opens the
    # raw URL on the browser's white canvas.
    out.append('<rect class="bg" width="100%" height="100%"/>')
    out.append(f'<text x="{X0}" y="22" style="font-weight:600">seo-kit audit trend - {surface_id}</text>')
    out.append(f'<text x="{X0}" y="38" class="muted">{len(snaps)} audits, {t0:%b %d} to {t1:%b %d %Y} (UTC)</text>')

    for idx, (key, label) in enumerate(panels):
        top = PAD_TOP + idx * PANEL_H
        base = top + LABEL_H + PLOT_H
        ymax = 100.0 if key == "psi_score" else max(1.0, *(s.metrics.get(key, 0.0) for s in snaps)) * 1.15

        def y_at(v: float) -> float:
            return base - (PLOT_H * (v / ymax))

        out.append(f'<text x="{X0}" y="{top + 10}">{label}</text>')
        out.append(f'<line x1="{X0}" y1="{base}" x2="{X1}" y2="{base}" class="grid"/>')

        pts = [(i, s.metrics.get(key)) for i, s in enumerate(snaps)]
        last_val: float | None = None
        for run in _runs(pts):
            coords = [(x_at(snaps[i].stamp), y_at(v)) for i, v in run]
            if len(coords) > 1:
                path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
                out.append(f'<polyline class="line" points="{path}"/>')
            for x, y in coords:
                out.append(f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="4"/>')
            last_val = run[-1][1]
        if last_val is not None:
            out.append(f'<text x="{VAL_X}" y="{base - 2}" class="val">{_fmt_val(last_val)}</text>')

    axis_y = PAD_TOP + len(panels) * PANEL_H + 14
    out.append(f'<text x="{X0}" y="{axis_y}" class="muted">{t0.strftime(axis_fmt)}</text>')
    out.append(f'<text x="{X1}" y="{axis_y}" class="muted" text-anchor="end">{t1.strftime(axis_fmt)}</text>')
    out.append("</svg>")
    return "\n".join(out)
