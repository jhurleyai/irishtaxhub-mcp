"""ASGI entrypoint for uvicorn (Lambda Web Adapter streaming mode)."""

from .middleware import FaviconRedirect, RequireOriginSecret, StripTrailingSlash
from .server import mcp

# FaviconRedirect is outermost (short-circuits /favicon.ico). StripTrailingSlash
# normalises the path before the origin check and FastMCP's router (which would
# otherwise 307-redirect /mcp/).
app = FaviconRedirect(StripTrailingSlash(RequireOriginSecret(mcp.http_app(stateless_http=True))))
