# MCP Server AWS Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the irishtaxhub-mcp server to AWS Lambda with stage and prod environments, matching the deployment patterns of irishtaxhubapi.

**Architecture:** FastMCP's `http_app()` returns a Starlette ASGI app which we wrap with Mangum for Lambda compatibility. API Gateway HTTP v2 routes requests to the Lambda. Terraform manages infrastructure with separate state per environment. GitHub Actions handles CI/CD with OIDC auth.

**Tech Stack:** FastMCP 2.x, Mangum, Terraform, GitHub Actions, AWS Lambda, API Gateway v2, ACM

---

### Task 1: Create feature branch

**Files:** None

- [ ] **Step 1: Create and push the feature branch**

```bash
cd /Users/jameshurley/projects/irishtaxhub-mcp
git checkout -b feat/aws-deployment
```

- [ ] **Step 2: Verify branch**

Run: `git branch --show-current`
Expected: `feat/aws-deployment`

---

### Task 2: Add Mangum dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Add mangum to pyproject.toml**

Add `mangum` to the `[tool.poetry.dependencies]` section:

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastmcp = ">=2.0"
httpx = ">=0.27"
pydantic = ">=2.6"
python-dotenv = ">=1.0.1"
PyYAML = ">=6.0"
Jinja2 = ">=3.1"
jsonschema = ">=4.22"
mangum = ">=0.19"
```

- [ ] **Step 2: Install and regenerate lock/requirements**

```bash
cd /Users/jameshurley/projects/irishtaxhub-mcp
poetry lock --no-update
poetry install
poetry export -f requirements.txt --without-hashes -o requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml poetry.lock requirements.txt
git commit -m "feat: add mangum dependency for Lambda ASGI bridge"
```

---

### Task 3: Create Lambda handler

**Files:**
- Create: `lambda_handler.py`

- [ ] **Step 1: Create lambda_handler.py**

```python
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

# FastMCP http_app() returns a Starlette ASGI app
_asgi_app = mcp.http_app()

# Wrap with Mangum for Lambda + API Gateway
_api_stage = os.getenv("API_GATEWAY_STAGE", "stage")
_mangum_handler = Mangum(_asgi_app, api_gateway_base_path=f"/{_api_stage}")


def handler(event, context):
    """AWS Lambda entrypoint using Mangum to adapt FastMCP ASGI to API Gateway."""
    logger.info(
        "Lambda invocation - Request ID: %s",
        getattr(context, "aws_request_id", "unknown"),
    )
    return _mangum_handler(event, context)
```

- [ ] **Step 2: Verify the handler can be imported locally**

```bash
cd /Users/jameshurley/projects/irishtaxhub-mcp
python -c "from lambda_handler import handler; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add lambda_handler.py
git commit -m "feat: add Lambda handler wrapping FastMCP with Mangum"
```

---

### Task 4: Create Lambda packaging script

**Files:**
- Create: `scripts/package_lambda.sh`

- [ ] **Step 1: Create scripts directory and package_lambda.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Lambda packaging script that uses Docker to ensure Linux compatibility

APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$APP_ROOT/build"
DIST_DIR="$APP_ROOT/dist"
ZIP_NAME="irishtaxhub-mcp.zip"

rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# Use Docker to build Lambda-compatible package for x86_64 architecture
echo "> Using Docker to build Lambda-compatible package (x86_64)"
docker run --rm --entrypoint="" --platform linux/amd64 \
    -v "$APP_ROOT:/var/task" \
    -v "$BUILD_DIR:/var/build" \
    public.ecr.aws/lambda/python:3.11 \
    /bin/bash -c "pip install -r /var/task/requirements.txt -t /var/build"

# Copy application code
echo "> Copying application code"
cp -R "$APP_ROOT/src/irishtaxhub_mcp" "$BUILD_DIR/"
cp "$APP_ROOT/lambda_handler.py" "$BUILD_DIR/"

# Create zip
echo "> Creating zip at $DIST_DIR/$ZIP_NAME"
(cd "$BUILD_DIR" && zip -rq "$DIST_DIR/$ZIP_NAME" .)

echo "> Package ready: $DIST_DIR/$ZIP_NAME"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/package_lambda.sh
```

- [ ] **Step 3: Add build/dist to .gitignore**

Append to `.gitignore`:

```
build/
dist/
```

- [ ] **Step 4: Commit**

```bash
git add scripts/package_lambda.sh .gitignore
git commit -m "feat: add Lambda packaging script"
```

---

### Task 5: Create Terraform api_lambda module (simplified)

**Files:**
- Create: `terraform/modules/api_lambda/main.tf`
- Create: `terraform/modules/api_lambda/variables.tf`
- Create: `terraform/modules/api_lambda/outputs.tf`

- [ ] **Step 1: Create terraform/modules/api_lambda/main.tf**

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  full_name = "${var.name}-${var.environment}"
}

resource "aws_iam_role" "lambda_role" {
  name               = "${local.full_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.full_name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_lambda_function" "this" {
  function_name = local.full_name
  role          = aws_iam_role.lambda_role.arn
  runtime       = var.python_runtime
  handler       = "lambda_handler.handler"

  s3_bucket        = var.lambda_s3_bucket
  s3_key           = var.lambda_s3_key
  source_code_hash = var.lambda_s3_key

  memory_size = var.lambda_memory_mb
  timeout     = var.lambda_timeout_seconds

  environment {
    variables = merge(
      var.env_vars,
      {
        API_GATEWAY_STAGE = coalesce(var.api_stage_name, var.environment)
      }
    )
  }

  tags = var.tags
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${local.full_name}-api"
  protocol_type = "HTTP"
  tags          = var.tags
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigwv2/${aws_apigatewayv2_api.http.name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_apigatewayv2_stage" "env" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = coalesce(var.api_stage_name, var.environment)
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      httpMethod              = "$context.httpMethod"
      path                    = "$context.path"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }

  tags = var.tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.this.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "root" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

############################
# Optional Custom Domain
############################

module "custom_domain" {
  source = "../custom_domain"

  create_domain = var.create_domain
  domain_name   = var.domain_name
  api_id        = aws_apigatewayv2_api.http.id
  api_stage_id  = aws_apigatewayv2_stage.env.id
  tags          = var.tags
}
```

- [ ] **Step 2: Create terraform/modules/api_lambda/variables.tf**

```hcl
variable "name" {
  description = "Base name for resources (e.g., irishtaxhub-mcp)"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g., stage or prod)"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.region))
    error_message = "Region must be a valid AWS region format (e.g., us-east-1, eu-west-1)."
  }
}

