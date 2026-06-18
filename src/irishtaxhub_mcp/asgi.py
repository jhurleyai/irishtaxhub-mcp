"""ASGI entrypoint for uvicorn (Lambda Web Adapter streaming mode)."""

from .server import mcp


class StripTrailingSlash:
    """Normalise a trailing slash off the request path before routing.

    FastMCP's Starlette app 307-redirects ``/mcp/`` to ``/mcp``. Behind
    CloudFront -> Lambda Function URL, that redirect's absolute URL is built
    from the *origin* (Function URL) host, so it leaks the raw origin hostname
    to clients and pushes their session off CloudFront — and therefore off the
    WAF and (with origin locking) onto a URL that returns 403.

    Stripping the trailing slash here means both ``/mcp`` and ``/mcp/`` are
    served directly with no redirect, keeping every request on the CloudFront
    edge. ``/`` itself is left untouched.
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


app = StripTrailingSlash(mcp.http_app(stateless_http=True))
