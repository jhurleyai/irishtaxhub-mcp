"""ASGI entrypoint for uvicorn (Lambda Web Adapter streaming mode)."""

from .middleware import (
    FaviconRedirect,
    OpenAIAppsChallenge,
    RequireOriginSecret,
    StripTrailingSlash,
)
from .server import mcp

# The two public metadata routes short-circuit before path normalisation and the
# origin check. StripTrailingSlash normalises /mcp/ before FastMCP's router.
app = OpenAIAppsChallenge(
    FaviconRedirect(StripTrailingSlash(RequireOriginSecret(mcp.http_app(stateless_http=True))))
)
