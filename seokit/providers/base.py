"""Provider framework: a uniform interface over every data source.

Tier 0 providers are implemented. Tier 1-3 providers are stubs that raise
ProviderNotEnabled carrying a promotion contract (what enabling adds, which env
keys it needs, and the exact API call to implement) so the report can surface
them honestly instead of silently doing nothing.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Tier(IntEnum):
    FREE = 0       # free, no-regret
    SERP = 1       # paid, cheap: SERP positions + keyword volume
    GEO = 2        # paid, usage: LLM citation probes
    BACKLINKS = 3  # paid sub: backlinks + competitor gap


TIER_LABEL = {
    Tier.FREE: "Tier 0 (free)",
    Tier.SERP: "Tier 1 (SERP/volume)",
    Tier.GEO: "Tier 2 (GEO probes)",
    Tier.BACKLINKS: "Tier 3 (backlinks)",
}


class ProviderNotEnabled(Exception):
    """Raised by a stubbed/disabled provider. Carries the promotion contract."""

    def __init__(self, name: str, env_keys: list[str], adds: str, contract: str):
        self.name = name
        self.env_keys = env_keys
        self.adds = adds
        self.contract = contract
        super().__init__(f"{name} not enabled (stub) - would add: {adds}")


@dataclass
class Signal:
    key: str
    value: Any
    note: str = ""


@dataclass
class Finding:
    severity: str  # high | medium | low | good
    code: str
    message: str


@dataclass
class ProviderResult:
    provider: str
    tier: Tier
    status: str = "ok"  # ok | stubbed | error | skipped
    signals: list[Signal] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    error: str | None = None
    # populated when status == "stubbed"
    stub_adds: str | None = None
    stub_env: list[str] = field(default_factory=list)
    stub_contract: str | None = None

    def signal(self, key: str, value: Any, note: str = "") -> None:
        self.signals.append(Signal(key, value, note))

    def find(self, severity: str, code: str, message: str) -> None:
        self.findings.append(Finding(severity, code, message))


class Provider(ABC):
    name: str = "base"
    tier: Tier = Tier.FREE
    requires_env: list[str] = []

    # Stub metadata (paid tiers fill these; the report reads them off the class).
    stub_adds: str | None = None
    stub_env: list[str] = []
    stub_contract: str | None = None

    def __init__(self, config: dict, env: dict):
        self.config = config
        self.env = env

    def missing_env(self) -> list[str]:
        return [k for k in self.requires_env if not self.env.get(k)]

    @abstractmethod
    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        ...