variable "lambda_s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package (zip)"
  type        = string
}

variable "lambda_s3_key" {
  description = "S3 key (path) to the Lambda deployment package (zip)"
  type        = string
}

variable "lambda_memory_mb" {
  description = "Lambda memory in MB"
  type        = number
  default     = 512

  validation {
    condition     = var.lambda_memory_mb >= 128 && var.lambda_memory_mb <= 10240
    error_message = "Lambda memory must be between 128 MB and 10240 MB."
  }
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 29

  validation {
    condition     = var.lambda_timeout_seconds > 0 && var.lambda_timeout_seconds <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "env_vars" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "create_domain" {
  description = "Whether to create a custom domain, ACM cert, and API mapping"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Fully qualified domain name for the API custom domain"
  type        = string
  default     = ""
}

variable "python_runtime" {
  description = "Python runtime version for Lambda"
  type        = string
  default     = "python3.11"

  validation {
    condition     = can(regex("^python3\\.(8|9|10|11|12|13)$", var.python_runtime))
    error_message = "Python runtime must be a valid version (python3.8 through python3.13)."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch Logs retention value."
  }
}

variable "api_stage_name" {
  description = "API Gateway stage name"
  type        = string
  default     = null

  validation {
    condition     = var.api_stage_name == null || can(regex("^[a-zA-Z0-9-_]+$", var.api_stage_name))
    error_message = "API stage name must contain only alphanumeric characters, hyphens, and underscores."
  }
}
```

- [ ] **Step 3: Create terraform/modules/api_lambda/outputs.tf**

```hcl
output "api_endpoint" {
  description = "HTTP API endpoint URL for this environment"
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "lambda_function_name" {
  value       = aws_lambda_function.this.function_name
  description = "Deployed Lambda function name"
}

output "lambda_arn" {
  value       = aws_lambda_function.this.arn
  description = "Deployed Lambda function ARN"
}

output "stage_name" {
  value       = aws_apigatewayv2_stage.env.name
  description = "API stage name"
}

output "custom_domain_name" {
  description = "Custom domain name (if created)"
  value       = module.custom_domain.custom_domain_name
}

output "custom_domain_url" {
  description = "Custom domain base URL (if created)"
  value       = module.custom_domain.custom_domain_url
}

output "acm_dns_validation_records" {
  description = "DNS records required for ACM validation when using external DNS"
  value       = module.custom_domain.acm_dns_validation_records
}

output "apigw_domain_target" {
  description = "API Gateway custom domain target for CNAME at external DNS"
  value       = module.custom_domain.apigw_domain_target
}

output "certificate_arn" {
  description = "ACM certificate ARN (if created)"
  value       = module.custom_domain.certificate_arn
}

output "certificate_status" {
  description = "ACM certificate validation status"
  value       = module.custom_domain.certificate_status
}

output "apigw_domain_hosted_zone_id" {
  description = "API Gateway custom domain hosted zone ID for alias records"
  value       = module.custom_domain.apigw_domain_hosted_zone_id
}

output "dns_setup_instructions" {
  description = "Instructions for setting up DNS records at external provider"
  value       = module.custom_domain.dns_setup_instructions
}
```

- [ ] **Step 4: Commit**

```bash
git add terraform/modules/api_lambda/
git commit -m "feat: add Terraform api_lambda module"
```

---

### Task 6: Create Terraform custom_domain module

**Files:**
- Create: `terraform/modules/custom_domain/main.tf`
- Create: `terraform/modules/custom_domain/variables.tf`
- Create: `terraform/modules/custom_domain/outputs.tf`

- [ ] **Step 1: Create terraform/modules/custom_domain/main.tf**

Copy the exact same module from irishtaxhubapi — it's reusable as-is:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

resource "aws_acm_certificate" "cert" {
  count             = var.create_domain ? 1 : 0
  domain_name       = var.domain_name
  validation_method = "DNS"
  tags              = var.tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_apigatewayv2_domain_name" "custom" {
  count       = var.create_domain ? 1 : 0
  domain_name = var.domain_name

  domain_name_configuration {
    certificate_arn = aws_acm_certificate.cert[0].arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = var.tags

  depends_on = [aws_acm_certificate.cert]
}

resource "aws_apigatewayv2_api_mapping" "custom" {
  count       = var.create_domain ? 1 : 0
  api_id      = var.api_id
  domain_name = aws_apigatewayv2_domain_name.custom[0].id
  stage       = var.api_stage_id
}
```

- [ ] **Step 2: Create terraform/modules/custom_domain/variables.tf**

```hcl
variable "create_domain" {
  description = "Whether to create a custom domain, ACM cert, and API mapping"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Fully qualified domain name for the API custom domain"
  type        = string
  default     = ""

  validation {
    condition     = var.domain_name == "" || can(regex("^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z]{2,}$", var.domain_name))
    error_message = "Domain name must be a valid FQDN format."
  }
}

variable "api_id" {
  description = "API Gateway HTTP API ID to map the custom domain to"
  type        = string
}

variable "api_stage_id" {
  description = "API Gateway stage ID to map the custom domain to"
  type        = string
}

variable "tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}
```

- [ ] **Step 3: Create terraform/modules/custom_domain/outputs.tf**

```hcl
output "custom_domain_name" {
  description = "Custom domain name (if created)"
  value       = try(aws_apigatewayv2_domain_name.custom[0].domain_name, null)
}

output "custom_domain_url" {
  description = "Custom domain base URL (if created)"
  value       = try("https://${aws_apigatewayv2_domain_name.custom[0].domain_name}", null)
}

output "acm_dns_validation_records" {
  description = "DNS records required for ACM validation when using external DNS"
  value = try({
    for dvo in aws_acm_certificate.cert[0].domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }, {})
}

output "apigw_domain_target" {
  description = "API Gateway custom domain target for CNAME at external DNS"
  value       = try(aws_apigatewayv2_domain_name.custom[0].domain_name_configuration[0].target_domain_name, null)
}

output "apigw_domain_hosted_zone_id" {
  description = "API Gateway custom domain hosted zone ID for alias records"
  value       = try(aws_apigatewayv2_domain_name.custom[0].domain_name_configuration[0].hosted_zone_id, null)
}

output "dns_setup_instructions" {
  description = "Complete DNS setup instructions for external DNS provider"
  value = var.create_domain ? {
    step1_certificate_validation = {
      description = "Create this CNAME record for certificate validation:"
      records = {
        for dvo in aws_acm_certificate.cert[0].domain_validation_options : dvo.domain_name => {
          type  = dvo.resource_record_type
          name  = dvo.resource_record_name
          value = dvo.resource_record_value
          note  = "Required for SSL certificate validation"
        }
      }
    }
    step2_domain_mapping = {
      description = "After certificate validates, create this CNAME record for domain mapping:"
      record = try({
        type  = "CNAME"
        name  = var.domain_name
        value = aws_apigatewayv2_domain_name.custom[0].domain_name_configuration[0].target_domain_name
        note  = "Points your domain to API Gateway"
        }, {
        type  = "CNAME"
        name  = var.domain_name
        value = "PENDING - Certificate must validate first"
        note  = "Will be available after certificate validation completes"
      })
    }
    current_status = {
      certificate_status = try(aws_acm_certificate.cert[0].status, "UNKNOWN")
      domain_ready       = try(aws_apigatewayv2_domain_name.custom[0] != null, false)
    }
  } : null
}

output "certificate_arn" {
  description = "ACM certificate ARN (if created)"
  value       = try(aws_acm_certificate.cert[0].arn, null)
}

output "certificate_status" {
  description = "ACM certificate validation status"
  value       = try(aws_acm_certificate.cert[0].status, null)
}
```

- [ ] **Step 4: Commit**

```bash
git add terraform/modules/custom_domain/
git commit -m "feat: add Terraform custom_domain module"
```

---

### Task 7: Create Terraform stage environment

**Files:**
- Create: `terraform/envs/stage/main.tf`
- Create: `terraform/envs/stage/variables.tf`
- Create: `terraform/envs/stage/backend.tf`
- Create: `terraform/envs/stage/terraform.tfvars`

- [ ] **Step 1: Create terraform/envs/stage/backend.tf**

```hcl
terraform {
  backend "s3" {}
}
```

- [ ] **Step 2: Create terraform/envs/stage/variables.tf**

```hcl
variable "name" {
  description = "Base name for resources"
  type        = string
  default     = "irishtaxhub-mcp"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "lambda_s3_bucket" {
  description = "S3 bucket containing the Lambda deployment zip"
  type        = string
}

variable "lambda_s3_key" {
  description = "S3 key/path for the Lambda deployment zip"
  type        = string
}

variable "lambda_memory_mb" {
  description = "Lambda function memory allocation in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout_seconds" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 29
}

variable "python_runtime" {
  description = "Python runtime version for Lambda"
  type        = string
  default     = "python3.11"
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
}

variable "env_vars" {
  description = "Environment variables for Lambda"
  type        = map(string)
  default     = {}
}

variable "stage_domain" {
  description = "Stage environment domain name"
  type        = string
  default     = "mcp-stage.aws.irishtaxhub.ie"

  validation {
    condition     = can(regex("^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z]{2,}$", var.stage_domain))
    error_message = "Stage domain must be a valid FQDN format."
  }
}
```

- [ ] **Step 3: Create terraform/envs/stage/main.tf**

```hcl
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

  create_domain = true
  domain_name   = var.stage_domain
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
```

- [ ] **Step 4: Create terraform/envs/stage/terraform.tfvars**

```hcl
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
```

- [ ] **Step 5: Commit**

```bash
git add terraform/envs/stage/
git commit -m "feat: add Terraform stage environment config"
```

---

### Task 8: Create Terraform prod environment

**Files:**
- Create: `terraform/envs/prod/main.tf`
- Create: `terraform/envs/prod/variables.tf`
- Create: `terraform/envs/prod/backend.tf`
- Create: `terraform/envs/prod/terraform.tfvars`

- [ ] **Step 1: Create terraform/envs/prod/backend.tf**

```hcl
terraform {
  backend "s3" {}
}
```

- [ ] **Step 2: Create terraform/envs/prod/variables.tf**

```hcl
variable "name" {
  description = "Base name for resources"
  type        = string
  default     = "irishtaxhub-mcp"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "lambda_s3_bucket" {
  description = "S3 bucket containing the Lambda deployment zip"
  type        = string
}

variable "lambda_s3_key" {
  description = "S3 key/path for the Lambda deployment zip"
  type        = string
}

variable "lambda_memory_mb" {
  description = "Lambda function memory allocation in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout_seconds" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 29
}

variable "python_runtime" {
  description = "Python runtime version for Lambda"
  type        = string
  default     = "python3.11"
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 90
}

variable "env_vars" {
  description = "Environment variables for Lambda"
  type        = map(string)
  default     = {}
}

variable "prod_domain" {
  description = "Production environment domain name"
  type        = string
  default     = "mcp-prod.aws.irishtaxhub.ie"

  validation {
    condition     = can(regex("^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z]{2,}$", var.prod_domain))
    error_message = "Prod domain must be a valid FQDN format."
  }
}
```

- [ ] **Step 3: Create terraform/envs/prod/main.tf**

```hcl
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

  create_domain = true
  domain_name   = var.prod_domain
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
```

- [ ] **Step 4: Create terraform/envs/prod/terraform.tfvars**

```hcl
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
```

- [ ] **Step 5: Commit**

```bash
git add terraform/envs/prod/
git commit -m "feat: add Terraform prod environment config"
```

---

### Task 9: Validate Terraform locally

**Files:** None

- [ ] **Step 1: Validate stage config**

```bash
cd /Users/jameshurley/projects/irishtaxhub-mcp/terraform/envs/stage
terraform init -backend=false
terraform validate
```

Expected: `Success! The configuration is valid.`

- [ ] **Step 2: Validate prod config**

```bash
cd /Users/jameshurley/projects/irishtaxhub-mcp/terraform/envs/prod
terraform init -backend=false
terraform validate
```

Expected: `Success! The configuration is valid.`

- [ ] **Step 3: Check formatting**

```bash
cd /Users/jameshurley/projects/irishtaxhub-mcp
terraform fmt -check -recursive terraform/
```

Expected: No output (all files formatted correctly)

---

### Task 10: Create AWS prerequisites setup script

**Files:**
- Create: `scripts/setup_aws_prerequisites.sh`
- Create: `scripts/aws_config.env`

- [ ] **Step 1: Create scripts/aws_config.env**

```bash
# AWS Configuration for irishtaxhub-mcp
PROJECT_NAME="irishtaxhub-mcp"
AWS_REGION="eu-west-1"
ARTIFACTS_BUCKET="artifacts-irishtaxhub-mcp"
TF_STATE_BUCKET="tf-state-irishtaxhub-mcp"
TF_STATE_DYNAMODB_TABLE="tf-locks-irishtaxhub-mcp"
GITHUB_REPO="jhurleyai/irishtaxhub-mcp"
GITHUB_ORG="jhurleyai"
ROLE_NAME="GitHubActions-irishtaxhub-mcp"
```

- [ ] **Step 2: Create scripts/setup_aws_prerequisites.sh**

Same structure as irishtaxhubapi but with irishtaxhub-mcp defaults:

```bash
#!/bin/bash
set -e

# AWS Prerequisites Setup Script for IrishTaxHub MCP Server

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/aws_config.env"

if [ -f "$CONFIG_FILE" ]; then
    log_info "Loading configuration from $CONFIG_FILE"
    source "$CONFIG_FILE"
fi

PROJECT_NAME="${PROJECT_NAME:-irishtaxhub-mcp}"
AWS_REGION="${AWS_REGION:-eu-west-1}"
ARTIFACTS_BUCKET="${ARTIFACTS_BUCKET:-artifacts-${PROJECT_NAME}}"
TF_STATE_BUCKET="${TF_STATE_BUCKET:-tf-state-${PROJECT_NAME}}"
TF_STATE_DYNAMODB_TABLE="${TF_STATE_DYNAMODB_TABLE:-tf-locks-${PROJECT_NAME}}"

check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install AWS CLI first."
        exit 1
    fi
    log_info "AWS CLI version: $(aws --version)"
}

check_aws_credentials() {
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid."
        log_info "Run 'aws configure' to set up your credentials."
        exit 1
    fi
    local caller_identity=$(aws sts get-caller-identity)
    if command -v jq &> /dev/null; then
        log_success "AWS credentials valid for: $(echo $caller_identity | jq -r '.Arn')"
    else
        log_success "AWS credentials valid"
    fi
}

bucket_exists() { aws s3 ls "s3://$1" &> /dev/null; }
table_exists() { aws dynamodb describe-table --table-name "$1" --region "$AWS_REGION" &> /dev/null 2>&1; }

create_artifacts_bucket() {
    log_info "Creating S3 artifacts bucket: $ARTIFACTS_BUCKET"
    if bucket_exists "$ARTIFACTS_BUCKET"; then
        log_warning "S3 bucket '$ARTIFACTS_BUCKET' already exists"
        return 0
    fi
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3 mb "s3://$ARTIFACTS_BUCKET"
    else
        aws s3 mb "s3://$ARTIFACTS_BUCKET" --region "$AWS_REGION"
    fi
    aws s3api put-bucket-versioning --bucket "$ARTIFACTS_BUCKET" --versioning-configuration Status=Enabled
    aws s3api put-public-access-block --bucket "$ARTIFACTS_BUCKET" \
        --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    log_success "Created artifacts bucket: $ARTIFACTS_BUCKET"
}

create_tf_state_bucket() {
    log_info "Creating S3 Terraform state bucket: $TF_STATE_BUCKET"
    if bucket_exists "$TF_STATE_BUCKET"; then
        log_warning "S3 bucket '$TF_STATE_BUCKET' already exists"
        return 0
    fi
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3 mb "s3://$TF_STATE_BUCKET"
    else
        aws s3 mb "s3://$TF_STATE_BUCKET" --region "$AWS_REGION"
    fi
    aws s3api put-bucket-versioning --bucket "$TF_STATE_BUCKET" --versioning-configuration Status=Enabled
    aws s3api put-bucket-encryption --bucket "$TF_STATE_BUCKET" \
        --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
    aws s3api put-public-access-block --bucket "$TF_STATE_BUCKET" \
        --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    log_success "Created Terraform state bucket: $TF_STATE_BUCKET"
}

create_tf_locks_table() {
    log_info "Creating DynamoDB table for Terraform locks: $TF_STATE_DYNAMODB_TABLE"
    if table_exists "$TF_STATE_DYNAMODB_TABLE"; then
        log_warning "DynamoDB table '$TF_STATE_DYNAMODB_TABLE' already exists"
        return 0
    fi
    aws dynamodb create-table \
        --table-name "$TF_STATE_DYNAMODB_TABLE" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION"
    log_info "Waiting for DynamoDB table to be active..."
    aws dynamodb wait table-exists --table-name "$TF_STATE_DYNAMODB_TABLE" --region "$AWS_REGION"
    log_success "Created DynamoDB locks table: $TF_STATE_DYNAMODB_TABLE"
}

generate_backend_configs() {
    log_info "Generating backend configuration files..."
    local stage_backend="$SCRIPT_DIR/../terraform/envs/stage/backend.hcl"
    local prod_backend="$SCRIPT_DIR/../terraform/envs/prod/backend.hcl"

    cat > "$stage_backend" << EOF
bucket         = "$TF_STATE_BUCKET"
key            = "state/irishtaxhub-mcp/stage.tfstate"
region         = "$AWS_REGION"
encrypt        = true
dynamodb_table = "$TF_STATE_DYNAMODB_TABLE"
EOF

    cat > "$prod_backend" << EOF
bucket         = "$TF_STATE_BUCKET"
key            = "state/irishtaxhub-mcp/prod.tfstate"
region         = "$AWS_REGION"
encrypt        = true
dynamodb_table = "$TF_STATE_DYNAMODB_TABLE"
EOF

    log_success "Generated backend configuration files"
}

print_summary() {
    echo ""
    log_success "AWS Prerequisites Setup Complete!"
    echo ""
    echo "Created Resources:"
    echo "   Artifacts bucket: $ARTIFACTS_BUCKET"
    echo "   Terraform state bucket: $TF_STATE_BUCKET"
    echo "   DynamoDB locks table: $TF_STATE_DYNAMODB_TABLE"
    echo "   Region: $AWS_REGION"
    echo ""
    echo "Next Steps:"
    echo "   1. Run: ./scripts/setup_github_oidc.sh"
    echo "   2. Set GitHub repository secrets:"
    echo "      ARTIFACTS_BUCKET = $ARTIFACTS_BUCKET"
    echo "      TF_STATE_BUCKET = $TF_STATE_BUCKET"
    echo "      TF_STATE_DYNAMODB_TABLE = $TF_STATE_DYNAMODB_TABLE"
    echo ""
}

main() {
    echo "Setting up AWS Prerequisites for IrishTaxHub MCP Server"
    echo "======================================================="
    echo ""
    check_aws_cli
    check_aws_credentials
    echo ""
    log_info "Configuration:"
    echo "   Project: $PROJECT_NAME"
    echo "   Region: $AWS_REGION"
    echo "   Artifacts bucket: $ARTIFACTS_BUCKET"
    echo "   TF state bucket: $TF_STATE_BUCKET"
    echo "   TF locks table: $TF_STATE_DYNAMODB_TABLE"
    echo ""
    read -p "Continue with this configuration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    echo ""
    create_artifacts_bucket
    create_tf_state_bucket
    create_tf_locks_table
    generate_backend_configs
    print_summary
}

if ! command -v jq &> /dev/null; then
    log_warning "jq not found. JSON output may not be formatted nicely."
fi

main "$@"
```

- [ ] **Step 3: Make executable**

```bash
chmod +x scripts/setup_aws_prerequisites.sh
```

- [ ] **Step 4: Commit**

```bash
git add scripts/setup_aws_prerequisites.sh scripts/aws_config.env
git commit -m "feat: add AWS prerequisites setup script"
```

---

### Task 11: Create GitHub OIDC setup script

**Files:**
- Create: `scripts/setup_github_oidc.sh`

- [ ] **Step 1: Create scripts/setup_github_oidc.sh**

Simplified from irishtaxhubapi — no DynamoDB, no Secrets Manager, no CloudFront permissions:

```bash
#!/bin/bash
set -e

# GitHub OIDC IAM Role Setup Script for IrishTaxHub MCP Server

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/aws_config.env"

if [ -f "$CONFIG_FILE" ]; then
    log_info "Loading configuration from $CONFIG_FILE"
    source "$CONFIG_FILE"
fi

PROJECT_NAME="${PROJECT_NAME:-irishtaxhub-mcp}"
AWS_REGION="${AWS_REGION:-eu-west-1}"
GITHUB_REPO="${GITHUB_REPO:-jhurleyai/irishtaxhub-mcp}"
GITHUB_ORG="${GITHUB_ORG:-jhurleyai}"
ROLE_NAME="${ROLE_NAME:-GitHubActions-${PROJECT_NAME}}"
OIDC_PROVIDER_ARN=""
ARTIFACTS_BUCKET="${ARTIFACTS_BUCKET:-artifacts-${PROJECT_NAME}}"
TF_STATE_BUCKET="${TF_STATE_BUCKET:-tf-state-${PROJECT_NAME}}"
TF_STATE_DYNAMODB_TABLE="${TF_STATE_DYNAMODB_TABLE:-tf-locks-${PROJECT_NAME}}"

check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found."
        exit 1
    fi
    log_info "AWS CLI version: $(aws --version)"
}

check_aws_credentials() {
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid."
        exit 1
    fi
    local caller_identity=$(aws sts get-caller-identity)
    if command -v jq &> /dev/null; then
        log_success "AWS credentials valid for: $(echo $caller_identity | jq -r '.Arn')"
    else
        log_success "AWS credentials valid"
    fi
}

get_aws_account_id() { aws sts get-caller-identity --query Account --output text; }

oidc_provider_exists() {
    aws iam get-open-id-connect-provider --open-id-connect-provider-arn "arn:aws:iam::$(get_aws_account_id):oidc-provider/token.actions.githubusercontent.com" &> /dev/null
}

role_exists() { aws iam get-role --role-name "$ROLE_NAME" &> /dev/null 2>&1; }

create_oidc_provider() {
    log_info "Creating GitHub OIDC provider..."
    if oidc_provider_exists; then
        log_warning "GitHub OIDC provider already exists"
        OIDC_PROVIDER_ARN="arn:aws:iam::$(get_aws_account_id):oidc-provider/token.actions.githubusercontent.com"
        return 0
    fi
    OIDC_PROVIDER_ARN=$(aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 1c58a3a8518e8759bf075b76b750d4f2df264fcd d89e3bd43d5d909b47a18977aa9d5ce36cee184c \
        --query 'OpenIDConnectProviderArn' \
        --output text)
    log_success "Created GitHub OIDC provider: $OIDC_PROVIDER_ARN"
}

create_trust_policy() {
    local account_id=$(get_aws_account_id)
    cat > /tmp/trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::${account_id}:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": [
                        "repo:${GITHUB_REPO}:*"
                    ]
                }
            }
        }
    ]
}
EOF
    log_info "Generated trust policy for repository: $GITHUB_REPO"
}

create_permissions_policy() {
    local account_id=$(get_aws_account_id)
    cat > /tmp/permissions-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaManagement",
            "Effect": "Allow",
            "Action": ["lambda:*"],
            "Resource": ["arn:aws:lambda:${AWS_REGION}:${account_id}:function:${PROJECT_NAME}-*"]
        },
        {
            "Sid": "APIGatewayFull",
            "Effect": "Allow",
            "Action": ["apigateway:*"],
            "Resource": "*"
        },
        {
            "Sid": "IAMComprehensive",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole", "iam:GetRole", "iam:DeleteRole",
                "iam:AttachRolePolicy", "iam:DetachRolePolicy",
                "iam:ListAttachedRolePolicies", "iam:ListRolePolicies",
                "iam:GetRolePolicy", "iam:PutRolePolicy", "iam:DeleteRolePolicy",
                "iam:ListInstanceProfilesForRole", "iam:PassRole",
                "iam:TagRole", "iam:UntagRole", "iam:UpdateAssumeRolePolicy",
                "iam:CreateServiceLinkedRole",
                "iam:GetServiceLinkedRoleDeletionStatus", "iam:DeleteServiceLinkedRole",
                "iam:CreatePolicy", "iam:GetPolicy", "iam:DeletePolicy",
                "iam:CreatePolicyVersion", "iam:DeletePolicyVersion",
                "iam:ListPolicyVersions", "iam:GetPolicyVersion",
                "iam:SetDefaultPolicyVersion",
                "iam:TagPolicy", "iam:UntagPolicy", "iam:GetAccountSummary"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CloudWatchLogsFull",
            "Effect": "Allow",
            "Action": ["logs:*"],
            "Resource": "*"
        },
        {
            "Sid": "ACMCertificates",
            "Effect": "Allow",
            "Action": ["acm:*"],
            "Resource": "*"
        },
        {
            "Sid": "S3ArtifactsBucket",
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject"],
            "Resource": ["arn:aws:s3:::${ARTIFACTS_BUCKET}/*"]
        },
        {
            "Sid": "S3TerraformState",
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
            "Resource": [
                "arn:aws:s3:::${TF_STATE_BUCKET}",
                "arn:aws:s3:::${TF_STATE_BUCKET}/*"
            ]
        },
        {
            "Sid": "DynamoDBStateLocking",
            "Effect": "Allow",
            "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"],
            "Resource": ["arn:aws:dynamodb:${AWS_REGION}:${account_id}:table/${TF_STATE_DYNAMODB_TABLE}"]
        }
    ]
}
EOF
    log_info "Generated permissions policy"
}

update_policy() {
    local account_id=$(get_aws_account_id)
    local policy_name="${ROLE_NAME}-Policy"
    local policy_arn="arn:aws:iam::${account_id}:policy/${policy_name}"

    log_info "Updating IAM policy: $policy_name"
    if ! aws iam get-policy --policy-arn "$policy_arn" &> /dev/null; then
        log_error "Policy does not exist: $policy_name"
        return 1
    fi
    create_permissions_policy

    local versions=$(aws iam list-policy-versions --policy-arn "$policy_arn" --query 'Versions[*].[VersionId,IsDefaultVersion]' --output json)
    local version_count=$(echo "$versions" | jq 'length')

    if [ "$version_count" -ge 5 ]; then
        log_warning "Policy has maximum versions (5). Deleting oldest non-default version..."
        local oldest_version=$(echo "$versions" | jq -r '.[] | select(.[1] == false) | .[0]' | head -1)
        if [ -n "$oldest_version" ]; then
            aws iam delete-policy-version --policy-arn "$policy_arn" --version-id "$oldest_version"
            log_success "Deleted old policy version: $oldest_version"
        fi
    fi

    local new_version=$(aws iam create-policy-version \
        --policy-arn "$policy_arn" \
        --policy-document file:///tmp/permissions-policy.json \
        --set-as-default \
        --query 'PolicyVersion.VersionId' \
        --output text)
    log_success "Updated policy to version: $new_version"
}

create_iam_role() {
    log_info "Setting up IAM role: $ROLE_NAME"
    create_trust_policy
    create_permissions_policy

    if role_exists; then
        log_warning "IAM role '$ROLE_NAME' already exists"
        log_info "Updating the attached policy with latest permissions..."
        update_policy
        rm -f /tmp/trust-policy.json /tmp/permissions-policy.json
        return 0
    fi

    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "GitHub Actions OIDC role for $PROJECT_NAME deployment" \
        --max-session-duration 3600

    local policy_name="${ROLE_NAME}-Policy"
    local policy_arn=$(aws iam create-policy \
        --policy-name "$policy_name" \
        --policy-document file:///tmp/permissions-policy.json \
        --description "Permissions for GitHub Actions to deploy $PROJECT_NAME" \
        --query 'Policy.Arn' \
        --output text)

    aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$policy_arn"

    log_success "Created IAM role: $ROLE_NAME"
    log_success "Created and attached policy: $policy_name"
    rm -f /tmp/trust-policy.json /tmp/permissions-policy.json
}

print_summary() {
    local account_id=$(get_aws_account_id)
    local role_arn="arn:aws:iam::${account_id}:role/${ROLE_NAME}"
    echo ""
    log_success "GitHub OIDC Setup Complete!"
    echo ""
    echo "Created Resources:"
    echo "   OIDC Provider: token.actions.githubusercontent.com"
    echo "   IAM Role: $ROLE_NAME"
    echo "   IAM Policy: ${ROLE_NAME}-Policy"
    echo "   Repository: $GITHUB_REPO"
    echo ""
    echo "Role ARN:"
    echo "   $role_arn"
    echo ""
    echo "Next Steps:"
    echo "   1. Set GitHub repository secret (in both 'stage' and 'prod' environments):"
    echo "      AWS_ROLE_TO_ASSUME = $role_arn"
    echo ""
}

validate_github_repo() {
    if [[ ! "$GITHUB_REPO" =~ ^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$ ]]; then
        log_error "Invalid GitHub repository format: $GITHUB_REPO"
        exit 1
    fi
}

main() {
    echo "Setting up GitHub OIDC IAM Role for IrishTaxHub MCP Server"
    echo "==========================================================="
    echo ""
    validate_github_repo
    check_aws_cli
    check_aws_credentials
    echo ""
    log_info "Configuration:"
    echo "   Project: $PROJECT_NAME"
    echo "   AWS Region: $AWS_REGION"
    echo "   GitHub Repository: $GITHUB_REPO"
    echo "   IAM Role Name: $ROLE_NAME"
    echo "   Artifacts Bucket: $ARTIFACTS_BUCKET"
    echo "   TF State Bucket: $TF_STATE_BUCKET"
    echo "   TF Locks Table: $TF_STATE_DYNAMODB_TABLE"
    echo ""
    read -p "Continue with this configuration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    echo ""
    create_oidc_provider
    create_iam_role
    print_summary
}

if ! command -v jq &> /dev/null; then
    log_error "jq is required for this script but not found."
    log_info "Install jq: brew install jq"
    exit 1
fi

main "$@"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/setup_github_oidc.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/setup_github_oidc.sh
git commit -m "feat: add GitHub OIDC IAM role setup script"
```

---

### Task 12: Create GitHub Actions workflows

**Files:**
- Create: `.github/workflows/deploy-stage.yml`
- Create: `.github/workflows/deploy-prod.yml`
- Create: `.github/workflows/tf-plan.yml`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create .github/workflows/deploy-stage.yml**

```yaml
name: Deploy MCP (stage)

on:
  push:
    branches: [ main ]
    paths:
      - 'src/**'
      - 'requirements.txt'
      - 'lambda_handler.py'
      - 'terraform/**'
      - 'scripts/package_lambda.sh'
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

env:
  APP_NAME: irishtaxhub-mcp
  REGION: eu-west-1

jobs:
  stage:
    name: Deploy stage
    runs-on: ubuntu-latest
    environment: stage
    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Setup Python 3.11
        uses: actions/setup-python@v6
        with:
          python-version: '3.11'

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ env.REGION }}
          audience: sts.amazonaws.com
          role-session-name: irishtaxhub-mcp-stage-deploy

      - name: Generate unique S3 key
        id: s3key
        run: |
          TIMESTAMP=$(date +%Y%m%d-%H%M%S)
          COMMIT_SHA=${{ github.sha }}
          S3_KEY="irishtaxhub-mcp/stage/irishtaxhub-mcp-${TIMESTAMP}-${COMMIT_SHA:0:8}.zip"
          echo "s3_key=${S3_KEY}" >> $GITHUB_OUTPUT

      - name: Package Lambda
        run: bash scripts/package_lambda.sh

      - name: Upload artifact to S3
        run: |
          aws s3 cp dist/irishtaxhub-mcp.zip s3://${{ secrets.ARTIFACTS_BUCKET }}/${{ steps.s3key.outputs.s3_key }}
          aws s3 cp dist/irishtaxhub-mcp.zip s3://${{ secrets.ARTIFACTS_BUCKET }}/irishtaxhub-mcp/stage/irishtaxhub-mcp.zip

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: 1.7.5

      - name: Terraform Init
        working-directory: terraform/envs/stage
        run: |
          terraform init \
            -backend-config="bucket=${{ secrets.TF_STATE_BUCKET }}" \
            -backend-config="key=state/irishtaxhub-mcp/stage.tfstate" \
            -backend-config="region=${{ env.REGION }}" \
            -backend-config="dynamodb_table=${{ secrets.TF_STATE_DYNAMODB_TABLE }}" \
            -backend-config="encrypt=true"

      - name: Terraform Apply (stage)
        working-directory: terraform/envs/stage
        run: |
          terraform apply -auto-approve \
            -var "region=${{ env.REGION }}" \
            -var "lambda_s3_bucket=${{ secrets.ARTIFACTS_BUCKET }}" \
            -var "lambda_s3_key=${{ steps.s3key.outputs.s3_key }}" \
            -var 'env_vars={APP_ENV="development",LOG_LEVEL="DEBUG"}'
```

- [ ] **Step 2: Create .github/workflows/deploy-prod.yml**

```yaml
name: Deploy MCP (prod)

on:
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

env:
  APP_NAME: irishtaxhub-mcp
  REGION: eu-west-1

jobs:
  prod:
    name: Deploy prod
    runs-on: ubuntu-latest
    environment: prod
    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Setup Python 3.11
        uses: actions/setup-python@v6
        with:
          python-version: '3.11'

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ env.REGION }}
          audience: sts.amazonaws.com
          role-session-name: irishtaxhub-mcp-prod-deploy

      - name: Generate unique S3 key
        id: s3key
        run: |
          TIMESTAMP=$(date +%Y%m%d-%H%M%S)
          COMMIT_SHA=${{ github.sha }}
          S3_KEY="irishtaxhub-mcp/prod/irishtaxhub-mcp-${TIMESTAMP}-${COMMIT_SHA:0:8}.zip"
          echo "s3_key=${S3_KEY}" >> $GITHUB_OUTPUT

      - name: Package Lambda
        run: bash scripts/package_lambda.sh

      - name: Upload artifact to S3
        run: |
          aws s3 cp dist/irishtaxhub-mcp.zip s3://${{ secrets.ARTIFACTS_BUCKET }}/${{ steps.s3key.outputs.s3_key }}
          aws s3 cp dist/irishtaxhub-mcp.zip s3://${{ secrets.ARTIFACTS_BUCKET }}/irishtaxhub-mcp/prod/irishtaxhub-mcp.zip

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: 1.7.5

      - name: Terraform Init
        working-directory: terraform/envs/prod
        run: |
          terraform init \
            -backend-config="bucket=${{ secrets.TF_STATE_BUCKET }}" \
            -backend-config="key=state/irishtaxhub-mcp/prod.tfstate" \
            -backend-config="region=${{ env.REGION }}" \
            -backend-config="dynamodb_table=${{ secrets.TF_STATE_DYNAMODB_TABLE }}" \
            -backend-config="encrypt=true"

      - name: Terraform Apply (prod)
        working-directory: terraform/envs/prod
        run: |
          terraform apply -auto-approve \
            -var "region=${{ env.REGION }}" \
            -var "lambda_s3_bucket=${{ secrets.ARTIFACTS_BUCKET }}" \
            -var "lambda_s3_key=${{ steps.s3key.outputs.s3_key }}" \
            -var 'env_vars={APP_ENV="production",LOG_LEVEL="INFO"}'
```

- [ ] **Step 3: Create .github/workflows/tf-plan.yml**

```yaml
name: Terraform Plan (PR)

on:
  pull_request:
    branches: [ main ]
    paths:
      - 'terraform/**'
      - 'src/**'
      - 'requirements.txt'
      - 'lambda_handler.py'
      - 'scripts/package_lambda.sh'

permissions:
  id-token: write
  contents: read
  pull-requests: write

env:
  REGION: eu-west-1
  STAGE_KEY: irishtaxhub-mcp/stage/irishtaxhub-mcp.zip
  PROD_KEY: irishtaxhub-mcp/prod/irishtaxhub-mcp.zip

jobs:
  fmt_validate:
    name: Format & Validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: 1.7.5
      - name: Terraform fmt check
        run: terraform fmt -check -recursive
      - name: Terraform validate (stage)
        working-directory: terraform/envs/stage
        run: |
          terraform init -backend=false
          terraform validate
      - name: Terraform validate (prod)
        working-directory: terraform/envs/prod
        run: |
          terraform init -backend=false
          terraform validate

  plan_stage:
    name: Plan stage
    runs-on: ubuntu-latest
    needs: fmt_validate
    steps:
      - uses: actions/checkout@v6
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ env.REGION }}
          audience: sts.amazonaws.com
          role-session-name: irishtaxhub-mcp-tf-plan
      - uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: 1.7.5
      - name: Terraform Init
        working-directory: terraform/envs/stage
        run: |
          terraform init \
            -backend-config="bucket=${{ secrets.TF_STATE_BUCKET }}" \
            -backend-config="key=state/irishtaxhub-mcp/stage.tfstate" \
            -backend-config="region=${{ env.REGION }}" \
            -backend-config="dynamodb_table=${{ secrets.TF_STATE_DYNAMODB_TABLE }}" \
            -backend-config="encrypt=true"
      - name: Terraform Plan (stage)
        working-directory: terraform/envs/stage
        run: |
          terraform plan -no-color \
            -var "region=${{ env.REGION }}" \
            -var "lambda_s3_bucket=${{ secrets.ARTIFACTS_BUCKET }}" \
            -var "lambda_s3_key=${{ env.STAGE_KEY }}" \
            -var 'env_vars={APP_ENV="development"}' \
            -out tfplan
      - name: Upload plan artifact
        uses: actions/upload-artifact@v7
        with:
          name: stage-tfplan
          path: terraform/envs/stage/tfplan
      - name: Add plan summary
        working-directory: terraform/envs/stage
        run: |
          echo '### Terraform Plan (stage)' >> $GITHUB_STEP_SUMMARY
          terraform show -no-color tfplan >> $GITHUB_STEP_SUMMARY

  plan_prod:
    name: Plan prod
    runs-on: ubuntu-latest
    needs: fmt_validate
    steps:
      - uses: actions/checkout@v6
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ env.REGION }}
          audience: sts.amazonaws.com
          role-session-name: irishtaxhub-mcp-tf-plan
      - uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: 1.7.5
      - name: Terraform Init
        working-directory: terraform/envs/prod
        run: |
          terraform init \
            -backend-config="bucket=${{ secrets.TF_STATE_BUCKET }}" \
            -backend-config="key=state/irishtaxhub-mcp/prod.tfstate" \
            -backend-config="region=${{ env.REGION }}" \
            -backend-config="dynamodb_table=${{ secrets.TF_STATE_DYNAMODB_TABLE }}" \
            -backend-config="encrypt=true"
      - name: Terraform Plan (prod)
        working-directory: terraform/envs/prod
        run: |
          terraform plan -no-color \
            -var "region=${{ env.REGION }}" \
            -var "lambda_s3_bucket=${{ secrets.ARTIFACTS_BUCKET }}" \
            -var "lambda_s3_key=${{ env.PROD_KEY }}" \
            -var 'env_vars={APP_ENV="production"}' \
            -out tfplan
      - name: Upload plan artifact
        uses: actions/upload-artifact@v7
        with:
          name: prod-tfplan
          path: terraform/envs/prod/tfplan
      - name: Add plan summary
        working-directory: terraform/envs/prod
        run: |
          echo '### Terraform Plan (prod)' >> $GITHUB_STEP_SUMMARY
          terraform show -no-color tfplan >> $GITHUB_STEP_SUMMARY
```

- [ ] **Step 4: Create .github/workflows/ci.yml**

```yaml
name: CI (Lint & Test)

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  lint-and-test:
    name: Lint & Test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11']

    steps:
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: 2.1.0
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Cache poetry dependencies
        uses: actions/cache@v5
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/poetry.lock') }}
          restore-keys: |
            venv-${{ runner.os }}-${{ matrix.python-version }}-

      - name: Install dependencies
        run: poetry install

      - name: Check code formatting with Black
        run: poetry run black --check --diff .

      - name: Check import sorting with isort
        run: poetry run isort --check-only --diff .

      - name: Lint with Flake8
        run: poetry run flake8 .

      - name: Run tests with pytest
        run: poetry run pytest -v
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/deploy-stage.yml .github/workflows/deploy-prod.yml .github/workflows/tf-plan.yml .github/workflows/ci.yml
git commit -m "feat: add GitHub Actions CI/CD workflows"
```

---

### Task 13: Run AWS prerequisites setup

**Files:** None (AWS resources created via CLI)

- [ ] **Step 1: Run the prerequisites script**

```bash
cd /Users/jameshurley/projects/irishtaxhub-mcp
bash scripts/setup_aws_prerequisites.sh
```

Expected: Creates S3 buckets and DynamoDB table, generates backend.hcl files.

- [ ] **Step 2: Run the OIDC setup script**

```bash
bash scripts/setup_github_oidc.sh
```

Expected: Creates or reuses OIDC provider, creates IAM role with deployment permissions. Note the Role ARN from the output.

- [ ] **Step 3: Set GitHub repository secrets**

Using the `gh` CLI, set the required secrets for both stage and prod environments:

```bash
# Get the role ARN from the OIDC script output
ROLE_ARN="<role-arn-from-output>"

# Create environments if they don't exist
gh api repos/jhurleyai/irishtaxhub-mcp/environments/stage -X PUT -f wait_timer=0
gh api repos/jhurleyai/irishtaxhub-mcp/environments/prod -X PUT -f wait_timer=0

# Set secrets for stage
gh secret set AWS_ROLE_TO_ASSUME --env stage --body "$ROLE_ARN"
gh secret set ARTIFACTS_BUCKET --env stage --body "artifacts-irishtaxhub-mcp"
gh secret set TF_STATE_BUCKET --env stage --body "tf-state-irishtaxhub-mcp"
gh secret set TF_STATE_DYNAMODB_TABLE --env stage --body "tf-locks-irishtaxhub-mcp"

# Set secrets for prod
gh secret set AWS_ROLE_TO_ASSUME --env prod --body "$ROLE_ARN"
gh secret set ARTIFACTS_BUCKET --env prod --body "artifacts-irishtaxhub-mcp"
gh secret set TF_STATE_BUCKET --env prod --body "tf-state-irishtaxhub-mcp"
gh secret set TF_STATE_DYNAMODB_TABLE --env prod --body "tf-locks-irishtaxhub-mcp"
```

- [ ] **Step 4: Commit generated backend.hcl files**

```bash
git add terraform/envs/stage/backend.hcl terraform/envs/prod/backend.hcl
git commit -m "chore: add generated Terraform backend configs"
```

---

### Task 14: Push branch and create PR

**Files:** None

- [ ] **Step 1: Push the feature branch**

```bash
git push -u origin feat/aws-deployment
```

- [ ] **Step 2: Create PR**

```bash
gh pr create --title "feat: add AWS Lambda deployment (stage + prod)" --body "$(cat <<'EOF'
## Summary
- Add Lambda handler wrapping FastMCP ASGI app with Mangum
- Add Terraform infrastructure (Lambda + API Gateway + custom domains)
- Add GitHub Actions CI/CD (auto-deploy stage, manual prod)
- Add AWS setup scripts (prerequisites + OIDC)
- Stage: mcp-stage.aws.irishtaxhub.ie → stage API
- Prod: mcp-prod.aws.irishtaxhub.ie → prod API

## Test plan
- [ ] Terraform validates successfully (stage + prod)
- [ ] AWS prerequisites created (S3 buckets, DynamoDB lock table)
- [ ] OIDC role created and GitHub secrets configured
- [ ] Stage deploys successfully via GitHub Actions
- [ ] MCP endpoints respond on mcp-stage.aws.irishtaxhub.ie
- [ ] Prod deploys successfully via manual trigger
- [ ] MCP endpoints respond on mcp-prod.aws.irishtaxhub.ie
EOF
)"
```

- [ ] **Step 3: Verify PR CI passes**

Check the GitHub Actions tab or run:

```bash
gh pr checks
```

Expected: Terraform format/validate passes, CI lint passes.
