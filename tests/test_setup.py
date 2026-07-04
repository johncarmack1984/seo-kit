"""The per-repo scaffold: inference inputs and a template that parses."""
import json
import tomllib

from seokit.setup import infer_url, scaffold_toml


def test_scaffold_is_valid_toml_with_expected_fields():
    text = scaffold_toml("example.com", "https://example.com/", "owner/repo")
    data = tomllib.loads(text)
    assert data["seokit"]["reports_dir"] == "seo-reports"
    (surface,) = data["surface"]
    assert surface["id"] == "example.com"
    assert surface["url"] == "https://example.com/"
    assert surface["github_repo"] == "owner/repo"


def test_scaffold_without_github_repo_comments_the_line():
    text = scaffold_toml("example.com", "https://example.com/", None)
    (surface,) = tomllib.loads(text)["surface"]
    assert "github_repo" not in surface
    assert '# github_repo = "owner/repo"' in text


def test_infer_url_from_cname(tmp_path):
    (tmp_path / "CNAME").write_text("example.com\n")
    assert infer_url(tmp_path) == "https://example.com/"


def test_infer_url_from_package_json_homepage(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"homepage": "https://example.com"}))
    assert infer_url(tmp_path) == "https://example.com"


def test_infer_url_none_when_no_sources(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"homepage": "not-a-url"}))
    assert infer_url(tmp_path) is None
