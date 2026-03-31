import logging
import os

from mangum import Mangum

from irishtaxhub_mcp.server import mcp

# Configure logging using env LOG_LEVEL (default INFO)
_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
_level = getattr(logging, _level_name, logging.INFO)

if not logging.getLogger().handlers:
    logging.basicConfig(level=_level)
else:
    logging.getLogger().setLevel(_level)

logger = logging.getLogger(__name__)

_api_stage = os.getenv("API_GATEWAY_STAGE", "stage")


def handler(event, context):
    """AWS Lambda entrypoint using Mangum to adapt FastMCP ASGI to API Gateway."""
    logger.info(
        "Lambda invocation - Request ID: %s",
        getattr(context, "aws_request_id", "unknown"),
    )
    # Create a fresh ASGI app per invocation because FastMCP's
    # StreamableHTTPSessionManager only supports a single lifespan cycle.
    asgi_app = mcp.http_app()
    mangum_handler = Mangum(asgi_app, api_gateway_base_path=f"/{_api_stage}")
    return mangum_handler(event, context)
