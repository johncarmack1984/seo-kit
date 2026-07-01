"""Scrub credential-shaped substrings before they reach console or report output.

Provider errors often embed the full request URL (httpx's HTTPStatusError does,
key= query param and all), and per-repo reports are designed to be committed —
so redact at the choke points: error capture and the rendered md/json.
"""
from __future__ import annotations

import re

# ?key=... / &access_token=... style query params, case-insensitive.
_PARAM = re.compile(
    r"(?i)([?&](?:key|api_?key|token|access_token|auth|signature|sig|client_secret|secret|password)=)[^&\s\"'<>]+"
)
# Bearer tokens in stringified headers/requests.
_BEARER = re.compile(r"(?i)\b(bearer\s+)[a-z0-9._~+/-]+=*")
# Bare well-known key shapes (Google AIza…, OpenAI sk-…), wherever they appear.
_BARE = re.compile(r"\b(AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9_-]{20,})\b")


def redact_secrets(text: str) -> str:
    text = _PARAM.sub(r"\1REDACTED", text)
    text = _BEARER.sub(r"\1REDACTED", text)
    return _BARE.sub("REDACTED", text)
