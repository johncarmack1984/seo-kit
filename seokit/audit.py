"""Orchestrator: run the enabled providers for a surface, collect results."""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Surface
from .providers import REGISTRY
from .providers.base import ProviderNotEnabled, ProviderResult


@dataclass
class AuditReport:
    surface: Surface
    results: list[ProviderResult] = field(default_factory=list)


def run_audit(surface: Surface, config: dict, env: dict, only: list[str] | None = None) -> AuditReport:
    enabled = config.get("providers", {})
    report = AuditReport(surface=surface)
    for name, cls in REGISTRY.items():
        if only and name not in only:
            continue
        if not enabled.get(name, False):
            continue
        prov = cls(config, env)
        try:
            res = prov.fetch(surface)
        except ProviderNotEnabled as e:
            res = ProviderResult(
                provider=name, tier=cls.tier, status="stubbed",
                stub_adds=e.adds, stub_env=e.env_keys, stub_contract=e.contract,
            )
        except Exception as e:  # noqa: BLE001 - a provider failure must not sink the audit
            res = ProviderResult(provider=name, tier=cls.tier, status="error",
                                 error=f"{type(e).__name__}: {e}")
        report.results.append(res)
    return report
