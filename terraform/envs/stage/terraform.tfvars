name   = "irishtaxhub-mcp"
region = "eu-west-1"

lambda_s3_bucket       = "artifacts-irishtaxhub-mcp"
lambda_s3_key          = "irishtaxhub-mcp/stage/irishtaxhub-mcp.zip"
lambda_memory_mb       = 512
lambda_timeout_seconds = 29
python_runtime         = "python3.11"

log_retention_days = 30

env_vars = {
  APP_ENV   = "development"
  LOG_LEVEL = "DEBUG"
}

stage_domain = ""

# Streaming / MCP support (Lambda Web Adapter for SSE)
lambda_web_adapter_layer_arn = "arn:aws:lambda:eu-west-1:753240598075:layer:LambdaAdapterLayerX86:25"
create_streaming_domain      = true
streaming_domain_name        = "mcp-stage.aws.irishtaxhub.ie"
