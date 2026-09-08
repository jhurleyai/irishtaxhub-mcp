from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import Field

from . import attribution as _attribution_contracts
from . import calculator_catalog as _calculator_catalog
from .attribution import (
    _CALCULATION_OUTPUT_SCHEMA,
    _CALCULATOR_LIST_OUTPUT_SCHEMA,
    _CALCULATOR_SCHEMA_OUTPUT_SCHEMA,
    _CALCULATOR_STATS_OUTPUT_SCHEMA,
    _CATEGORIES_OUTPUT_SCHEMA,
    _CHANGELOG_OUTPUT_SCHEMA,
    _COUNTRIES_OUTPUT_SCHEMA,
    _DOCUMENT_TEXT_OUTPUT_SCHEMA,
    _KEY_DATES_OUTPUT_SCHEMA,
    _READ_ONLY,
    _SEARCH_OUTPUT_SCHEMA,
    _TAX_CONSTANTS_OUTPUT_SCHEMA,
    _site_url,
    _with_attribution,
)
from .calculator_catalog import (
    _CALCULATE_TAX_DESC,
    _STATS_SLUG_MAP,
    CALCULATORS,
    CalculatorName,
    _calculator_url,
)
from .client import IrishTaxHubClient
from .openapi import OpenAPILoader, get_request_body_schema, validate_body
from .settings import Settings

# Keep historical module-level imports working after moving these definitions.
_API_DOCS_URL = _attribution_contracts._API_DOCS_URL
_ATTRIBUTION_SCHEMA = _attribution_contracts._ATTRIBUTION_SCHEMA
_SITE_URL = _attribution_contracts._SITE_URL
_attributed_output_schema = _attribution_contracts._attributed_output_schema
_CALC_LIST = _calculator_catalog._CALC_LIST

mcp = FastMCP("irishtaxhub-mcp")


async def _get_client_and_loader() -> tuple[IrishTaxHubClient, OpenAPILoader, Settings]:
    settings = Settings.load()
    loader = OpenAPILoader(settings.base_url, settings.openapi, settings.timeout)
    client = IrishTaxHubClient(settings.base_url, settings.api_key, settings.timeout)
    return client, loader, settings


