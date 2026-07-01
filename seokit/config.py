"""Loads .env, config.toml, and surfaces.toml from the repo root."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Surface:
    id: str
    url: str
    kind: str = "site"
    gsc_property: str | None = None
    github_repo: str | None = None
    positioning: str = ""
    seed_keywords: list[str] = field(default_factory=list)
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


def load_config() -> dict:
    return _load_toml("config.toml")


def load_surfaces() -> dict[str, Surface]:
    data = _load_toml("surfaces.toml")
    return {s["id"]: Surface(**s) for s in data.get("surface", [])}
