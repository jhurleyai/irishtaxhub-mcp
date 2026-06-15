import asyncio
from unittest.mock import AsyncMock, patch

import httpx

from irishtaxhub_mcp import server


def _patched_client():
    client = AsyncMock()
    client.request = AsyncMock(return_value={"status": "success"})
    client.close = AsyncMock()
    return client


def test_search_tax_treaties_request():
    client = _patched_client()
    with patch.object(
        server, "_get_client_and_loader", AsyncMock(return_value=(client, None, None))
    ):
        asyncio.run(server.search_tax_treaties(query="dividends", country="France", limit=5))
    client.request.assert_awaited_once_with(
        "GET", "/v1/tax-treaties", params={"q": "dividends", "country": "France", "limit": 5}
    )


def test_search_tax_treaties_omits_country_when_none():
    client = _patched_client()
    with patch.object(
        server, "_get_client_and_loader", AsyncMock(return_value=(client, None, None))
    ):
        asyncio.run(server.search_tax_treaties(query="mli", limit=10))
    args, kwargs = client.request.call_args
    assert "country" not in kwargs["params"]


def test_get_tax_treaty_text_normalises_identifier():
    client = _patched_client()
    with patch.object(
        server, "_get_client_and_loader", AsyncMock(return_value=(client, None, None))
    ):
        asyncio.run(server.get_tax_treaty_text(filename="https://x/u/usa-1997.pdf"))
    client.request.assert_awaited_once_with("GET", "/v1/tax-treaties/text/usa-1997")


def test_get_tax_treaty_text_404_friendly():
    client = _patched_client()
    response = httpx.Response(404, request=httpx.Request("GET", "http://x"))
    client.request = AsyncMock(
        side_effect=httpx.HTTPStatusError("404", request=response.request, response=response)
    )
    with patch.object(
        server, "_get_client_and_loader", AsyncMock(return_value=(client, None, None))
    ):
        result = asyncio.run(server.get_tax_treaty_text(filename="missing"))
    assert result["status"] == "error"
    assert "not available" in result["message"]


def test_list_tax_treaty_countries_request():
    client = _patched_client()
    with patch.object(
        server, "_get_client_and_loader", AsyncMock(return_value=(client, None, None))
    ):
        asyncio.run(server.list_tax_treaty_countries())
    client.request.assert_awaited_once_with("GET", "/v1/tax-treaties/countries")
