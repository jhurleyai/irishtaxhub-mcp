"""ASGI middleware for the MCP HTTP app: origin locking + path normalisation.

Applied to BOTH entrypoints (the streaming Function URL app in ``asgi.py`` and
the API Gateway app in ``lambda_handler.py``) so neither is an unprotected way
to reach the MCP tools.
"""

import hmac
import os

_PROTECTED_PREFIX = "/mcp"
_VERIFY_HEADER = b"x-origin-verify"

# The MCP endpoint is an API with no HTML, so it has no favicon — which means the
# connector directory (and tool-call UI), which fetches the logo from the MCP
# domain's favicon, would show a generic icon. Redirect /favicon.ico to the main
# site's favicon so the Irish Tax Hub brand mark is used instead.
_FAVICON_PATH = "/favicon.ico"
_FAVICON_TARGET = b"https://www.irishtaxhub.ie/favicon.ico"


class FaviconRedirect:
    """Redirect ``/favicon.ico`` to the main site favicon (302)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path") == _FAVICON_PATH:
            await send(
                {
                    "type": "http.response.start",
                    "status": 302,
                    "headers": [
                        (b"location", _FAVICON_TARGET),
                        (b"cache-control", b"public, max-age=86400"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": b""})
            return
        await self.app(scope, receive, send)


class StripTrailingSlash:
    """Normalise a trailing slash off the request path before routing.

    FastMCP's Starlette app 307-redirects ``/mcp/`` to ``/mcp``. Behind
    CloudFront -> Lambda Function URL that redirect's absolute URL is built from
    the origin (Function URL) host, leaking it to clients and pushing their
    session off CloudFront (and the WAF / origin lock). Stripping the trailing
    slash here means both ``/mcp`` and ``/mcp/`` are served directly with no
    redirect. ``/`` itself is left untouched.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if len(path) > 1 and path.endswith("/"):
                scope = dict(scope)
                scope["path"] = path.rstrip("/")
                raw_path = scope.get("raw_path")
                if raw_path:
                    scope["raw_path"] = raw_path.rstrip(b"/")
        await self.app(scope, receive, send)


class RequireOriginSecret:
    """Reject ``/mcp`` requests that did not arrive through CloudFront.

    The Lambda Function URL is ``authorization_type = NONE`` (so POST streaming
    works — CloudFront OAC can't sign POST bodies to Lambda URLs). We lock the
    origin with a shared secret instead: CloudFront injects an ``X-Origin-Verify``
    origin custom header on every request, and this middleware rejects any
    ``/mcp`` request whose header doesn't match. Direct hits to the Function URL
    or the API Gateway endpoint lack the header -> 403, leaving CloudFront (and
    its WAF) the only usable client path.

    The secret is an infrastructure secret (it lives in Terraform state +
    CloudFront/Lambda config), not user authentication. It's compared with
    ``hmac.compare_digest`` to avoid timing leaks. The check **fails closed**: if
    no secret is configured, every ``/mcp`` request is rejected (a misconfigured
    deploy denies rather than exposes). Stage and prod always set the secret via
    Terraform; local/dev must set ``ORIGIN_VERIFY_SECRET`` and send the header to
    exercise ``/mcp``. Non-``/mcp`` paths (e.g. the Web Adapter health check on
    ``/``) are never gated.
    """

    def __init__(self, app, secret=None):
        if secret is None:
            secret = os.getenv("ORIGIN_VERIFY_SECRET", "")
        self.app = app
        self._secret = secret.encode() if isinstance(secret, str) else (secret or b"")

    def _is_protected(self, path):
        return path == _PROTECTED_PREFIX or path.startswith(_PROTECTED_PREFIX + "/")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and self._is_protected(scope.get("path", "")):
            # Fail closed: no configured secret => deny.
            if not self._secret:
                await self._forbidden(send)
                return
            provided = b""
            for name, value in scope.get("headers", []):
                if name.lower() == _VERIFY_HEADER:
                    provided = value
                    break
            if not hmac.compare_digest(provided, self._secret):
                await self._forbidden(send)
                return
        await self.app(scope, receive, send)

    async def _forbidden(self, send):
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": b"Forbidden"})
