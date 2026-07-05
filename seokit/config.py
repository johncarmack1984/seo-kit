"""Config layering: machine-level lives in the tool home, target-level lives with each repo.

Tool home (this repo): .env secrets, optional config.toml provider overrides,
secrets/ token caches, surfaces.toml as the global registry. Each audited repo may
carry its own seo-kit.toml (scaffolded by `seo-kit setup`) with its surfaces +
reports_dir; ids there win over the global registry.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
LOCAL_CONFIG = "seo-kit.toml"


@dataclass
class Surface:
    id: str
    url: str
    kind: str = "site"
    gsc_property: str | None = None
    github_repo: str | None = None
    positioning: str = ""
    seed_keywords: list[str] = field(default_factory=list)
    # Optional allowlist: only these providers apply to this surface (a repo-only
    # surface keeps site-only providers like psi/gsc out). Empty -> no restriction;
    # machine-level enablement still applies either way.
    providers: list[str] = field(default_factory=list)
    # GEO probe config (per target); empty -> geo_probe skips for this surface.
    surface_markers: list[str] = field(default_factory=list)
    namesake_markers: list[str] = field(default_factory=list)
    geo_probes: list[str] = field(default_factory=list)
    cite_domains: list[str] = field(default_factory=list)


def surface_from_target(target: str) -> Surface | None:
    """Synthesize a minimal Surface from a raw URL or domain (portable mode).

    URL-only providers (crawl, psi, bing) run with no config; providers that need
    per-target config (gsc, github, keyword/SERP, GEO probes) skip cleanly. Returns
    None if the target is not URL/domain-shaped, so the caller can error.
    """
    t = target.strip()
    if "://" not in t:
        t = "https://" + t
    host = urlparse(t).netloc
    if not host or "." not in host:
        return None
    return Surface(id=host.replace("www.", ""), url=t)


def load_env() -> dict:
    load_dotenv(ROOT / ".env")
    return dict(os.environ)


def _load_toml(name: str) -> dict:
    p = ROOT / name
    if not p.exists():
        return {}
    with p.open("rb") as f:
        return tomllib.load(f)


# Built-in provider defaults: the free Tier-0 core runs everywhere — including a
# fresh install with no config.toml — and every paid tier is opt-in.
DEFAULT_PROVIDERS = {
    "crawl": True, "psi": True, "gsc": True, "github": True, "bing": True, "trends": True,
    "dataforseo": False, "serper": False, "geo_probe": False,
    "ahrefs": False, "semrush": False,
}


def load_config() -> dict:
    """config.toml (tool home) overrides DEFAULT_PROVIDERS per key; absent, defaults apply."""
    data = _load_toml("config.toml")
    data["providers"] = {**DEFAULT_PROVIDERS, **data.get("providers", {})}
    return data


def load_surfaces() -> dict[str, Surface]:
    data = _load_toml("surfaces.toml")
    return {s["id"]: Surface(**s) for s in data.get("surface", [])}


@dataclass
class LocalConfig:
    """A target repo's seo-kit.toml: its surfaces plus where its reports go."""

    path: Path
    surfaces: dict[str, Surface]
    reports_dir: Path  # absolute; resolved against the config file's directory


def find_local_config(start: Path | None = None) -> Path | None:
    """Nearest seo-kit.toml walking up from start (default cwd), so the command works from any subdirectory of a set-up repo."""
    d = (start or Path.cwd()).resolve()
    for p in (d, *d.parents):
        candidate = p / LOCAL_CONFIG
        if candidate.is_file():
            return candidate
    return None


def load_local_config(start: Path | None = None) -> LocalConfig | None:
    path = find_local_config(start)
    if not path:
        return None
    with path.open("rb") as f:
        data = tomllib.load(f)
    surfaces = {s["id"]: Surface(**s) for s in data.get("surface", [])}
    reports = data.get("seokit", {}).get("reports_dir", "seo-reports")
    return LocalConfig(path=path, surfaces=surfaces, reports_dir=(path.parent / reports).resolve())
