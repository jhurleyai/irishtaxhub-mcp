terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# WAFv2 Web ACL for the public, anonymous MCP streaming endpoint.
#
# The endpoint sits behind CloudFront with no auth (authorization_type = "NONE"),
# so before it is listed in Anthropic's connector directory it needs an abuse
# guard. This ACL applies a per-source-IP request-rate cap at the edge, so
# blocked traffic never reaches the Lambda Function URL or the backend API.
#
# NOTE: For scope = CLOUDFRONT the ACL must be created in us-east-1. The caller
# maps the us-east-1 provider into this module's default `aws` provider.
#
# Rollout: start with block_mode = false (COUNT) to observe real traffic via
# CloudWatch + sampled requests, tune rate_limit_per_5min, then flip to BLOCK.
resource "aws_wafv2_web_acl" "streaming" {
  count = var.enable ? 1 : 0

  name        = "${var.name}-streaming"
  description = "Rate limiting / abuse guard for the public MCP streaming endpoint"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  rule {
    name     = "per-ip-rate-limit"
    priority = 1

    # COUNT while observing, BLOCK once the threshold is validated.
    action {
      dynamic "block" {
        for_each = var.block_mode ? [1] : []
        content {}
      }
      dynamic "count" {
        for_each = var.block_mode ? [] : [1]
        content {}
      }
    }

    statement {
      rate_based_statement {
        limit                 = var.rate_limit_per_5min
        aggregate_key_type    = "IP"
        evaluation_window_sec = 300
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name}-per-ip-rate"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.name}-streaming-acl"
    sampled_requests_enabled   = true
  }

  tags = var.tags
}
