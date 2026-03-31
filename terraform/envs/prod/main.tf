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
  environment      = "prod"
  region           = var.region
  lambda_s3_bucket = var.lambda_s3_bucket
  lambda_s3_key    = var.lambda_s3_key

  lambda_memory_mb       = var.lambda_memory_mb
  lambda_timeout_seconds = var.lambda_timeout_seconds

  env_vars = merge(
    var.env_vars,
    {
      IRISHTAXHUB_BASE_URL = "https://prod.aws.irishtaxhub.ie"
    }
  )

  tags = {
    Project     = var.name
    Environment = "prod"
  }

  create_domain         = true
  domain_name           = var.prod_domain
  certificate_validated = var.certificate_validated
}

output "prod_api_url" {
  value = module.api_lambda.api_endpoint
}

output "prod_custom_domain" {
  value = module.api_lambda.custom_domain_url
}

output "prod_dns_setup" {
  value = module.api_lambda.dns_setup_instructions
}
