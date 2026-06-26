"""Render an AuditReport to markdown + JSON, labeling stubbed tiers honestly."""
from __future__ import annotations

from dataclasses import asdict

from .audit import AuditReport
from .providers import REGISTRY
from .providers.base import TIER_LABEL, Tier

SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "good": 3}
SEV_MARK = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]", "good": "[OK]"}


def render_json(report: AuditReport) -> dict:
    return {
        "surface": asdict(report.surface),
        "results": [asdict(r) for r in report.results],
    }


def render_markdown(report: AuditReport, config: dict, generated: str) -> str:
    s = report.surface
    out: list[str] = []
    out.append(f"# SEO/GEO audit - {s.id}")
    out.append("")
    out.append(f"`{s.url}` | generated {generated} | positioning: {s.positioning or 'n/a'}")
    out.append("")

    # --- findings, ranked by severity across all providers ---
    findings = [(r.provider, f) for r in report.results for f in r.findings]
    findings.sort(key=lambda pf: SEV_ORDER.get(pf[1].severity, 9))
    actionable = [pf for pf in findings if pf[1].severity != "good"]
    out.append("## Findings (ranked)")
    out.append("")
    if actionable:
        for prov, f in actionable:
            out.append(f"- {SEV_MARK.get(f.severity, '[?]')} `{prov}:{f.code}` - {f.message}")
    else:
        out.append("- No issues flagged by the enabled providers.")
    out.append("")

    # --- per-provider signals ---
    out.append("## Signals by provider")
    out.append("")
    for r in report.results:
        head = f"### {r.provider} - {TIER_LABEL.get(r.tier, r.tier.name)} - {r.status}"
        out.append(head)
        if r.status == "error":
            out.append(f"- error: `{r.error}`")
        elif r.status == "stubbed":
            out.append(f"- stubbed - would add: **{r.stub_adds}**")
            if r.stub_env:
                out.append(f"- needs env: {', '.join(f'`{k}`' for k in r.stub_env)}")
            if r.stub_contract:
                out.append(f"- contract: `{r.stub_contract}`")
        else:
            for sig in r.signals:
                val = sig.value
                if isinstance(val, list):
                    val = ", ".join(map(str, val)) if val else "(none)"
                note = f"  _{sig.note}_" if sig.note else ""
                out.append(f"- **{sig.key}**: {val}{note}")
        out.append("")

    # --- what promoting a paid tier would add (stubs not even run) ---
    enabled = config.get("providers", {})
    promotable = [
        cls for name, cls in REGISTRY.items()
        if cls.tier != Tier.FREE and not enabled.get(name, False) and cls.stub_adds
    ]
    if promotable:
        out.append("## Available if promoted (paid tiers, currently stubbed)")
        out.append("")
        for cls in promotable:
            envs = ", ".join(f"`{k}`" for k in cls.stub_env) or "n/a"
            out.append(f"- **{cls.name}** ({TIER_LABEL.get(cls.tier)}): {cls.stub_adds} - needs {envs}")
        out.append("")

    return "\n".join(out)
