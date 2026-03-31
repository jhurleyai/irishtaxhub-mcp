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

module "api_lambda" {
  source           = "../../modules/api_lambda"
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

  create_domain         = true
  domain_name           = var.stage_domain
  certificate_validated = var.certificate_validated
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
