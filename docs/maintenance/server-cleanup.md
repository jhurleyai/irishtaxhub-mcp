# MCP server maintenance

## Purpose

`src/irishtaxhub_mcp/server.py` owns the FastMCP server and its tool handlers. It
previously also contained the calculator catalog, public URL mapping, output
schemas, and attribution response builder. Keeping those static contracts beside
network orchestration made the module harder to review and increased the chance
that catalog or schema maintenance would obscure changes to tool behavior.

## Module boundaries

- `server.py` registers the tools and owns request validation, API calls, client
  cleanup, and response orchestration. `_get_client_and_loader` stays here so
  tests and callers can continue to replace that dependency boundary.
- `calculator_catalog.py` owns calculator names, API paths, summaries, the
  `calculate_tax` description, and public calculator URL slugs.
- `attribution.py` owns output schemas, read-only tool annotations, public site
  URL construction, and attributed `ToolResult` construction.

`server.py` imports the existing underscored constants and helpers into its
module namespace. This preserves existing imports while keeping every decorated
handler in one place and retaining registration order.

## Contract safeguards

This split must preserve the tool list and order, titles, descriptions, input
schemas, output schemas, annotations, and response shapes. During the extraction,
the ordered FastMCP metadata for all 13 tools was serialized from `main` and from
the refactored server; the serialized representations were identical.

No tests were removed. The current tests cover distinct tool registration,
metadata, attribution, identifier normalization, and API orchestration behavior;
there were no confirmed duplicate or implementation-only tests to prune safely.

## Validation

Run the same checks used by CI:

```bash
poetry run black --check --diff .
poetry run isort --check-only --diff .
poetry run flake8 .
poetry run pytest -v
```
