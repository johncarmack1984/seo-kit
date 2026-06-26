"""Loads .env, config.toml, and surfaces.toml from the repo root."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

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
