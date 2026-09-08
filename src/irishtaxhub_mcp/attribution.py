"""Stable MCP output contracts and Irish Tax Hub attribution rendering."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastmcp.tools import ToolResult
from mcp.types import ResourceLink, TextContent

# Every tool is read-only and reaches only the Irish Tax Hub API, which fronts
# Revenue data. Connector review requires each hint to be explicit.
_READ_ONLY = {
    "readOnlyHint": True,
    "openWorldHint": False,
    "destructiveHint": False,
}

_SITE_URL = "https://www.irishtaxhub.ie"
_API_DOCS_URL = "https://prod.aws.irishtaxhub.ie/docs"

_ATTRIBUTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Source attribution and a link back to Irish Tax Hub.",
    "properties": {
        "provider": {"type": "string"},
        "source_url": {"type": "string", "format": "uri"},
        "methodology_url": {"type": "string", "format": "uri"},
        "last_updated": {"type": "string", "format": "date"},
        "last_updated_note": {"type": "string"},
        "relevant_url": {"type": "string", "format": "uri"},
        "action": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "url": {"type": "string", "format": "uri"},
            },
            "required": ["label", "url"],
            "additionalProperties": False,
        },
    },
    "required": [
        "provider",
        "source_url",
        "methodology_url",
        "last_updated",
        "relevant_url",
        "action",
    ],
    "additionalProperties": True,
}


def _attributed_output_schema(
    properties: Optional[Dict[str, Any]] = None,
    required: Optional[List[str]] = None,
    *,
    attribution_key: str = "attribution",
) -> Dict[str, Any]:
    """Build a permissive API-data schema with the stable attribution block."""
    output_properties = dict(properties or {})
    output_properties[attribution_key] = _ATTRIBUTION_SCHEMA
    return {
        "type": "object",
        "properties": output_properties,
        "required": [*(required or []), attribution_key],
        # Calculator payloads evolve independently, so allow fields this server
        # does not know while describing the stable response contract.
        "additionalProperties": True,
    }


_CALCULATION_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "status": {"type": "string"},
        "message": {"type": "string"},
        "calculation_count": {"type": "integer"},
        "result": {"type": "object", "additionalProperties": True},
        "breakdown": {"type": "object", "additionalProperties": True},
        "data": {"type": "object", "additionalProperties": True},
    },
    ["status"],
)

_CALCULATOR_SCHEMA_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "type": {"type": "string"},
        "properties": {"type": "object", "additionalProperties": True},
        "required": {"type": "array", "items": {"type": "string"}},
    },
    attribution_key="x-irish-tax-hub-attribution",
)

_CALCULATOR_LIST_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "result": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "url": {"type": "string", "format": "uri"},
                },
                "required": ["name", "description", "url"],
                "additionalProperties": False,
            },
        }
    },
    ["result"],
)

_TAX_CONSTANTS_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "status": {"type": "string"},
        "message": {"type": "string"},
        "data": {"type": "object", "additionalProperties": True},
    },
    ["status", "data"],
)

_KEY_DATES_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "status": {"type": "string"},
        "message": {"type": "string"},
        "year": {"type": "integer"},
        "data": {"type": "array", "items": {"type": "object"}},
    },
    ["status", "year", "data"],
)

_SEARCH_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "status": {"type": "string"},
        "results": {"type": "array", "items": {"type": "object"}},
        "total": {"type": "integer"},
        "limit": {"type": "integer"},
        "offset": {"type": "integer"},
    },
    ["status", "results"],
)

_DOCUMENT_TEXT_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "status": {"type": "string", "enum": ["success", "error"]},
        "filename": {"type": "string"},
        "text": {"type": "string"},
        "message": {"type": "string"},
    },
    ["status"],
)

_CATEGORIES_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "status": {"type": "string"},
        "categories": {"type": "array", "items": {"type": "object"}},
    },
    ["status", "categories"],
)

_CHANGELOG_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "status": {"type": "string"},
        "entries": {"type": "array", "items": {"type": "object"}},
        "total": {"type": "integer"},
        "limit": {"type": "integer"},
        "offset": {"type": "integer"},
    },
    ["status"],
)

_COUNTRIES_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "status": {"type": "string"},
        "countries": {"type": "array", "items": {"type": "object"}},
    },
    ["status", "countries"],
)

_CALCULATOR_STATS_OUTPUT_SCHEMA = _attributed_output_schema(
    {
        "status": {"type": "string"},
        "calculator": {"type": "string"},
        "calculation_count": {"type": "integer", "minimum": 0},
    },
    ["status", "calculator", "calculation_count"],
)


def _site_url(path: str) -> str:
    return f"{_SITE_URL}{path}"


def _with_attribution(
    result: Any,
    *,
    source_url: str,
    relevant_url: Optional[str] = None,
    schema_result: bool = False,
) -> ToolResult:
    """Add visible attribution without hiding or replacing the upstream result."""
    continue_url = relevant_url or source_url
    attribution = {
        "provider": "Irish Tax Hub",
        "source_url": source_url,
        "methodology_url": _API_DOCS_URL,
        "last_updated": datetime.now(timezone.utc).date().isoformat(),
        "last_updated_note": "Live data retrieved from Irish Tax Hub on this date.",
        "relevant_url": continue_url,
        "action": {
            "label": "Continue on Irish Tax Hub",
            "url": continue_url,
        },
    }

    if isinstance(result, dict):
        structured_content = dict(result)
    else:
        # FastMCP wraps lists in a `result` object; retain that shape when a
        # custom ToolResult supplies the structured content.
        structured_content = {"result": result}

    attribution_key = "x-irish-tax-hub-attribution" if schema_result else "attribution"
    structured_content[attribution_key] = attribution

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(structured_content, ensure_ascii=False, default=str),
            ),
            ResourceLink(
                type="resource_link",
                name="continue-on-irish-tax-hub",
                title="Continue on Irish Tax Hub",
                uri=continue_url,
                description="Open the relevant Irish Tax Hub calculator or guide.",
                mimeType="text/html",
            ),
        ],
        structured_content=structured_content,
        meta={"attribution": attribution},
    )
