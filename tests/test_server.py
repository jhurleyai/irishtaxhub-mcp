from irishtaxhub_mcp.server import mcp


def test_mcp_server_has_registered_tools():
    """Verify the MCP server registers the expected tool functions."""
    assert mcp._tool_manager._tools, "No tools registered"
    tool_names = list(mcp._tool_manager._tools.keys())
    assert "openapi_list_endpoints" in tool_names
    assert "openapi_get_request_schema" in tool_names
    assert "openapi_invoke" in tool_names


def test_mcp_http_app():
    """Verify FastMCP produces an ASGI app for Lambda."""
    app = mcp.http_app()
    assert callable(app)
