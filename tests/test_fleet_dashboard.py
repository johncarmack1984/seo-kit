import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fleet_dashboard import render  # noqa: E402


def _report(psi: float) -> dict:
    return {
        "results": [
            {
                "provider": "psi",
                "status": "ok",
                "signals": [{"key": "performance_score", "value": psi, "note": ""}],
            }
        ]
    }


def test_render_cards_and_flagships(tmp_path):
    hist = tmp_path / "x.com"
    hist.mkdir()
    (hist / "x.com-20260716T000000Z.json").write_text(json.dumps(_report(96)))
    html = render(tmp_path, ["x.com", "empty.example"])
    assert "x.com" in html and "/fleet/x.com/trend-x.com.svg" in html
    assert "PSI <b>96</b>" in html
    assert "empty.example" in html and "no reports yet" in html
    assert "johncarmack.com/audits/trend-johncarmack-com.svg" in html
    assert "prefers-color-scheme: dark" in html
    assert "noindex" in html
