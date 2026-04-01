"""ASGI entrypoint for uvicorn (Lambda Web Adapter streaming mode)."""

from .server import mcp

app = mcp.http_app(stateless_http=True)
