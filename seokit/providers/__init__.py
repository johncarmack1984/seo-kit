"""Provider registry. Order here is the order the audit runs + reports them."""
from __future__ import annotations

from .ahrefs import AhrefsProvider
from .bing import BingProvider
from .crawl import CrawlProvider
from .dataforseo import DataForSeoProvider
from .geo_probe import GeoProbeProvider
from .github import GithubProvider
from .gsc import GscProvider
from .psi import PsiProvider
from .semrush import SemrushProvider
from .serper import SerperProvider
from .trends import TrendsProvider

_PROVIDERS = [
    CrawlProvider,
    PsiProvider,
    GscProvider,
    GithubProvider,
    BingProvider,
    TrendsProvider,
    DataForSeoProvider,
    SerperProvider,
    GeoProbeProvider,
    AhrefsProvider,
    SemrushProvider,
]
REGISTRY = {p.name: p for p in _PROVIDERS}
