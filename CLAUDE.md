# CLAUDE.md — irishtaxhub-mcp

## What this is

MCP server that wraps the Irish Tax Hub API, exposing tax calculators, Revenue documents, tax constants, and key dates as MCP tools for AI agents.

## Tech stack

- Python 3.11+, FastMCP v2, Pydantic, httpx
- Poetry for dependency management
- Deployed as AWS Lambda behind API Gateway + CloudFront

## Dev commands

```bash
poetry install                        # Install dependencies
poetry run pytest -v                  # Run tests
poetry run black --check --diff .     # Check formatting
poetry run isort --check-only --diff . # Check import sorting
poetry run flake8 .                   # Lint
```

**Before committing, always run:**
```bash
poetry run black .
poetry run isort .
```

CI runs black, isort, flake8, and pytest on every PR. All must pass.

## Code style

- **black** (line-length 100, target py311)
- **isort** (profile "black", line-length 100)
- **flake8** for linting

## Architecture

- `src/irishtaxhub_mcp/server.py` — MCP tool definitions (the main file)
- `src/irishtaxhub_mcp/client.py` — HTTP client for the Irish Tax Hub API
- `src/irishtaxhub_mcp/openapi.py` — OpenAPI spec loader, schema extraction, validation
- `src/irishtaxhub_mcp/settings.py` — Config from environment variables
- `src/irishtaxhub_mcp/asgi.py` — ASGI entrypoint for uvicorn/Lambda
- `lambda_handler.py` — AWS Lambda handler (Mangum)
- `tests/test_server.py` — Tool registration and ASGI app tests

## Environment variables

- `IRISHTAXHUB_BASE_URL` — API base URL (default: `http://localhost:5000`)
- `IRISHTAXHUB_API_KEY` — Bearer token for API auth
- `IRISHTAXHUB_TIMEOUT` — Request timeout in seconds (default: 30)
- `IRISHTAXHUB_OPENAPI` — OpenAPI spec source (file path or URL; defaults to `{base_url}/openapi.json`)

## MCP tools

The server exposes 11 domain-specific tools. All calculator tools validate inputs against the OpenAPI schema before calling the API.

| Tool | Purpose |
|------|---------|
| `calculate_tax` | Run any of 20 tax calculators |
| `get_calculator_schema` | Get input schema for a calculator |
| `list_calculators` | List calculators with descriptions |
| `get_tax_constants` | Tax bands, rates, credits |
| `get_key_dates` | Revenue deadlines |
| `search_revenue_documents` | Search TDMs by keyword |
| `get_revenue_document_text` | Read a specific TDM |
| `list_revenue_document_categories` | List TDM categories |
| `get_revenue_ebrief_changelog` | Recent Revenue changes |
| `generate_net_income_summary` | AI tax summary |
| `get_calculator_stats` | Calculator usage stats |
