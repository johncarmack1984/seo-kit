"""Surface synthesis, provider defaults, and the local-config discovery walk."""
import seokit.config as config
from seokit.config import (
    DEFAULT_PROVIDERS,
    find_local_config,
    load_config,
    load_local_config,
    surface_from_target,
)


def test_surface_from_url_strips_www():
    s = surface_from_target("https://www.example.com/path")
    assert s.id == "example.com"
    assert s.url == "https://www.example.com/path"


def test_surface_from_bare_domain_gets_https():
    s = surface_from_target("example.com")
    assert s.id == "example.com"
    assert s.url == "https://example.com"


def test_surface_rejects_non_urls():
    assert surface_from_target("definitely-not-a-url") is None
    assert surface_from_target("localhost") is None
    assert surface_from_target("") is None


def test_defaults_apply_without_config_toml(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    providers = load_config()["providers"]
    assert providers == DEFAULT_PROVIDERS
    assert providers["crawl"] is True  # Tier 0 on out of the box
    assert providers["dataforseo"] is False  # paid tiers opt-in


def test_config_toml_overrides_merge_over_defaults(monkeypatch, tmp_path):
    (tmp_path / "config.toml").write_text("[providers]\ndataforseo = true\ncrawl = false\n")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    providers = load_config()["providers"]
    assert providers["dataforseo"] is True
    assert providers["crawl"] is False
    assert providers["psi"] is True  # untouched keys keep their default


def test_find_local_config_nearest_wins(tmp_path):
    (tmp_path / "seo-kit.toml").write_text("")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_local_config(nested) == tmp_path / "seo-kit.toml"
    (tmp_path / "a" / "seo-kit.toml").write_text("")
    assert find_local_config(nested) == tmp_path / "a" / "seo-kit.toml"


def test_load_local_config_resolves_reports_dir(tmp_path):
    (tmp_path / "seo-kit.toml").write_text(
        '[seokit]\nreports_dir = "out"\n\n[[surface]]\nid = "x.com"\nurl = "https://x.com/"\n'
    )
    lc = load_local_config(tmp_path)
    assert lc.reports_dir == (tmp_path / "out").resolve()
    assert lc.surfaces["x.com"].url == "https://x.com/"
