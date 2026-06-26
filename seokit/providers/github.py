"""Tier 0 - GitHub repo signals + traffic. Needs GITHUB_TOKEN (traffic needs push scope)."""
from __future__ import annotations

import httpx

from .base import Provider, ProviderResult, Tier


class GithubProvider(Provider):
    name = "github"
    tier = Tier.FREE
    requires_env = ["GITHUB_TOKEN"]

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        res = ProviderResult(provider=self.name, tier=self.tier)
        repo = surface.github_repo
        if not repo:
            res.status = "skipped"
            res.find("low", "github.no_repo", "surface has no github_repo set.")
            return res

        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        token = self.env.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        with httpx.Client(timeout=20.0, headers=headers, base_url="https://api.github.com") as c:
            meta = c.get(f"/repos/{repo}")
            meta.raise_for_status()
            m = meta.json()
            res.signal("description", m.get("description"))
            res.signal("topics", m.get("topics", []))
            res.signal("stars", m.get("stargazers_count"))
            res.signal("homepage", m.get("homepage"))
            if not m.get("description"):
                res.find("medium", "github.no_description", "repo has no description (GitHub search + SEO signal).")
            if not m.get("topics"):
                res.find("medium", "github.no_topics", "repo has no topics (GitHub search keywords - add your niche terms).")

            tv = c.get(f"/repos/{repo}/traffic/views")
            if tv.status_code == 200:
                j = tv.json()
                res.signal("views_14d", j.get("count"))
                res.signal("uniques_14d", j.get("uniques"))
            else:
                res.signal("traffic", f"unavailable (HTTP {tv.status_code}; needs a push-scoped token)")
        return res
