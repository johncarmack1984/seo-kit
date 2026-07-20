"""seo-kit command line: set up a repo, audit a site by URL or surface, list providers, run GSC auth."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from .audit import run_audit
from .config import LOCAL_CONFIG, ROOT, load_config, load_env, load_local_config, load_surfaces, surface_from_target
from .providers import REGISTRY
from .providers.base import TIER_LABEL
from .redact import redact_secrets
from .report import render_json, render_markdown
from .setup import git_root, infer_github_repo, infer_url, scaffold_toml

console = Console()


def _cmd_audit(args: argparse.Namespace) -> int:
    config, env = load_config(), load_env()
    local, surfaces = load_local_config(), load_surfaces()
    local_surfaces = local.surfaces if local else {}
    # Resolve the target: a per-repo seo-kit.toml id (nearest, wins), a global
    # surfaces.toml id, OR a raw URL/domain (portable mode: URL-only providers
    # run, config-needing ones skip).
    surface = local_surfaces.get(args.target) or surfaces.get(args.target) or surface_from_target(args.target)
    if not surface:
        known = ", ".join([*local_surfaces, *(k for k in surfaces if k not in local_surfaces)]) or "(none)"
        console.print(
            f"[red]'{args.target}' is not a configured surface id or a URL.[/] "
            f"pass a URL (e.g. https://example.com), run `seo-kit setup` in the target repo, or use one of: {known}"
        )
        return 2

    only = args.only.split(",") if args.only else None
    from_local = args.target in local_surfaces
    if from_local:
        console.print(f"[dim]surface from {local.path}[/]")
    console.print(f"[bold]auditing[/] {surface.id} ...")
    report = run_audit(surface, config, env, only=only)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Belt and suspenders with the capture-point redaction in run_audit: both
    # written reports (and the console render of md below) pass through the scrub.
    md = redact_secrets(render_markdown(report, config, generated=stamp))
    out_dir = local.reports_dir if from_local else ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{surface.id}-{stamp}.md"
    md_path.write_text(md)
    (out_dir / f"{surface.id}-{stamp}.json").write_text(
        redact_secrets(json.dumps(render_json(report), indent=2, default=str))
    )

    console.print(Markdown(md))
    console.print(f"\n[dim]saved {md_path} (+ .json)[/]")
    return 0


def _cmd_setup(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    root = git_root(cwd) or cwd
    dest = root / LOCAL_CONFIG
    if dest.exists() and not args.force:
        console.print(f"[yellow]{dest} already exists.[/] edit it directly, or rerun with --force to regenerate.")
        return 0
    url = args.url or infer_url(root)
    if not url:
        console.print(
            "[red]could not infer the site url[/] (no CNAME or package.json homepage found). "
            "pass it: seo-kit setup https://example.com"
        )
        return 2
    synth = surface_from_target(url)
    if not synth:
        console.print(f"[red]'{url}' does not look like a URL or domain.[/]")
        return 2
    dest.write_text(scaffold_toml(synth.id, synth.url, infer_github_repo(root)))
    console.print(f"[green]wrote {dest}[/] (surface '{synth.id}')")
    console.print(
        "next:\n"
        f"  1. fill positioning, seed_keywords, and the GEO block in {LOCAL_CONFIG} (from the repo's README/docs)\n"
        f"  2. seo-kit audit {synth.id}   # reports land in this repo's seo-reports/"
    )
    return 0


def _cmd_trend(args: argparse.Namespace) -> int:
    from .trend import METRICS, load_series, public_slice, render_svg, series_json

    local, surfaces = load_local_config(), load_surfaces()
    local_surfaces = local.surfaces if local else {}
    surface = local_surfaces.get(args.target) or surfaces.get(args.target) or surface_from_target(args.target)
    if not surface:
        console.print(f"[red]'{args.target}' is not a configured surface id or a URL.[/]")
        return 2
    from_local = args.target in local_surfaces
    if args.reports_dir:
        reports_dir = Path(args.reports_dir)
    else:
        reports_dir = local.reports_dir if from_local else ROOT / "reports"
    snaps = load_series(reports_dir, surface.id)
    if not snaps:
        console.print(f"[yellow]no reports for '{surface.id}' in {reports_dir}[/] - run `seo-kit audit {surface.id}` first.")
        return 1
    # Applied before anything renders, so the table, the SVG and the JSON agree.
    if args.public:
        snaps = public_slice(snaps)

    # The SVG plots everything; the table shows the newest handful.
    shown = snaps[-8:]
    title = f"audit trend - {surface.id} ({len(snaps)} audits" + (f", last {len(shown)} shown" if len(shown) < len(snaps) else "") + ")"
    t = Table(title=title)
    t.add_column("metric")
    for s in shown:
        t.add_column(s.stamp.strftime("%m-%d %H:%M"), justify="right")
    for key, label in METRICS:
        if not any(key in s.metrics for s in snaps):
            continue
        vals = [("-" if key not in s.metrics else f"{s.metrics[key]:g}") for s in shown]
        t.add_row(label, *vals)
    console.print(t)

    out = Path(args.out) if args.out else reports_dir / f"trend-{surface.id}.svg"
    out.write_text(render_svg(snaps, surface.id))
    console.print(f"[dim]wrote {out}[/]")

    if args.emit_json:
        emit = Path(args.emit_json)
        emit.write_text(json.dumps(series_json(snaps, surface.id), indent=2) + "\n")
        console.print(f"[dim]wrote {emit}[/]")
    return 0


def _cmd_providers(args: argparse.Namespace) -> int:
    config, env = load_config(), load_env()
    enabled = config.get("providers", {})
    t = Table(title="seo-kit providers")
    for col in ("provider", "tier", "enabled", "env ready", "role"):
        t.add_column(col)
    for name, cls in REGISTRY.items():
        miss = [k for k in cls.requires_env if not env.get(k)]
        env_ready = "n/a" if not cls.requires_env else ("yes" if not miss else f"missing {','.join(miss)}")
        role = "impl" if cls.stub_adds is None else "stub"
        t.add_row(name, TIER_LABEL.get(cls.tier, ""), "yes" if enabled.get(name) else "no", env_ready, role)
    console.print(t)
    return 0


def _cmd_auth_gsc(args: argparse.Namespace) -> int:
    from .providers.gsc import authorize  # lazy: needs the 'google' extra
    env = load_env()
    path = authorize(env)
    console.print(f"[green]Search Console authorized.[/] token cached at {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seo-kit", description="Real-data SEO + GEO audit toolkit for any site.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit", help="audit a site by URL, or a configured surface id")
    p_audit.add_argument("target", help="a URL (https://example.com) or a surface id from seo-kit.toml / surfaces.toml")
    p_audit.add_argument("--only", help="comma-separated provider names to run (e.g. crawl,psi)")
    p_audit.set_defaults(func=_cmd_audit)

    p_setup = sub.add_parser("setup", help=f"scaffold {LOCAL_CONFIG} in the current repo (per-repo setup)")
    p_setup.add_argument("url", nargs="?", help="site url; inferred from CNAME / package.json homepage when omitted")
    p_setup.add_argument("--force", action="store_true", help=f"overwrite an existing {LOCAL_CONFIG}")
    p_setup.set_defaults(func=_cmd_setup)

    p_trend = sub.add_parser("trend", help="metric timeseries across a surface's report history (table + SVG)")
    p_trend.add_argument("target", help="a surface id with committed reports (or a URL audited before)")
    p_trend.add_argument("--out", help="SVG output path (default: reports_dir/trend-<id>.svg)")
    p_trend.add_argument("--reports-dir", help="read report history from this directory instead of the resolved one (CI: a synced S3 prefix)")
    p_trend.add_argument("--emit-json", help="also write the series as JSON (the optimizer's history input)")
    p_trend.add_argument("--public", action="store_true", help="omit Search Console metrics — required for artifacts published to the public audits/ slice")
    p_trend.set_defaults(func=_cmd_trend)

    sub.add_parser("providers", help="list providers, tiers, and env readiness").set_defaults(func=_cmd_providers)

    p_auth = sub.add_parser("auth", help="one-time auth flows")
    auth_sub = p_auth.add_subparsers(dest="auth_target", required=True)
    auth_sub.add_parser("gsc", help="OAuth consent for Search Console").set_defaults(func=_cmd_auth_gsc)

    args = parser.parse_args(argv)
    return args.func(args)
