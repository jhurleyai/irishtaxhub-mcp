from __future__ import annotations

from typing import Any, Dict, Optional

from fastmcp import FastMCP

from .settings import Settings
from .client import IrishTaxHubClient
from .openapi import (
    OpenAPILoader,
    list_endpoints,
    get_request_body_schema,
    validate_body,
    normalize_path,
)


mcp = FastMCP("irishtaxhub-mcp")

"""
Dynamic OpenAPI-driven MCP tools only: list endpoints, fetch schemas, and invoke.
"""


@mcp.tool
async def openapi_list_endpoints(tag: Optional[str] = None) -> Any:
    """
    List available OpenAPI endpoints discovered from the server.

    Optionally filter by tag.
    """
    settings = Settings.load()
    loader = OpenAPILoader(settings.base_url, settings.openapi, settings.timeout)
    spec = await loader.load()
    return list_endpoints(spec, tag=tag)


@mcp.tool
async def openapi_get_request_schema(path: str, method: str = "POST") -> Any:
    """
    Get the JSON Schema for the request body of an endpoint.
    """
    settings = Settings.load()
    loader = OpenAPILoader(settings.base_url, settings.openapi, settings.timeout)
    spec = await loader.load()
    schema = get_request_body_schema(spec, path, method)
    return schema or {}


@mcp.tool
async def openapi_invoke(
    path: str,
    method: str = "POST",
    body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Invoke an OpenAPI endpoint dynamically with optional JSON Schema validation.

    - Validates the request body against the OpenAPI schema when available
    - Calls the API and returns the JSON response
    """
    settings = Settings.load()
    loader = OpenAPILoader(settings.base_url, settings.openapi, settings.timeout)
    spec = await loader.load()
    # Validate against schema if present (using spec path)
    validate_body(spec, path, method, body)

    client = IrishTaxHubClient(settings.base_url, settings.api_key, settings.timeout)
    try:
        effective = normalize_path(spec, path)
        return await client.request(method, effective, json_body=body, params=params)
    finally:
        await client.close()


def run() -> None:
    # Default uses STDIO transport; compatible with MCP clients
    mcp.run()


if __name__ == "__main__":
    run()
