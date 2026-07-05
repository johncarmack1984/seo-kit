"""`seo-kit setup`: scaffold a per-repo seo-kit.toml (the per-repo setup function).

Setup infers the mechanical fields — url (CNAME or package.json homepage),
github_repo (origin remote), the gsc_property form — and leaves the semantic
fields (positioning, seed_keywords, the GEO entity block) as commented templates:
those need repo knowledge, not inference, so the operator/skill fills them from
the repo's README, docs, and positioning notes.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def _git(cwd: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout.strip() or None


def git_root(cwd: Path) -> Path | None:
    top = _git(cwd, "rev-parse", "--show-toplevel")
    return Path(top) if top else None


def infer_github_repo(root: Path) -> str | None:
    url = _git(root, "remote", "get-url", "origin")
    if not url:
        return None
    m = re.search(r"github\.com[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def infer_url(root: Path) -> str | None:
    for cname in (root / "CNAME", root / "public" / "CNAME", root / "static" / "CNAME"):
        if cname.is_file():
            lines = [l.strip() for l in cname.read_text().splitlines() if l.strip()]
            if lines:
                return f"https://{lines[0]}/"
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            home = json.loads(pkg.read_text()).get("homepage")
        except (json.JSONDecodeError, UnicodeDecodeError):
            home = None
        if isinstance(home, str) and home.startswith(("http://", "https://")):
            return home
    return None


def scaffold_toml(surface_id: str, url: str, github_repo: str | None) -> str:
    gh_line = (
        f'github_repo = "{github_repo}"'
        if github_repo
        else '# github_repo = "owner/repo"'
    )
    return f'''\
# seo-kit per-repo config (scaffolded by `seo-kit setup`).
# This file makes the repo a saved surface: `seo-kit audit {surface_id}` runs the
# full configured provider set from any directory inside the repo and writes
# reports to reports_dir below (committed reports give you the trend history the
# Measure phase needs). Secrets and provider enablement stay in the seo-kit tool
# home — this file is safe to commit. Add more [[surface]] blocks as needed.

[seokit]
reports_dir = "seo-reports"

[[surface]]
id = "{surface_id}"
url = "{url}"
kind = "site"
# Each field below unlocks a provider for this target; fill what applies.
# gsc_property = "sc-domain:{surface_id}"  # Search Console queries; uncomment once the property is verified
{gh_line}  # GitHub repo topics / description / traffic signals
# providers = []  # optional allowlist: only these run for this surface (e.g. a repo-only surface: ["crawl", "github", "trends", "geo_probe"])
# positioning = ""  # one-line steer for the content + keyword layer
# seed_keywords = []  # unlocks trends (free) + dataforseo volume / serper SERP position (keyed)

# GEO probe (LLM citation + namesake disambiguation). Needs surface_markers +
# geo_probes; namesake_markers and cite_domains are optional (cite_domains
# defaults to the surface's domain).
# surface_markers = []  # strings that prove an answer is about THIS entity (handles, product names, domains)
# namesake_markers = []  # strings that prove the answer drifted to a namesake
# cite_domains = ["{surface_id}"]
# geo_probes = [
#     "Who or what is ... and what do they build?",
# ]
'''
