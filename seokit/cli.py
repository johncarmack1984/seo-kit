"""seo-kit command line: audit a surface, list providers, run GSC auth."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from .audit import run_audit
from .config import ROOT, load_config, load_env, load_surfaces
from .providers import REGISTRY
from .providers.base import TIER_LABEL
from .report import render_json, render_markdown

console = Console()


def _cmd_audit(args: argparse.Namespace) -> int:
    config, env, surfaces = load_config(), load_env(), load_surfaces()
    surface = surfaces.get(args.surface)
    if not surface:
        console.print(f"[red]unknown surface '{args.surface}'.[/] known: {', '.join(surfaces) or '(none)'}")
        return 2

    only = args.only.split(",") if args.only else None
    console.print(f"[bold]auditing[/] {surface.id} ...")
    report = run_audit(surface, config, env, only=only)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    md = render_markdown(report, config, generated=stamp)
    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{surface.id}-{stamp}.md").write_text(md)
    (out_dir / f"{surface.id}-{stamp}.json").write_text(json.dumps(render_json(report), indent=2, default=str))

    console.print(Markdown(md))
    console.print(f"\n[dim]saved reports/{surface.id}-{stamp}.md (+ .json)[/]")
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
    parser = argparse.ArgumentParser(prog="seo-kit", description="Real-data SEO + GEO audit toolkit.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit", help="audit a surface from surfaces.toml")
    p_audit.add_argument("surface", help="surface id, e.g. example.com")
    p_audit.add_argument("--only", help="comma-separated provider names to run (e.g. crawl)")
    p_audit.set_defaults(func=_cmd_audit)

    sub.add_parser("providers", help="list providers, tiers, and env readiness").set_defaults(func=_cmd_providers)

    p_auth = sub.add_parser("auth", help="one-time auth flows")
    auth_sub = p_auth.add_subparsers(dest="auth_target", required=True)
    auth_sub.add_parser("gsc", help="OAuth consent for Search Console").set_defaults(func=_cmd_auth_gsc)

    args = parser.parse_args(argv)
    return args.func(args)
