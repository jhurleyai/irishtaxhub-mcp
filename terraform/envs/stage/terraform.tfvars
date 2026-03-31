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

stage_domain = "mcp-stage.aws.irishtaxhub.ie"
