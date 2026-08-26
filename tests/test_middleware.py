import asyncio

from irishtaxhub_mcp.asgi import app
from irishtaxhub_mcp.middleware import (
    FaviconRedirect,
    OpenAIAppsChallenge,
    RequireOriginSecret,
    StripTrailingSlash,
)

# ---- StripTrailingSlash ----


def _run_strip(path, raw_path):
    seen = {}

    async def inner(scope, receive, send):
        seen["path"] = scope.get("path")
        seen["raw_path"] = scope.get("raw_path")

    asyncio.run(
        StripTrailingSlash(inner)({"type": "http", "path": path, "raw_path": raw_path}, None, None)
    )
    return seen


def test_strips_trailing_slash_so_no_redirect_is_triggered():
    seen = _run_strip("/mcp/", b"/mcp/")
    assert seen["path"] == "/mcp"
    assert seen["raw_path"] == b"/mcp"


def test_leaves_non_trailing_slash_path_untouched():
    seen = _run_strip("/mcp", b"/mcp")
    assert seen["path"] == "/mcp"


def test_does_not_collapse_root_path():
    seen = _run_strip("/", b"/")
    assert seen["path"] == "/"


# ---- RequireOriginSecret ----


def _run_secret(mw_secret, headers, path="/mcp"):
    """Drive a scope through RequireOriginSecret; return (reached_inner, status)."""
    state = {"reached": False, "status": None}

    async def inner(scope, receive, send):
        state["reached"] = True

    async def send(message):
        if message["type"] == "http.response.start":
            state["status"] = message["status"]

    mw = RequireOriginSecret(inner, secret=mw_secret)
    scope = {"type": "http", "path": path, "headers": headers}
    asyncio.run(mw(scope, None, send))
    return state


def test_rejects_mcp_request_without_secret_header():
    state = _run_secret("s3cr3t", headers=[])
    assert state["reached"] is False
    assert state["status"] == 403


def test_rejects_mcp_request_with_wrong_secret():
    state = _run_secret("s3cr3t", headers=[(b"x-origin-verify", b"nope")])
    assert state["reached"] is False
    assert state["status"] == 403


def test_allows_mcp_request_with_correct_secret():
    state = _run_secret("s3cr3t", headers=[(b"x-origin-verify", b"s3cr3t")])
    assert state["reached"] is True


def test_header_match_is_case_insensitive_on_name():
    state = _run_secret("s3cr3t", headers=[(b"X-Origin-Verify", b"s3cr3t")])
    assert state["reached"] is True


def test_non_mcp_paths_are_not_gated():
    state = _run_secret("s3cr3t", headers=[], path="/")
    assert state["reached"] is True


def test_fail_closed_when_no_secret_configured():
    # A misconfigured deploy (no secret) must deny /mcp, not expose it.
    state = _run_secret("", headers=[(b"x-origin-verify", b"anything")])
    assert state["reached"] is False
    assert state["status"] == 403


def test_fail_closed_does_not_gate_non_mcp_paths():
    # Health check on / still passes even with no secret configured.
    state = _run_secret("", headers=[], path="/")
    assert state["reached"] is True


def test_does_not_gate_lookalike_prefix():
    state = _run_secret("s3cr3t", headers=[], path="/mcpother")
    assert state["reached"] is True


def test_app_is_wrapped_challenge_then_favicon_then_slash_then_secret():
    assert isinstance(app, OpenAIAppsChallenge)
    assert isinstance(app.app, FaviconRedirect)
    assert isinstance(app.app.app, StripTrailingSlash)
    assert isinstance(app.app.app.app, RequireOriginSecret)


# ---- OpenAIAppsChallenge ----


def _run_openai_challenge(path):
    state = {"reached": False, "status": None, "content_type": None, "body": None}

    async def inner(scope, receive, send):
        state["reached"] = True

    async def send(message):
        if message["type"] == "http.response.start":
            state["status"] = message["status"]
            state["content_type"] = dict(message["headers"]).get(b"content-type")
        elif message["type"] == "http.response.body":
            state["body"] = message["body"]

    asyncio.run(OpenAIAppsChallenge(inner)({"type": "http", "path": path}, None, send))
    return state


def test_openai_challenge_returns_exact_plain_text_token():
    state = _run_openai_challenge("/.well-known/openai-apps-challenge")
    assert state["reached"] is False
    assert state["status"] == 200
    assert state["content_type"] == b"text/plain; charset=utf-8"
    assert state["body"] == b"pNWAYlmjufGPF-GYUTSFqqZh0WSR5NSz5nEwqu0miU8"


def test_openai_challenge_middleware_passes_other_paths_through():
    state = _run_openai_challenge("/mcp")
    assert state["reached"] is True
    assert state["status"] is None


# ---- FaviconRedirect ----


def _run_favicon(path):
    state = {"reached": False, "status": None, "location": None}

    async def inner(scope, receive, send):
        state["reached"] = True

    async def send(message):
        if message["type"] == "http.response.start":
            state["status"] = message["status"]
            for name, value in message["headers"]:
                if name == b"location":
                    state["location"] = value

    asyncio.run(FaviconRedirect(inner)({"type": "http", "path": path}, None, send))
    return state


def test_favicon_redirects_to_main_site():
    state = _run_favicon("/favicon.ico")
    assert state["reached"] is False
    assert state["status"] == 302
    assert state["location"] == b"https://www.irishtaxhub.ie/favicon.ico"


def test_favicon_middleware_passes_other_paths_through():
    state = _run_favicon("/mcp")
    assert state["reached"] is True
    assert state["status"] is None
