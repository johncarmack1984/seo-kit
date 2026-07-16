"""Trend series extraction and the small-multiples SVG renderer."""
import json
import xml.etree.ElementTree as ET

from seokit.trend import extract_metrics, load_series, render_svg


def _report(providers: dict) -> dict:
    results = []
    for name, signals in providers.items():
        results.append({
            "provider": name, "status": "ok",
            "signals": [{"key": k, "value": v, "note": ""} for k, v in signals.items()],
        })
    return {"surface": {"id": "x.com"}, "results": results}


FULL_1 = _report({
    "psi": {"performance_score": 100},
    "github": {"stars": 0, "views_14d": 0},
    "serper": {"serp_positions": ["kw a: not in top 10", "kw b: not in top 8"]},
    "geo_probe": {
        "perplexity": "surfaced 1/5, conflated 0, cited 0",
        "openai": "surfaced 1/5, conflated 1, cited 0",
    },
})
PARTIAL = _report({"github": {"stars": 2, "views_14d": 31}})
FULL_2 = _report({
    "psi": {"performance_score": 98},
    "github": {"stars": 5, "views_14d": 90},
    "serper": {"serp_positions": ["kw a: #7", "kw b: not in top 8"]},
    "geo_probe": {
        "perplexity": "surfaced 3/5, conflated 0, cited 2",
        "openai": "surfaced 2/5, conflated 0, cited 0",
    },
})


def _write_reports(tmp_path):
    for stamp, rep in [
        ("20260626T120000Z", FULL_1),
        ("20260701T120000Z", PARTIAL),
        ("20260704T120000Z", FULL_2),
    ]:
        (tmp_path / f"x.com-{stamp}.json").write_text(json.dumps(rep))
    (tmp_path / "other.com-20260701T120000Z.json").write_text(json.dumps(FULL_1))


def test_extract_sums_geo_across_engines():
    m = extract_metrics(FULL_1)
    assert m["geo_surfaced"] == 2
    assert m["geo_conflated"] == 1
    assert m["geo_cited"] == 0
    assert m["serp_ranked"] == 0
    assert m["psi_score"] == 100


def test_load_series_sorted_and_scoped_to_surface(tmp_path):
    _write_reports(tmp_path)
    snaps = load_series(tmp_path, "x.com")
    assert len(snaps) == 3
    assert snaps[0].stamp < snaps[1].stamp < snaps[2].stamp
    assert "psi_score" not in snaps[1].metrics  # partial report: only github metrics
    assert snaps[1].metrics["gh_stars"] == 2


def test_svg_renders_present_panels_with_gaps(tmp_path):
    _write_reports(tmp_path)
    snaps = load_series(tmp_path, "x.com")
    svg = render_svg(snaps, "x.com")
    ET.fromstring(svg)  # well-formed XML
    assert "prefers-color-scheme: dark" in svg
    assert 'class="bg"' in svg  # self-painted background: readable on any page
    assert "PageSpeed score" in svg
    assert "GitHub stars" in svg
    assert "Search Console clicks" not in svg  # no gsc data -> no panel
    # psi exists at snaps 0 and 2 with a gap between: two isolated dots, no line
    assert svg.count('class="dot"') >= 8
    # github has all three points: at least one polyline connects a run
    assert 'class="line"' in svg
