terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.13.0"
    }
  }
}

provider "aws" {
  region = var.region
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

module "api_lambda" {
  source = "../../modules/api_lambda"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  name             = var.name
  environment      = "stage"
  region           = var.region
  lambda_s3_bucket = var.lambda_s3_bucket
  lambda_s3_key    = var.lambda_s3_key

  lambda_memory_mb       = var.lambda_memory_mb
  lambda_timeout_seconds = var.lambda_timeout_seconds

  env_vars = merge(
    var.env_vars,
    {
      IRISHTAXHUB_BASE_URL = "https://stage.aws.irishtaxhub.ie"
    }
  )

  tags = {
    Project     = var.name
    Environment = "stage"
  }

  create_domain         = false
  domain_name           = var.stage_domain
  certificate_validated = var.certificate_validated

  # Streaming / MCP support
  lambda_web_adapter_layer_arn    = var.lambda_web_adapter_layer_arn
  create_streaming_domain         = var.create_streaming_domain
  streaming_domain_name           = var.streaming_domain_name
  streaming_certificate_validated = var.streaming_certificate_validated
}

output "stage_api_url" {
  value = module.api_lambda.api_endpoint
}

output "stage_custom_domain" {
  value = module.api_lambda.custom_domain_url
}

output "stage_dns_setup" {
  value = module.api_lambda.dns_setup_instructions
}

output "stage_mcp_function_url" {
  value       = module.api_lambda.lambda_function_url
  description = "Lambda Function URL for MCP (use this directly or via custom domain)"
}

output "stage_streaming_custom_domain" {
  value       = module.api_lambda.streaming_custom_domain_url
  description = "Custom domain URL for MCP streaming"
}

output "stage_streaming_dns_instructions" {
  value       = module.api_lambda.streaming_dns_instructions
  description = "DNS instructions for streaming domain"
}
