# MCP Server AWS Deployment Design

## Overview

Deploy the irishtaxhub-mcp server to AWS Lambda (stage + prod), following the same patterns established by irishtaxhubapi and irishtaxhubplatform.

## Architecture

- **Compute:** AWS Lambda (Python 3.11)
- **Routing:** API Gateway HTTP v2
- **IaC:** Terraform with remote S3 state + DynamoDB locking
- **CI/CD:** GitHub Actions with OIDC authentication
- **Transport:** FastMCP v2 ASGI app wrapped with Mangum for Lambda compatibility

## Domains

| Environment | Domain |
|-------------|--------|
| Stage | `mcp-stage.aws.irishtaxhub.ie` |
| Production | `mcp-prod.aws.irishtaxhub.ie` |

## Environment Configuration

| Setting | Stage | Prod |
|---------|-------|------|
| `IRISHTAXHUB_BASE_URL` | `https://stage.aws.irishtaxhub.ie` | `https://prod.aws.irishtaxhub.ie` |
| `APP_ENV` | `development` | `production` |
| `LOG_LEVEL` | `DEBUG` | `INFO` |
| Lambda memory | 512 MB | 512 MB |
| Lambda timeout | 29s | 29s |
| Log retention | 30 days | 90 days |

## AWS Resources

### Per-project (created by setup scripts)

- `tf-state-irishtaxhub-mcp` — S3 bucket for Terraform state
- `tf-locks-irishtaxhub-mcp` — DynamoDB table for state locking
- `artifacts-irishtaxhub-mcp` — S3 bucket for Lambda deployment packages
- GitHub OIDC IAM role scoped to `irishtaxhub-mcp` repo

### Per-environment (created by Terraform)

- Lambda function (`irishtaxhub-mcp-{stage|prod}`)
- Lambda execution IAM role (CloudWatch Logs only)
- API Gateway HTTP v2
- ACM certificate (DNS-validated)
- API Gateway custom domain mapping
- CloudWatch log group

## Files to Create

### Application

- `lambda_handler.py` — Mangum wrapper around FastMCP's ASGI app

### Scripts

- `scripts/package_lambda.sh` — Docker-based Lambda zip packaging
- `scripts/setup_aws_prerequisites.sh` — Creates S3 buckets + DynamoDB lock table
- `scripts/setup_github_oidc.sh` — Creates GitHub OIDC IAM role for this repo

### Terraform

```
terraform/
├── envs/
│   ├── stage/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── backend.tf
│   │   └── terraform.tfvars
│   └── prod/
│       ├── main.tf
│       ├── variables.tf
│       ├── backend.tf
│       └── terraform.tfvars
└── modules/
    ├── api_lambda/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── custom_domain/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

### GitHub Actions

- `.github/workflows/deploy-stage.yml` — Auto-deploy on push to main
- `.github/workflows/deploy-prod.yml` — Manual trigger only
- `.github/workflows/tf-plan.yml` — Terraform plan on PRs
- `.github/workflows/ci.yml` — Lint and tests

## What's NOT Needed (vs irishtaxhubapi)

- No DynamoDB tables (no rate limiting or stats)
- No streaming domain / CloudFront
- No Secrets Manager (no API keys to store)
- No Sentry integration
- No CORS configuration (not a browser-facing API)

## GitHub Secrets Required

- `AWS_ROLE_TO_ASSUME` — OIDC role ARN
- `ARTIFACTS_BUCKET` — `artifacts-irishtaxhub-mcp`
- `TF_STATE_BUCKET` — `tf-state-irishtaxhub-mcp`
- `TF_STATE_DYNAMODB_TABLE` — `tf-locks-irishtaxhub-mcp`
