from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional

from fastmcp import FastMCP
from pydantic import Field

from .client import IrishTaxHubClient
from .openapi import OpenAPILoader, get_request_body_schema, validate_body
from .settings import Settings

mcp = FastMCP("irishtaxhub-mcp")

# All available calculator names with their API paths
CALCULATORS: Dict[str, Dict[str, str]] = {
    "base": {
        "path": "/v1/tax/calculators/base",
        "summary": (
            "Calculate income tax, USC, and PRSI for a given salary."
            " Supports single/married, multiple employments, tax credits."
        ),
    },
    "refund": {
        "path": "/v1/tax/calculators/refund",
        "summary": "Estimate a PAYE tax refund by comparing tax paid vs tax owed.",
    },
    "tax-free-earnings": {
        "path": "/v1/tax/calculators/tax-free-earnings",
        "summary": (
            "Calculate tax-free earnings date for someone"
            " arriving in or departing Ireland mid-year."
        ),
    },
    "refund-for-move-date": {
        "path": "/v1/tax/calculators/refund-for-move-date",
        "summary": "Calculate tax refund for a specific move date (arriving/departing Ireland).",
    },
    "net-to-gross": {
        "path": "/v1/tax/calculators/net-to-gross",
        "summary": "Reverse-calculate the gross salary needed to achieve a target net income.",
    },
    "rental-income": {
        "path": "/v1/tax/calculators/rental-income",
        "summary": (
            "Calculate tax on rental income including" " allowable expenses and mortgage interest."
        ),
    },
    "self-employed": {
        "path": "/v1/tax/calculators/self-employed",
        "summary": (
            "Calculate tax for self-employed individuals" " including PRSI Class S and expenses."
        ),
    },
    "capital-gains": {
        "path": "/v1/tax/calculators/capital-gains",
        "summary": "Calculate Capital Gains Tax (CGT) on asset disposals at 33%.",
    },
    "share-options": {
        "path": "/v1/tax/calculators/share-options",
        "summary": "Calculate tax on share option exercise (RTSO — Relevant Tax on Share Options).",
    },
    "share-options-cgt": {
        "path": "/v1/tax/calculators/share-options-cgt",
        "summary": "Calculate CGT on the sale of shares acquired via share options.",
    },
    "work-from-home-expense": {
        "path": "/v1/tax/calculators/work-from-home-expense",
        "summary": "Calculate e-worker tax relief for remote working expenses.",
    },
    "avc": {
        "path": "/v1/tax/calculators/avc",
        "summary": "Calculate maximum Additional Voluntary Contribution (AVC) and tax relief.",
    },
    "pension-value": {
        "path": "/v1/tax/calculators/pension-value",
        "summary": "Estimate pension fund value at retirement based on contributions and growth.",
    },
    "future-fund": {
        "path": "/v1/tax/calculators/future-fund",
        "summary": "Estimate future investment fund value with regular contributions.",
    },
    "mortgage": {
        "path": "/v1/tax/calculators/mortgage",
        "summary": "Calculate monthly mortgage repayments, total interest, and amortisation.",
    },
    "redundancy-tax": {
        "path": "/v1/tax/calculators/redundancy-tax",
        "summary": "Calculate tax on redundancy and termination payments (SCSB, top-up, etc.).",
    },
    "mortgage-affordability": {
        "path": "/v1/tax/calculators/mortgage-affordability",
        "summary": "Calculate maximum mortgage you can afford based on income and LTI rules.",
    },
    "cat": {
        "path": "/v1/tax/calculators/cat",
        "summary": "Calculate Capital Acquisitions Tax (CAT) on gifts and inheritances.",
    },
    "sarp": {
        "path": "/v1/tax/calculators/sarp",
        "summary": (
            "Calculate SARP (Special Assignee Relief Programme)"
            " tax relief for foreign assignees."
        ),
    },
    "vat3": {
        "path": "/v1/tax/calculators/vat3",
        "summary": "Calculate VAT3 return figures for VAT-registered businesses.",
    },
}


# Build the Literal type and enum from CALCULATORS keys
CalculatorName = Literal[
    "base",
    "refund",
    "tax-free-earnings",
    "refund-for-move-date",
    "net-to-gross",
    "rental-income",
    "self-employed",
    "capital-gains",
    "share-options",
    "share-options-cgt",
    "work-from-home-expense",
    "avc",
    "pension-value",
    "future-fund",
    "mortgage",
    "redundancy-tax",
    "mortgage-affordability",
    "cat",
    "sarp",
    "vat3",
]

