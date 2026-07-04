"""The redaction choke point: credential-shaped substrings never reach output."""
from seokit.redact import redact_secrets


def test_query_param_keys_scrubbed():
    url = "https://api.example/v1?foo=1&key=AIzaSyFAKEFAKE&api_key=xyz9&apikey=abc8&access_token=tok123"
    out = redact_secrets(f"HTTPStatusError: 403 for url '{url}'")
    for leak in ("AIzaSyFAKEFAKE", "xyz9", "abc8", "tok123"):
        assert leak not in out
    assert "key=REDACTED" in out
    assert "foo=1" in out  # non-credential params survive


def test_bearer_token_scrubbed():
    assert redact_secrets("headers: Bearer abc.DEF-ghi_2=") == "headers: Bearer REDACTED"


def test_bare_key_shapes_scrubbed():
    assert redact_secrets("AIza" + "A" * 35) == "REDACTED"
    assert redact_secrets("saw sk-" + "a1" * 12 + " in logs") == "saw REDACTED in logs"


def test_plain_text_untouched():
    s = "title is 42 chars; monkey=business; ?keyed=off; risky business"
    assert redact_secrets(s) == s
