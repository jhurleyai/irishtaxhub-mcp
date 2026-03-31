output "certificate_validation_records" {
  description = "DNS validation records for ACM certificate"
  value = var.create_domain ? [
    for dvo in aws_acm_certificate.streaming_cert[0].domain_validation_options : {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      value  = dvo.resource_record_value
      domain = dvo.domain_name
    }
  ] : []
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (create CNAME pointing custom domain to this)"
  value       = var.create_domain ? aws_cloudfront_distribution.streaming[0].domain_name : null
}

output "streaming_url" {
  description = "Custom domain URL for streaming endpoint"
  value       = var.create_domain ? "https://${var.domain_name}" : null
}

output "dns_configuration_instructions" {
  description = "Instructions for DNS configuration"
  value = var.create_domain ? {
    step_1 = "Add ACM certificate validation records to your DNS"
    step_2 = "Wait for certificate validation to complete"
    step_3 = "Create CNAME record: ${var.domain_name} -> ${aws_cloudfront_distribution.streaming[0].domain_name}"
    step_4 = "Access MCP endpoint at: https://${var.domain_name}/mcp"
  } : null
}