# Build a static description string for the calculate_tax tool
_CALC_LIST = "\n".join(f"  - {name}: {info['summary']}" for name, info in CALCULATORS.items())

_CALCULATE_TAX_DESC = f"""Run an Irish tax calculator and return the full result.

Available calculators:
{_CALC_LIST}

Pass the calculator name and its required inputs. \
Use `get_calculator_schema` first if you need to know \
the exact input fields for a calculator.

Common examples:

base (income tax): {{"marital_status": "single", \
"employment_income": {{"income": 75000, "period": "annual"}}, \
"year": 2025}}

marital_status options: single, widow, \
married_one_income, married_two_income

refund: {{"marital_status": "single", \
"employment_income": {{"income": 50000, "tax_paid": 18000}}, \
"year": 2025}}

capital-gains: {{"sale_price": 400000, \
"purchase_price": 250000, "purchase_date": "2018-03-15", \
"sale_date": "2025-06-01", "year": 2025}}

mortgage: {{"home_price": 400000, "deposit": 40000, \
"loan_term_years": 30, "interest_rate": 4.0}}

work-from-home-expense: {{"electricity_costs": 1200, \
"heating_costs": 800, "internet_costs": 600, \
"tax_year": 2025, "total_earnings": 75000, \
"days_working_from_home": 200}}

avc: {{"age": 45, "gross_earnings": 100000, "year": 2025}}

share-options: {{"share_option_price": 10, \
"sale_price": 50, "number_of_units": 1000}}

redundancy-tax: {{"employment_start_date": "2010-01-01", \
"employment_end_date": "2025-06-01", "gross_weekly_pay": 1500}}

mortgage-affordability: {{"buyer_type": "first_time_buyer", \
"gross_annual_income_1": 75000, "savings": 50000}}"""


async def _get_client_and_loader() -> tuple[IrishTaxHubClient, OpenAPILoader, Settings]:
    settings = Settings.load()
    loader = OpenAPILoader(settings.base_url, settings.openapi, settings.timeout)
    client = IrishTaxHubClient(settings.base_url, settings.api_key, settings.timeout)
    return client, loader, settings


@mcp.tool(description=_CALCULATE_TAX_DESC)
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
        return await client.request("POST", calc["path"], json_body=inputs)
    finally:
        await client.close()


@mcp.tool
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
    return schema or {}


@mcp.tool
async def list_calculators() -> List[Dict[str, str]]:
    """List all available Irish tax calculators with their names and descriptions.

    Returns a list of calculators that can be used with the `calculate_tax` tool.
    """
    return [{"name": name, "description": info["summary"]} for name, info in CALCULATORS.items()]


@mcp.tool
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
        return await client.request("GET", "/v1/tax/constants", params=params or None)
    finally:
        await client.close()


@mcp.tool
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
        return await client.request("POST", "/v1/tax/key-dates", json_body=body or None)
    finally:
        await client.close()


def _search_algolia_revenue_documents(
    query: str, category: Optional[str], limit: int
) -> Optional[List[Dict[str, Any]]]:
    """Search Revenue documents via Algolia full-text index.

    Returns a list of result dicts, or None if Algolia is not configured.
    """
    import os

    search_only_key = os.environ.get("ALGOLIA_SEARCH_ONLY_KEY")
    if not search_only_key:
        return None

    from algoliasearch.search.client import SearchClientSync

    client = SearchClientSync("B6A5JWIU4S", search_only_key)
    try:
        result = client.search_single_index(
            index_name="revenue-documents",
            search_params={
                "query": query,
                "filters": f'category:"{category}"' if category else "",
                "hitsPerPage": limit,
                "attributesToSnippet": ["content:40"],
                "snippetEllipsisText": "…",
                "distinct": True,
            },
        )
    finally:
        client.close()

    hits: List[Dict[str, Any]] = []
    for hit in result.hits:
        snippet = ""
        snippet_result = hit.get("_snippetResult", {})
        if isinstance(snippet_result, dict):
            content_snippet = snippet_result.get("content", {})
            if isinstance(content_snippet, dict):
                snippet = content_snippet.get("value", "")

        hits.append(
            {
                "title": hit.get("title", ""),
                "displayName": hit.get("displayName", ""),
                "description": hit.get("description", ""),
                "category": hit.get("category", ""),
                "url": hit.get("docUrl", ""),
                "keywords": hit.get("keywords", []),
                "contentSnippet": snippet,
            }
        )

    return hits


