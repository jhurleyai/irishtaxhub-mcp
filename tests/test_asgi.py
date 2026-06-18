import asyncio

from irishtaxhub_mcp.asgi import StripTrailingSlash, app


def _run_through(path, raw_path):
    """Send a minimal HTTP scope through the middleware, capture the inner path."""
    seen = {}

    async def inner(scope, receive, send):
        seen["path"] = scope.get("path")
        seen["raw_path"] = scope.get("raw_path")

    mw = StripTrailingSlash(inner)
    scope = {"type": "http", "path": path, "raw_path": raw_path}
    asyncio.run(mw(scope, None, None))
    return seen


def test_strips_trailing_slash_so_no_redirect_is_triggered():
    seen = _run_through("/mcp/", b"/mcp/")
    assert seen["path"] == "/mcp"
    assert seen["raw_path"] == b"/mcp"


def test_leaves_non_trailing_slash_path_untouched():
    seen = _run_through("/mcp", b"/mcp")
    assert seen["path"] == "/mcp"
    assert seen["raw_path"] == b"/mcp"


def test_does_not_collapse_root_path():
    seen = _run_through("/", b"/")
    assert seen["path"] == "/"


def test_non_http_scope_passes_through_untouched():
    seen = {}

    async def inner(scope, receive, send):
        seen["type"] = scope["type"]

    mw = StripTrailingSlash(inner)
    asyncio.run(mw({"type": "lifespan"}, None, None))
    assert seen["type"] == "lifespan"


def test_app_is_wrapped_with_strip_trailing_slash():
    assert isinstance(app, StripTrailingSlash)
