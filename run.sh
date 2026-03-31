#!/bin/bash
exec python -m uvicorn irishtaxhub_mcp.asgi:app --host 0.0.0.0 --port 8080
