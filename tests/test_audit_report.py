"""The orchestrator + renderer: enablement, error isolation with redaction, ranking."""
import seokit.audit as audit_mod
from seokit.audit import run_audit
from seokit.config import Surface
from seokit.providers.base import Provider, ProviderNotEnabled, ProviderResult, Tier
from seokit.report import render_markdown


class BoomProvider(Provider):
    name = "boom"
    tier = Tier.FREE

    def fetch(self, surface):
        raise RuntimeError("403 for url 'https://api.test/?key=SUPERSECRET&x=1'")


class FineProvider(Provider):
    name = "fine"
    tier = Tier.FREE

    def fetch(self, surface):
        res = ProviderResult(provider=self.name, tier=self.tier)
        res.find("low", "fine.low", "minor thing")
        res.find("high", "fine.high", "major thing")
        res.signal("k", "v")
        return res


class StubbyProvider(Provider):
    name = "stubby"
    tier = Tier.BACKLINKS
    stub_adds = "X-ray vision"
    stub_env = ["XRAY_KEY"]
    stub_contract = "GET /xray"

    def fetch(self, surface):
        raise ProviderNotEnabled(self.name, self.stub_env, self.stub_adds, self.stub_contract)


SURFACE = Surface(id="x.com", url="https://x.com/")
# Enable the real Tier-3 stubs too so the "Available if promoted" section stays empty.
ENABLED = {"providers": {"boom": True, "fine": True, "stubby": True, "ahrefs": True, "semrush": True}}


def _patch_registry(monkeypatch, *classes):
    monkeypatch.setattr(audit_mod, "REGISTRY", {c.name: c for c in classes})


def test_provider_failure_is_isolated_and_redacted(monkeypatch):
    _patch_registry(monkeypatch, BoomProvider, FineProvider)
    report = run_audit(SURFACE, ENABLED, env={})
    boom, fine = report.results
    assert boom.status == "error"
    assert "SUPERSECRET" not in boom.error
    assert "key=REDACTED" in boom.error
    assert fine.status == "ok"  # one provider blowing up must not sink the audit


def test_disabled_and_only_filters(monkeypatch):
    _patch_registry(monkeypatch, BoomProvider, FineProvider)
    assert run_audit(SURFACE, {"providers": {"boom": False, "fine": False}}, env={}).results == []
    only_fine = run_audit(SURFACE, ENABLED, env={}, only=["fine"])
    assert [r.provider for r in only_fine.results] == ["fine"]


def test_surface_provider_allowlist(monkeypatch):
    _patch_registry(monkeypatch, BoomProvider, FineProvider)
    surf = Surface(id="x.com", url="https://x.com/", providers=["fine"])
    assert [r.provider for r in run_audit(surf, ENABLED, env={}).results] == ["fine"]
    # outside the allowlist, --only cannot force a provider in
    assert run_audit(surf, ENABLED, env={}, only=["boom"]).results == []


def test_markdown_ranks_findings_and_labels_stubs(monkeypatch):
    _patch_registry(monkeypatch, FineProvider, StubbyProvider)
    report = run_audit(SURFACE, ENABLED, env={})
    md = render_markdown(report, ENABLED, generated="20260704T000000Z")
    assert md.index("fine.high") < md.index("fine.low")  # severity order, not insertion order
    assert "would add: **X-ray vision**" in md
    assert "`XRAY_KEY`" in md
