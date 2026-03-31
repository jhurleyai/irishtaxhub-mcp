name   = "irishtaxhub-mcp"
region = "eu-west-1"

lambda_s3_bucket       = "artifacts-irishtaxhub-mcp"
lambda_s3_key          = "irishtaxhub-mcp/prod/irishtaxhub-mcp.zip"
lambda_memory_mb       = 512
lambda_timeout_seconds = 29
python_runtime         = "python3.11"

log_retention_days = 90

env_vars = {
  APP_ENV   = "production"
  LOG_LEVEL = "INFO"
}

prod_domain = "mcp-prod.aws.irishtaxhub.ie"
