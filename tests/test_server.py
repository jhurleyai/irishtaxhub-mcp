import asyncio

from irishtaxhub_mcp.server import mcp

EXPECTED_TOOLS = [
    "calculate_tax",
    "get_calculator_schema",
    "list_calculators",
    "get_tax_constants",
    "get_key_dates",
    "search_revenue_documents",
    "get_revenue_document_text",
    "list_revenue_document_categories",
    "get_revenue_ebrief_changelog",
    "generate_net_income_summary",
    "get_calculator_stats",
]


def _get_tool_names():
    return [t.name for t in asyncio.run(mcp.list_tools())]


def test_mcp_server_has_registered_tools():
    """Verify the MCP server registers the expected tool functions."""
    tool_names = _get_tool_names()
    assert tool_names, "No tools registered"
    for expected in EXPECTED_TOOLS:
        assert expected in tool_names, f"Missing tool: {expected}"


def test_mcp_server_tool_count():
    """Verify no unexpected tools are registered."""
    tool_names = _get_tool_names()
    assert len(tool_names) == len(
        EXPECTED_TOOLS
    ), f"Expected {len(EXPECTED_TOOLS)} tools, got {len(tool_names)}: {tool_names}"


def test_mcp_http_app():
    """Verify FastMCP produces an ASGI app for Lambda."""
    app = mcp.http_app()
    assert callable(app)
