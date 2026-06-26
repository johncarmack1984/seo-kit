"""Tier 3 (stub) - Semrush: domain/organic research + backlinks + competitor gap."""
from __future__ import annotations

from .base import Provider, ProviderNotEnabled, Tier


class SemrushProvider(Provider):
    name = "semrush"
    tier = Tier.BACKLINKS
    requires_env = ["SEMRUSH_API_KEY"]
    stub_adds = "Domain/organic research + backlinks + competitor keyword gap (Semrush)"
    stub_env = ["SEMRUSH_API_KEY"]
    stub_contract = "GET https://api.semrush.com/?type=domain_organic&key=...&domain=...  (+ /analytics/v1 backlinks)"

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        raise ProviderNotEnabled(self.name, self.stub_env, self.stub_adds, self.stub_contract)
