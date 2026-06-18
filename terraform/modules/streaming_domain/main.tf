terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = ">= 5.0"
      configuration_aliases = [aws.us_east_1]
    }
  }
}

# ACM Certificate for streaming subdomain (must be in us-east-1 for CloudFront)
resource "aws_acm_certificate" "streaming_cert" {
  count             = var.create_domain ? 1 : 0
  provider          = aws.us_east_1
  domain_name       = var.domain_name
  validation_method = "DNS"
  tags              = var.tags

  lifecycle {
    create_before_destroy = true
  }
}

# TRANSITIONAL (OAC unwind, step 1 of 2): the OAC approach was abandoned (it
# can't sign POST bodies to Lambda Function URLs). This resource is kept ONLY so
# Terraform does not try to delete it in the same apply that removes its
# reference from the distribution below — CloudFront returns 409
# OriginAccessControlInUse if the OAC is deleted before the distribution update
# has propagated. The distribution no longer references it (it uses the
# X-Origin-Verify custom header instead). A follow-up PR removes this resource
# once the distribution is deployed without it. Safe to drop the count guard's
# tail because it already exists in stage/prod state.
resource "aws_cloudfront_origin_access_control" "lambda" {
  count                             = var.create_domain && var.certificate_validated ? 1 : 0
  name                              = "${var.domain_name}-oac"
  description                       = "OAC for the MCP streaming Lambda Function URL origin"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront only created after cert is validated
resource "aws_cloudfront_distribution" "streaming" {
  count      = var.create_domain && var.certificate_validated ? 1 : 0
  enabled    = true
  aliases    = [var.domain_name]
  web_acl_id = var.web_acl_arn

  origin {
    domain_name = var.lambda_function_url_hostname
    origin_id   = "lambda-streaming"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }

    # Shared-secret origin lock: CloudFront injects this header on every origin
    # request. The Lambda app rejects /mcp requests without it, so the raw
    # Function URL (and the API Gateway path) can't be used to bypass the edge.
    # OAC/SigV4 can't be used here because CloudFront can't sign POST bodies to
    # Lambda Function URLs, and MCP is POST-based. CloudFront origin custom
    # headers override any viewer-supplied header of the same name, so it can't
    # be spoofed through the edge.
    custom_header {
      name  = "X-Origin-Verify"
      value = var.origin_verify_secret
    }
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "lambda-streaming"

    forwarded_values {
      query_string = true
      headers      = ["Accept", "Authorization", "Content-Type", "Origin", "Mcp-Session-Id"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.streaming_cert[0].arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = var.tags
}
