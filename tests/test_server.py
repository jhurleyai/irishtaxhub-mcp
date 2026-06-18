import asyncio

import pytest

from irishtaxhub_mcp.server import _normalise_document_identifier, mcp

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
    "search_tax_treaties",
    "get_tax_treaty_text",
    "list_tax_treaty_countries",
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


def _get_tools():
    return asyncio.run(mcp.list_tools())


def test_every_tool_has_a_title():
    """Directory requirement: every tool must expose a human-readable title."""
    missing = [t.name for t in _get_tools() if not t.title]
    assert not missing, f"Tools missing a title: {missing}"


def test_every_tool_declares_read_only_hint():
    """Directory requirement: every tool must declare readOnlyHint/destructiveHint.

    All tools in this server are read-only, so each must set readOnlyHint=True.
    """
    bad = [
        t.name
        for t in _get_tools()
        if t.annotations is None or t.annotations.readOnlyHint is not True
    ]
    assert not bad, f"Tools not declaring readOnlyHint=True: {bad}"


def test_every_tool_declares_open_world_hint():
    """Every tool reaches the external Irish Tax Hub API, so each sets openWorldHint=True."""
    bad = [
        t.name
        for t in _get_tools()
        if t.annotations is None or t.annotations.openWorldHint is not True
    ]
    assert not bad, f"Tools not declaring openWorldHint=True: {bad}"


def test_mcp_http_app():
    """Verify FastMCP produces an ASGI app for Lambda."""
    app = mcp.http_app()
    assert callable(app)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("19-07-03", "19-07-03"),
        ("19-07-03.pdf", "19-07-03"),
        ("19-07-03.PDF", "19-07-03"),
        (
            "https://www.revenue.ie/en/tax-professionals/tdm/"
            "income-tax-capital-gains-tax-corporation-tax/part-19/19-07-03.pdf",
            "19-07-03",
        ),
        ("/revenue/documents/text/19-07-03", "19-07-03"),
        ("  19-07-03  ", "19-07-03"),
        ("19-07-03/", "19-07-03"),
    ],
)
def test_normalise_document_identifier(value, expected):
    assert _normalise_document_identifier(value) == expected