@mcp.tool
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
    """Search Irish Revenue Tax & Duty Manual (TDM) documents by full-text content.

    Find official Revenue guidance documents by keyword. Searches the full text
    of 1,343 TDM documents, returning matching snippets showing where your query
    was found. Use `get_revenue_document_text` to read the full text of a specific document.
    """
    # Try Algolia full-text search first
    algolia_results = _search_algolia_revenue_documents(query, category, limit)
    if algolia_results is not None:
        return {"source": "algolia", "query": query, "results": algolia_results}

    # Fall back to API title/keyword search if Algolia is not configured
    client, loader, settings = await _get_client_and_loader()
    try:
        params: Dict[str, Any] = {"q": query, "limit": limit}
        if category:
            params["category"] = category
        return await client.request("GET", "/v1/revenue/documents", params=params)
    finally:
        await client.close()


@mcp.tool
async def get_revenue_document_text(
    filename: Annotated[
        str,
        Field(
            description=(
                "Document filename as returned by"
                " `search_revenue_documents`"
                " (e.g. 'part-04-06-02')."
                " Do NOT include the .pdf extension."
            )
        ),
    ],
) -> Any:
    """Get the full text of a specific Revenue Tax & Duty Manual document.

    Use `search_revenue_documents` first to find the filename.
    Not all documents have extracted text available.
    """
    import httpx

    client, loader, settings = await _get_client_and_loader()
    try:
        return await client.request("GET", f"/v1/revenue/documents/text/{filename}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {
                "status": "error",
                "message": (
                    f"Full text not available for '{filename}'. "
                    "Use the search result metadata (title, description, "
                    "keywords, url) instead."
                ),
            }
        raise
    finally:
        await client.close()


@mcp.tool
async def list_revenue_document_categories() -> Any:
    """List all available categories for Revenue Tax & Duty Manual documents.

    Use with `search_revenue_documents` to filter results by category.
    """
    client, loader, settings = await _get_client_and_loader()
    try:
        return await client.request("GET", "/v1/revenue/documents/categories")
    finally:
        await client.close()


@mcp.tool
async def get_revenue_ebrief_changelog() -> Any:
    """Get the Revenue eBrief changelog — recent updates to Revenue guidance and Tax & Duty Manuals.

    Useful for checking what Revenue guidance has changed recently.
    """
    client, loader, settings = await _get_client_and_loader()
    try:
        return await client.request("GET", "/v1/revenue/documents/changelog")
    finally:
        await client.close()


@mcp.tool
async def generate_net_income_summary(
    status: Annotated[
        str, Field(description="The 'status' field from the base tax calculation response.")
    ],
    message: Annotated[
        str, Field(description="The 'message' field from the base tax calculation response.")
    ],
    year: Annotated[int, Field(description="Tax year (e.g. 2025).", ge=2024, le=2034)],
    breakdown: Annotated[
        Dict[str, Any],
        Field(description="The full 'breakdown' object from the base tax calculation response."),
    ],
) -> Any:
    """Generate an AI-powered plain-English summary of a tax calculation.

    This takes the OUTPUT from a `calculate_tax` call (with calculator_name="base") and returns
    a human-readable explanation of the tax breakdown, effective rates, and key insights.

    Workflow: first call `calculate_tax(calculator_name="base", inputs={...})`, then pass the
    response fields (status, message, year, breakdown) to this tool.
    """
    client, loader, settings = await _get_client_and_loader()
    try:
        body = {
            "status": status,
            "message": message,
            "year": year,
            "breakdown": breakdown,
        }
        return await client.request(
            "POST", "/v1/tax/calculators/net-income-summary", json_body=body
        )
    finally:
        await client.close()


# Mapping from MCP calculator names to the frontend slugs used by the stats API
_STATS_SLUG_MAP: Dict[str, str] = {
    "base": "salary-after-tax",
    "refund": "refund",
    "tax-free-earnings": "arriving-ireland-tax-savings",
    "refund-for-move-date": "arriving-ireland-tax-savings",
    "net-to-gross": "net-to-gross",
    "rental-income": "rental-income",
    "self-employed": "self-employed-income",
    "capital-gains": "capital-gains-tax",
    "share-options": "employee-share-options",
    "share-options-cgt": "share-sale-cgt",
    "work-from-home-expense": "work-from-home",
    "avc": "additional-voluntary-contribution",
    "pension-value": "pension-value",
    "future-fund": "auto-enrolment",
    "mortgage": "mortgage-payments",
    "redundancy-tax": "redundancy-tax",
    "mortgage-affordability": "mortgage-affordability",
    "cat": "cat",
    "sarp": "sarp",
    "vat3": "vat3",
}


@mcp.tool
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
        return await client.request("GET", f"/v1/tax/calculators/{stats_slug}/stats")
    finally:
        await client.close()


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