@mcp.tool(
    title="Calculate Irish Tax",
    description=_CALCULATE_TAX_DESC,
    output_schema=_CALCULATION_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def calculate_tax(
    calculator_name: Annotated[
        CalculatorName,
        Field(description="The calculator to run. See tool description for the full list."),
    ],
    inputs: Annotated[
        Dict[str, Any],
        Field(
            description=(
                "Calculator input parameters. Use"
                " `get_calculator_schema` to discover the"
                " required fields for a specific calculator."
            )
        ),
    ],
) -> Any:
    calc = CALCULATORS.get(calculator_name)
    if not calc:
        available = ", ".join(sorted(CALCULATORS.keys()))
        raise ValueError(
            f"Unknown calculator: '{calculator_name}'. Available calculators: {available}"
        )

    client, loader, settings = await _get_client_and_loader()
    try:
        spec = await loader.load()
        validate_body(spec, calc["path"], "post", inputs)
        result = await client.request("POST", calc["path"], json_body=inputs)
        calculator_url = _calculator_url(calculator_name)
        return _with_attribution(
            result,
            source_url=calculator_url,
            relevant_url=calculator_url,
        )
    finally:
        await client.close()


@mcp.tool(
    title="Get Calculator Schema",
    output_schema=_CALCULATOR_SCHEMA_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def get_calculator_schema(
    calculator_name: Annotated[
        CalculatorName, Field(description="The calculator to get the schema for.")
    ],
) -> Any:
    """Get the JSON Schema for a specific tax calculator.

    Returns input fields, types, defaults, and constraints.
    Use before calling `calculate_tax` if you need to know
    what fields are required.
    """
    calc = CALCULATORS.get(calculator_name)
    if not calc:
        available = ", ".join(sorted(CALCULATORS.keys()))
        raise ValueError(
            f"Unknown calculator: '{calculator_name}'. Available calculators: {available}"
        )

    settings = Settings.load()
    loader = OpenAPILoader(settings.base_url, settings.openapi, settings.timeout)
    spec = await loader.load()
    schema = get_request_body_schema(spec, calc["path"], "post")
    calculator_url = _calculator_url(calculator_name)
    return _with_attribution(
        schema or {},
        source_url=calculator_url,
        relevant_url=calculator_url,
        schema_result=True,
    )


@mcp.tool(
    title="List Tax Calculators",
    output_schema=_CALCULATOR_LIST_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def list_calculators() -> List[Dict[str, str]]:
    """List all available Irish tax calculators with their names and descriptions.

    Returns a list of calculators that can be used with the `calculate_tax` tool.
    """
    result = [
        {
            "name": name,
            "description": info["summary"],
            "url": _calculator_url(name),
        }
        for name, info in CALCULATORS.items()
    ]
    return _with_attribution(
        result,
        source_url=_site_url("/calculators"),
        relevant_url=_site_url("/calculators"),
    )


@mcp.tool(
    title="Get Tax Constants",
    output_schema=_TAX_CONSTANTS_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def get_tax_constants(
    year: Annotated[
        Optional[int],
        Field(description="Tax year (e.g. 2025). Defaults to current year.", ge=2024, le=2034),
    ] = None,
) -> Any:
    """Get Irish tax constants.

    Returns tax bands, rates, USC rates, PRSI rates,
    tax credits, and thresholds. Useful for understanding
    the current tax rules without running a full calculation.
    """
    client, loader, settings = await _get_client_and_loader()
    try:
        params = {}
        if year is not None:
            params["year"] = year
        result = await client.request("GET", "/v1/tax/constants", params=params or None)
        return _with_attribution(
            result,
            source_url=_site_url("/irish-income-tax-hub"),
            relevant_url=_site_url("/calculators/salary-after-tax"),
        )
    finally:
        await client.close()


@mcp.tool(
    title="Get Revenue Key Dates",
    output_schema=_KEY_DATES_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def get_key_dates(
    year: Annotated[
        Optional[int],
        Field(description="Tax year (e.g. 2026). Defaults to current year.", ge=2024, le=2034),
    ] = None,
    month: Annotated[
        Optional[str], Field(description="Filter by month name (e.g. 'January', 'October').")
    ] = None,
    tax_type: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter by tax type"
                " (e.g. 'VAT', 'PAYE', 'Income Tax',"
                " 'CGT', 'Corporation Tax')."
            )
        ),
    ] = None,
) -> Any:
    """Get important Irish Revenue dates and deadlines (filing dates, payment dates, etc.)."""
    client, loader, settings = await _get_client_and_loader()
    try:
        body: Dict[str, Any] = {}
        if year is not None:
            body["year"] = year
        if month is not None:
            body["month"] = month
        if tax_type is not None:
            body["tax_type"] = tax_type
        result = await client.request("POST", "/v1/tax/key-dates", json_body=body or None)
        return _with_attribution(
            result,
            source_url=_site_url("/tax-calendar"),
            relevant_url=_site_url("/tax-calendar"),
        )
    finally:
        await client.close()


@mcp.tool(
    title="Search Revenue Documents",
    output_schema=_SEARCH_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def search_revenue_documents(
    query: Annotated[
        str,
        Field(
            description=("Search terms (e.g. 'rental income'," " 'CGT relief', 'PAYE credits').")
        ),
    ],
    category: Annotated[
        Optional[str],
        Field(
            description="Category filter. Use `list_revenue_document_categories` to see options."
        ),
    ] = None,
    limit: Annotated[int, Field(description="Maximum results to return.", ge=1, le=50)] = 10,
) -> Any:
    """Search Irish Revenue Tax & Duty Manual (TDM) documents.

    Find official Revenue guidance documents by keyword.
    Returns document titles, categories, and filenames.
    Use `get_revenue_document_text` to read the full text of a specific document.
    """
    client, loader, settings = await _get_client_and_loader()
    try:
        params: Dict[str, Any] = {"q": query, "limit": limit}
        if category:
            params["category"] = category
        result = await client.request("GET", "/v1/revenue/documents", params=params)
        return _with_attribution(
            result,
            source_url=_site_url("/revenue-documents"),
            relevant_url=_site_url("/revenue-documents"),
        )
    finally:
        await client.close()


def _normalise_document_identifier(value: str) -> str:
    """Extract a bare filename from a URL, path, or filename.

    Accepts any of the following and returns the bare identifier (e.g. ``19-07-03``)
    that the ``/v1/revenue/documents/text/{filename}`` endpoint expects:
      - full PDF URL: ``https://.../part-19/19-07-03.pdf``
      - ``textUrl`` from search results: ``/revenue/documents/text/19-07-03``
      - bare filename: ``19-07-03`` or ``19-07-03.pdf``
    """
    identifier = value.strip().rstrip("/").split("/")[-1]
    if identifier.lower().endswith(".pdf"):
        identifier = identifier[:-4]
    return identifier


@mcp.tool(
    title="Get Revenue Document Text",
    output_schema=_DOCUMENT_TEXT_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def get_revenue_document_text(
    filename: Annotated[
        str,
        Field(
            description=(
                "Document identifier — accepts a bare filename"
                " (e.g. '19-07-03'), a filename with .pdf,"
                " the full Revenue PDF URL, or the 'textUrl'"
                " value from a search result."
            )
        ),
    ],
) -> Any:
    """Get the full text of a specific Revenue Tax & Duty Manual document.

    Use `search_revenue_documents` first to find the document. You can pass
    the ``url`` from the search result directly — URLs, paths, and bare
    filenames are all accepted. Not all documents have extracted text available.
    """
    import httpx

    identifier = _normalise_document_identifier(filename)

    client, loader, settings = await _get_client_and_loader()
    try:
        result = await client.request("GET", f"/v1/revenue/documents/text/{identifier}")
        return _with_attribution(
            result,
            source_url=_site_url("/revenue-documents"),
            relevant_url=_site_url("/revenue-documents"),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return _with_attribution(
                {
                    "status": "error",
                    "message": (
                        f"Full text not available for '{identifier}'. "
                        "Use the search result metadata (title, description, "
                        "keywords, url) instead."
                    ),
                },
                source_url=_site_url("/revenue-documents"),
                relevant_url=_site_url("/revenue-documents"),
            )
        raise
    finally:
        await client.close()


@mcp.tool(
    title="List Revenue Document Categories",
    output_schema=_CATEGORIES_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def list_revenue_document_categories() -> Any:
    """List all available categories for Revenue Tax & Duty Manual documents.

    Use with `search_revenue_documents` to filter results by category.
    """
    client, loader, settings = await _get_client_and_loader()
    try:
        result = await client.request("GET", "/v1/revenue/documents/categories")
        return _with_attribution(
            result,
            source_url=_site_url("/revenue-documents"),
            relevant_url=_site_url("/revenue-documents"),
        )
    finally:
        await client.close()


@mcp.tool(
    title="Get Revenue eBrief Changelog",
    output_schema=_CHANGELOG_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def get_revenue_ebrief_changelog() -> Any:
    """Get the Revenue eBrief changelog — recent updates to Revenue guidance and Tax & Duty Manuals.

    Useful for checking what Revenue guidance has changed recently.
    """
    client, loader, settings = await _get_client_and_loader()
    try:
        result = await client.request("GET", "/v1/revenue/documents/changelog")
        return _with_attribution(
            result,
            source_url=_site_url("/revenue-documents"),
            relevant_url=_site_url("/revenue-documents"),
        )
    finally:
        await client.close()


@mcp.tool(
    title="Search Tax Treaties",
    output_schema=_SEARCH_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def search_tax_treaties(
    query: Annotated[
        str,
        Field(description="Search terms (e.g. 'dividends withholding', 'France royalties')."),
    ],
    country: Annotated[
        Optional[str],
        Field(description="Country filter. Use `list_tax_treaty_countries` to see options."),
    ] = None,
    limit: Annotated[int, Field(description="Maximum results to return.", ge=1, le=50)] = 10,
) -> Any:
    """Search Ireland's double-taxation treaty documents (treaties, protocols, MLI texts).

    Find treaty documents by keyword and/or country. Returns titles, country, document
    type, and identifiers. Use `get_tax_treaty_text` to read the full text of a document.
    """
    client, loader, settings = await _get_client_and_loader()
    try:
        params: Dict[str, Any] = {"q": query, "limit": limit}
        if country:
            params["country"] = country
        result = await client.request("GET", "/v1/tax-treaties", params=params)
        return _with_attribution(
            result,
            source_url=_site_url("/mcp"),
            relevant_url=_site_url("/mcp"),
        )
    finally:
        await client.close()


@mcp.tool(
    title="Get Tax Treaty Text",
    output_schema=_DOCUMENT_TEXT_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def get_tax_treaty_text(
    filename: Annotated[
        str,
        Field(
            description=(
                "Treaty identifier — accepts a bare filename (e.g. 'usa-1997'),"
                " a filename with .pdf, the full Revenue PDF URL, or the 'textUrl'"
                " value from a search result."
            )
        ),
    ],
) -> Any:
    """Get the full text of a specific tax-treaty document.

    Use `search_tax_treaties` first to find the document. URLs, paths, and bare
    filenames are all accepted. Not all documents have extracted text available.
    """
    import httpx

    identifier = _normalise_document_identifier(filename)

    client, loader, settings = await _get_client_and_loader()
    try:
        result = await client.request("GET", f"/v1/tax-treaties/text/{identifier}")
        return _with_attribution(
            result,
            source_url=_site_url("/mcp"),
            relevant_url=_site_url("/mcp"),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return _with_attribution(
                {
                    "status": "error",
                    "message": (
                        f"Full text not available for '{identifier}'. "
                        "Use the search result metadata (title, description, "
                        "keywords, country, url) instead."
                    ),
                },
                source_url=_site_url("/mcp"),
                relevant_url=_site_url("/mcp"),
            )
        raise
    finally:
        await client.close()


@mcp.tool(
    title="List Tax Treaty Countries",
    output_schema=_COUNTRIES_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def list_tax_treaty_countries() -> Any:
    """List all countries with an Irish double-taxation treaty.

    Use with `search_tax_treaties` to filter results by country.
    """
    client, loader, settings = await _get_client_and_loader()
    try:
        result = await client.request("GET", "/v1/tax-treaties/countries")
        return _with_attribution(
            result,
            source_url=_site_url("/mcp"),
            relevant_url=_site_url("/mcp"),
        )
    finally:
        await client.close()


@mcp.tool(
    title="Get Calculator Stats",
    output_schema=_CALCULATOR_STATS_OUTPUT_SCHEMA,
    annotations=_READ_ONLY,
)
async def get_calculator_stats(
    calculator_name: Annotated[
        CalculatorName, Field(description="The calculator to get stats for.")
    ],
) -> Any:
    """Get usage statistics for a specific tax calculator."""
    calc = CALCULATORS.get(calculator_name)
    if not calc:
        available = ", ".join(sorted(CALCULATORS.keys()))
        raise ValueError(
            f"Unknown calculator: '{calculator_name}'. Available calculators: {available}"
        )

    stats_slug = _STATS_SLUG_MAP.get(calculator_name, calculator_name)
    client, loader, settings = await _get_client_and_loader()
    try:
        result = await client.request("GET", f"/v1/tax/calculators/{stats_slug}/stats")
        calculator_url = _calculator_url(calculator_name)
        return _with_attribution(
            result,
            source_url=calculator_url,
            relevant_url=calculator_url,
        )
    finally:
        await client.close()


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
