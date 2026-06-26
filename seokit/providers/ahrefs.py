"""Tier 3 (stub) - Ahrefs: backlinks + competitor keyword gap."""
from __future__ import annotations

from .base import Provider, ProviderNotEnabled, Tier


class AhrefsProvider(Provider):
    name = "ahrefs"
    tier = Tier.BACKLINKS
    requires_env = ["AHREFS_API_KEY"]
    stub_adds = "Backlink profile + referring domains + organic keyword/competitor gap"
    stub_env = ["AHREFS_API_KEY"]
    stub_contract = "GET https://api.ahrefs.com/v3/site-explorer/{backlinks,refdomains,organic-keywords} (Bearer token)"

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        raise ProviderNotEnabled(self.name, self.stub_env, self.stub_adds, self.stub_contract)
