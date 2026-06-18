"""ASGI entrypoint for uvicorn (Lambda Web Adapter streaming mode)."""

from .middleware import RequireOriginSecret, StripTrailingSlash
from .server import mcp

# StripTrailingSlash is outermost so the path is normalised before the origin
# check and before FastMCP's router (which would otherwise 307-redirect /mcp/).
app = StripTrailingSlash(RequireOriginSecret(mcp.http_app(stateless_http=True)))
