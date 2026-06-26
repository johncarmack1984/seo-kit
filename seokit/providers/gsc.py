"""Tier 0 - Google Search Console (real queries/clicks/impressions/position).

OAuth Desktop flow. First run `seo-kit auth gsc` once to consent; the token is
cached in secrets/gsc_token.json and refreshed automatically thereafter.
Needs the 'google' extra and GSC_OAUTH_CLIENT_JSON.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from ..config import ROOT
from .base import Provider, ProviderResult, Tier

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
TOKEN_PATH = ROOT / "secrets" / "gsc_token.json"


def authorize(env: dict) -> Path:
    """One-time consent. Opens a browser; caches the refresh token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    client = env.get("GSC_OAUTH_CLIENT_JSON")
    if not client or not Path(client).exists():
        raise FileNotFoundError(f"GSC_OAUTH_CLIENT_JSON not found: {client!r}")
    flow = InstalledAppFlow.from_client_secrets_file(client, SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    return TOKEN_PATH


def _load_creds():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not TOKEN_PATH.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
    return creds


class GscProvider(Provider):
    name = "gsc"
    tier = Tier.FREE
    requires_env = ["GSC_OAUTH_CLIENT_JSON"]

    def fetch(self, surface) -> ProviderResult:  # noqa: ANN001
        res = ProviderResult(provider=self.name, tier=self.tier)
        if not surface.gsc_property:
            res.status = "skipped"
            res.find("low", "gsc.no_property", "surface has no gsc_property set.")
            return res
        try:
            creds = _load_creds()
        except ImportError:
            res.status = "skipped"
            res.find("low", "gsc.no_dep", "install the 'google' extra, then run `seo-kit auth gsc`.")
            return res
        if not creds:
            res.status = "skipped"
            res.find("medium", "gsc.no_token", "no cached token - run `seo-kit auth gsc` once.")
            return res

        from googleapiclient.discovery import build

        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=28)
        body = {"startDate": str(start), "endDate": str(end), "dimensions": ["query"], "rowLimit": 25}
        resp = service.searchanalytics().query(siteUrl=surface.gsc_property, body=body).execute()
        rows = resp.get("rows", [])

        res.signal("query_count_28d", len(rows))
        res.signal("total_clicks_28d", sum(r.get("clicks", 0) for r in rows))
        res.signal("total_impressions_28d", sum(r.get("impressions", 0) for r in rows))
        res.signal("top_queries", [f"{r['keys'][0]} ({int(r['clicks'])}c/{int(r['impressions'])}i p{r['position']:.0f})" for r in rows[:10]])
        if not rows:
            res.find("low", "gsc.no_data", "no Search Console query data yet (new/low-traffic property; data lags ~2 days).")
        return res
