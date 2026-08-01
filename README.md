# Irish Tax Hub MCP server

FastMCP server exposing a curated, read-only toolset backed by the Irish Tax Hub API.

## Hosted endpoints

- Production: `https://mcp-prod.aws.irishtaxhub.ie/mcp`
- Stage: `https://mcp-stage.aws.irishtaxhub.ie/mcp`

The hosted service uses stateless Streamable HTTP. For local MCP clients, run the same server over
standard input/output as described below.

## Tools

| Tool | Purpose |
|---|---|
| `calculate_tax` | Run one of the supported Irish tax calculators |
| `get_calculator_schema` | Return the input schema for a calculator |
| `list_calculators` | List calculator names and descriptions |
| `get_tax_constants` | Return tax constants for a supported year |
| `get_key_dates` | Return Irish tax deadlines and key dates |
| `search_revenue_documents` | Search Revenue Tax and Duty Manuals |
| `get_revenue_document_text` | Retrieve the text of a Revenue document |
| `list_revenue_document_categories` | List Revenue document categories |
| `get_revenue_ebrief_changelog` | Return the latest Revenue eBrief changes |
| `search_tax_treaties` | Search Ireland's double-taxation treaty corpus |
| `get_tax_treaty_text` | Retrieve treaty, protocol, or MLI text |
| `list_tax_treaty_countries` | List countries in the treaty corpus |
| `get_calculator_stats` | Return usage statistics for a calculator |

Tools are deliberately curated rather than generated dynamically. The OpenAPI document is used to
validate calculator requests, while stable tool names and descriptions form the MCP interface.

## Install

Python 3.11 and Poetry are recommended:

```bash
poetry install
```

An editable pip installation also works:

```bash
pip install -e .
```

## Configure

The server reads these environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `IRISHTAXHUB_BASE_URL` | `http://localhost:5000` | Irish Tax Hub API base URL |
| `IRISHTAXHUB_OPENAPI` | `<base-url>/openapi.json` | OpenAPI file path or URL used for validation |
| `IRISHTAXHUB_API_KEY` | unset | Optional API key forwarded to the API |
| `IRISHTAXHUB_TIMEOUT` | `30` | HTTP timeout in seconds |

For production-backed local use:

```bash
export IRISHTAXHUB_BASE_URL="https://prod.aws.irishtaxhub.ie"
export IRISHTAXHUB_OPENAPI="https://prod.aws.irishtaxhub.ie/openapi.json"
poetry run irishtaxhub-mcp
```

For a locally running API, the defaults are sufficient. You can also run the module or FastMCP
entrypoint directly:

```bash
python -m irishtaxhub_mcp.server
fastmcp run src/irishtaxhub_mcp/server.py
```

## MCP client configuration

Example local standard-input/output configuration:

```json
{
  "mcpServers": {
    "irishtaxhub": {
      "command": "poetry",
      "args": ["run", "irishtaxhub-mcp"],
      "cwd": "/absolute/path/to/irishtaxhub-mcp",
      "env": {
        "IRISHTAXHUB_BASE_URL": "https://prod.aws.irishtaxhub.ie",
        "IRISHTAXHUB_OPENAPI": "https://prod.aws.irishtaxhub.ie/openapi.json"
      }
    }
  }
}
```

Restart the client after changing its MCP configuration.

## Examples

Discover the available calculators, inspect the selected input schema, and then calculate:

```json
{"tool": "list_calculators", "arguments": {}}
```

```json
{
  "tool": "get_calculator_schema",
  "arguments": {"calculator_name": "refund"}
}
```

```json
{
  "tool": "calculate_tax",
  "arguments": {
    "calculator_name": "refund",
    "inputs": {
      "marital_status": "single",
      "year": 2025,
      "employment_income": {"income": 50000, "tax_paid": 18000}
    }
  }
}
```

Search the Revenue and treaty corpora:

```json
{"tool": "search_revenue_documents", "arguments": {"query": "principal private residence"}}
```

```json
{"tool": "search_tax_treaties", "arguments": {"query": "employment income", "country": "France"}}
```

## Development

```bash
poetry run black --check .
poetry run isort --check-only .
poetry run flake8 .
poetry run pytest
```

The implementation calls the deployed HTTP API rather than importing API internals, keeping this
service small and independently deployable. `src/irishtaxhub_mcp/asgi.py` provides the ASGI
entrypoint used by the Lambda Web Adapter deployment.

## Claude PR review

`.github/workflows/claude-pr-review.yml` can review pull requests when the repository has a valid
`CLAUDE_CODE_OAUTH_TOKEN` secret. Generate a replacement with `claude setup-token` when required,
then update it with:

```bash
gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo jhurleyai/irishtaxhub-mcp
```
