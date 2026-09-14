import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx

from irishtaxhub_mcp import attribution, server

STATEMENT = (
    "Information provided courtesy of the Revenue Commissioners under a "
    "Creative Commons Attribution 4.0 International (CC BY 4.0) licence"
)
LICENCE_URL = (
    "https://www.revenue.ie/en/corporate/using-revenue/"
    "reuse-of-public-sector-information/public-sector-information-licence.pdf"
)
TDM_INDEX = "https://www.revenue.ie/en/tax-professionals/tdm/index.aspx"
TREATY_INDEX = (
    "https://www.revenue.ie/en/tax-professionals/tax-agreements/"
    "double-taxation-treaties/tax-treaties-by-country.aspx"
)
EBRIEF_INDEX = "https://www.revenue.ie/en/tax-professionals/ebrief/index.aspx"

GOV_IE_ATTRIBUTION = {
    "provider": "Department of Social Protection (gov.ie)",
    "statement": (
        "Contains Irish Public Sector Information licensed under a Creative Commons "
        "Attribution 4.0 International (CC BY 4.0) licence"
    ),
    "licence": "CC BY 4.0",
    "licence_url": "https://creativecommons.org/licenses/by/4.0/",
    "source_url": "https://assets.gov.ie/x/sw14.pdf",
    "modified": True,
    "modification_note": attribution.MODIFICATION_NOTE,
}


def _client(response):
    client = AsyncMock()
    client.request = AsyncMock(return_value=response)
    client.close = AsyncMock()
    return client


def _run(coro_fn, response, **kwargs):
    client = _client(response)
    with patch.object(
        server, "_get_client_and_loader", AsyncMock(return_value=(client, None, None))
    ):
        return asyncio.run(coro_fn(**kwargs))


def test_constants_match_spec():
    assert attribution.REVENUE_ATTRIBUTION_STATEMENT == STATEMENT
    assert attribution.REVENUE_LICENCE_URL == LICENCE_URL
    assert attribution.REVENUE_TDM_INDEX_URL == TDM_INDEX
    assert attribution.REVENUE_TREATIES_INDEX_URL == TREATY_INDEX
    assert attribution.REVENUE_EBRIEF_INDEX_URL == EBRIEF_INDEX


def test_revenue_source_shape():
    src = attribution.revenue_source("https://www.revenue.ie/x.pdf")
    assert src == {
        "provider": "Revenue Commissioners",
        "statement": STATEMENT,
        "licence": "CC BY 4.0",
        "licence_url": LICENCE_URL,
        "source_url": "https://www.revenue.ie/x.pdf",
        "modified": True,
        "modification_note": attribution.MODIFICATION_NOTE,
    }


def test_with_attribution_places_source_everywhere():
    src = attribution.revenue_source(TDM_INDEX)
    result = attribution._with_attribution(
        {"status": "success"}, source_url="https://www.irishtaxhub.ie/x", source=src
    )
    block = result.structured_content["attribution"]
    assert block["provider"] == "Irish Tax Hub"
    assert block["source"] == src
    assert block["last_updated_note"] == (
        "Date this response was generated. Source material is as last retrieved "
        "from the source identified in attribution.source."
    )
    assert json.loads(result.content[0].text)["attribution"]["source"] == src
    assert result.meta["attribution"]["source"] == src


def test_with_attribution_without_source_is_unchanged():
    result = attribution._with_attribution(
        {"status": "success"}, source_url="https://www.irishtaxhub.ie/x"
    )
    block = result.structured_content["attribution"]
    assert "source" not in block
    assert block["last_updated_note"] == "Live data retrieved from Irish Tax Hub on this date."


