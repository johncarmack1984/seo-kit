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
    # Fixture ids stay dot-free and assertions anchor to full attribute values:
    # a bare domain-shaped substring check reads to CodeQL as the buggy
    # URL-allowlist idiom (py/incomplete-url-substring-sanitization).
    hist = tmp_path / "demo-surface"
    hist.mkdir()
    (hist / "demo-surface-20260716T000000Z.json").write_text(json.dumps(_report(96)))
    html = render(tmp_path, ["demo-surface", "empty-surface"])
    assert "<h3>demo-surface</h3>" in html
    assert 'src="/fleet/demo-surface/trend-demo-surface.svg"' in html
    assert "PSI <b>96</b>" in html
    assert "<h3>empty-surface</h3>" in html
    assert "no reports yet" in html
    assert 'src="https://johncarmack.com/audits/trend-johncarmack-com.svg"' in html
    assert "prefers-color-scheme: dark" in html
    assert "noindex" in html
