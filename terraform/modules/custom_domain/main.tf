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

# Only create domain + mapping when cert is validated
# On first deploy, set certificate_validated = false, add DNS records,
# then set certificate_validated = true on next deploy
resource "aws_apigatewayv2_domain_name" "custom" {
  count       = var.create_domain && var.certificate_validated ? 1 : 0
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
  count       = var.create_domain && var.certificate_validated ? 1 : 0
  api_id      = var.api_id
  domain_name = aws_apigatewayv2_domain_name.custom[0].id
  stage       = var.api_stage_id
}
