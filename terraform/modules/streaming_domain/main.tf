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

# Origin Access Control: CloudFront SigV4-signs every request to the Lambda
# Function URL origin. Combined with the Function URL's AWS_IAM auth + an
# invoke permission scoped to this distribution, it means the raw
# *.lambda-url.* origin rejects (403) any request that didn't come through and
# get signed by this distribution — so the WAF/edge controls can't be bypassed.
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
    domain_name              = var.lambda_function_url_hostname
    origin_id                = "lambda-streaming"
    origin_access_control_id = aws_cloudfront_origin_access_control.lambda[0].id

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "lambda-streaming"

    # NOTE: "Authorization" is intentionally NOT forwarded — CloudFront OAC owns
    # that header for the SigV4 origin signature, and forwarding a viewer-supplied
    # one would break signing (403). This connector is no-auth, so nothing relies
    # on a viewer Authorization header reaching the origin.
    forwarded_values {
      query_string = true
      headers      = ["Accept", "Content-Type", "Origin", "Mcp-Session-Id"]

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