def test_upstream_attribution_is_moved_to_source():
    upstream = {"status": "success", "text": "t", "attribution": GOV_IE_ATTRIBUTION}
    result = attribution._with_attribution(
        upstream,
        source_url="https://www.irishtaxhub.ie/x",
        source=attribution.revenue_source(TDM_INDEX),
    )
    block = result.structured_content["attribution"]
    assert block["provider"] == "Irish Tax Hub"
    assert block["source"] == GOV_IE_ATTRIBUTION
    assert STATEMENT not in json.dumps(result.structured_content)


def test_get_revenue_document_text_keeps_gov_ie_upstream_attribution():
    upstream = {
        "status": "success",
        "filename": "sw14",
        "text": "t",
        "attribution": GOV_IE_ATTRIBUTION,
    }
    result = _run(server.get_revenue_document_text, upstream, filename="sw14")
    for view in (
        result.structured_content["attribution"],
        json.loads(result.content[0].text)["attribution"],
        result.meta["attribution"],
    ):
        assert view["source"] == GOV_IE_ATTRIBUTION


def test_search_revenue_documents_source():
    result = _run(
        server.search_revenue_documents, {"status": "success", "results": []}, query="ppr"
    )
    src = result.structured_content["attribution"]["source"]
    assert src["statement"] == STATEMENT
    assert src["source_url"] == TDM_INDEX


def test_list_revenue_document_categories_source():
    result = _run(server.list_revenue_document_categories, {"status": "success", "categories": []})
    assert result.structured_content["attribution"]["source"]["source_url"] == TDM_INDEX


def test_get_revenue_ebrief_changelog_source():
    result = _run(server.get_revenue_ebrief_changelog, {"status": "success", "entries": []})
    assert result.structured_content["attribution"]["source"]["source_url"] == EBRIEF_INDEX


def test_get_revenue_document_text_uses_upstream_url_or_index():
    with_url = _run(
        server.get_revenue_document_text,
        {
            "status": "success",
            "filename": "19-07-03",
            "text": "t",
            "url": "https://www.revenue.ie/a.pdf",
        },
        filename="19-07-03",
    )
    assert (
        with_url.structured_content["attribution"]["source"]["source_url"]
        == "https://www.revenue.ie/a.pdf"
    )
    without = _run(
        server.get_revenue_document_text,
        {"status": "success", "filename": "19-07-03", "text": "t"},
        filename="19-07-03",
    )
    assert without.structured_content["attribution"]["source"]["source_url"] == TDM_INDEX


def test_get_revenue_document_text_404_has_source():
    client = _client(None)
    response = httpx.Response(404, request=httpx.Request("GET", "http://x"))
    client.request = AsyncMock(
        side_effect=httpx.HTTPStatusError("404", request=response.request, response=response)
    )
    with patch.object(
        server, "_get_client_and_loader", AsyncMock(return_value=(client, None, None))
    ):
        result = asyncio.run(server.get_revenue_document_text(filename="missing"))
    assert result.structured_content["status"] == "error"
    assert result.structured_content["attribution"]["source"]["statement"] == STATEMENT


def test_treaty_tools_source():
    search = _run(
        server.search_tax_treaties, {"status": "success", "results": []}, query="dividends"
    )
    countries = _run(server.list_tax_treaty_countries, {"status": "success", "countries": []})
    text = _run(
        server.get_tax_treaty_text,
        {"status": "success", "filename": "usa-1997", "text": "t"},
        filename="usa-1997",
    )
    for r in (search, countries, text):
        src = r.structured_content["attribution"]["source"]
        assert src["statement"] == STATEMENT
        assert src["source_url"] == TREATY_INDEX


def test_server_instructions_contain_statement():
    assert STATEMENT in server.mcp.instructions


def test_attribution_schema_declares_source():
    assert "source" in attribution._ATTRIBUTION_SCHEMA["properties"]
    assert "source" not in attribution._ATTRIBUTION_SCHEMA["required"]
    for key in ("url", "title", "displayName"):
        assert key in attribution._DOCUMENT_TEXT_OUTPUT_SCHEMA["properties"]
