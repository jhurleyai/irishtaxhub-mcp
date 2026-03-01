# IrishTaxHub MCP Server

Model Context Protocol (MCP) server that exposes IrishTaxHub API operations as tools.

This server now uses FastMCP v2 for a simpler, production-ready implementation.

## Features
- Dynamic OpenAPI-powered tools only:
  - `openapi_list_endpoints(tag?)` → discover available endpoints
  - `openapi_get_request_schema(path, method=POST)` → JSON Schema for request body
  - `openapi_invoke(path, method=POST, body?, params?)` → validate and call dynamically

## Install

Use Poetry (recommended) or pip.

```bash
# With Poetry
poetry install

# Or with pip
pip install -e .

# If running directly with FastMCP CLI
pip install fastmcp
```

## Configure

Set environment variables (or copy `.env.example` to `.env`):

**For production use:**
```bash
export IRISHTAXHUB_BASE_URL="https://prod.aws.irishtaxhub.ie"
export IRISHTAXHUB_TIMEOUT="30"
# OpenAPI source (file or URL). Defaults to "$IRISHTAXHUB_BASE_URL/apispec_1.json".
export IRISHTAXHUB_OPENAPI="https://prod.aws.irishtaxhub.ie/apispec_1.json"
export IRISHTAXHUB_DEVELOPMENT_MODE=false
```

**For local development (if running the API locally):**
```bash
export IRISHTAXHUB_BASE_URL="http://localhost:5000"
export IRISHTAXHUB_TIMEOUT="30"
export IRISHTAXHUB_OPENAPI="http://localhost:5000/openapi.json"
export IRISHTAXHUB_DEVELOPMENT_MODE=true
```

## Run (local)

Standard I/O server (used by MCP clients):

```bash
python -m irishtaxhub_mcp.server
# or via Poetry
poetry run irishtaxhub-mcp

# or run with the FastMCP CLI (equivalent)
fastmcp run src/irishtaxhub_mcp/server.py
```

## Use with Claude Desktop

Add an MCP server entry to your Claude Desktop config (replace path as needed):

**For production use:**
```json
{
  "mcpServers": {
    "irishtaxhub": {
      "command": "python",
      "args": ["-m", "irishtaxhub_mcp.server"],
      "env": {
        "IRISHTAXHUB_BASE_URL": "https://prod.aws.irishtaxhub.ie",
        "IRISHTAXHUB_OPENAPI": "https://prod.aws.irishtaxhub.ie/apispec_1.json"
      }
    }
  }
}
```

**For local development:**
```json
{
  "mcpServers": {
    "irishtaxhub": {
      "command": "python",
      "args": ["-m", "irishtaxhub_mcp.server"],
      "env": {
        "IRISHTAXHUB_BASE_URL": "http://localhost:5000",
        "IRISHTAXHUB_OPENAPI": "http://localhost:5000/openapi.json"
      }
    }
  }
}
```

Then restart Claude Desktop; tools will appear as `openapi_list_endpoints`,
`openapi_get_request_schema`, and `openapi_invoke`.

## Examples

Dynamic discovery + invocation:

```json
{
  "tool": "openapi_list_endpoints",
  "arguments": { "tag": "Tax Calculators" }
}
```

```json
{
  "tool": "openapi_get_request_schema",
  "arguments": { "path": "/v1/tax/calculators/refund", "method": "POST" }
}
```

```json
{
  "tool": "openapi_invoke",
  "arguments": {
    "path": "/v1/tax/calculators/refund",
    "method": "POST",
    "body": {
      "marital_status": "single",
      "year": 2024,
      "employment_income": { "income": 50000 }
    }
  }
}
```

## Notes
- Tools call your deployed HTTP API; they do not import internal Python modules. This keeps the MCP server lightweight and decoupled.
- Dynamic tools load your OpenAPI definition from a file or via HTTP. For local development, you can point `IRISHTAXHUB_OPENAPI` at your repo’s `openapi.yaml` — Jinja templating is supported.
- If you prefer in-process usage, you can create another variant inside the API repo that imports facades directly.

