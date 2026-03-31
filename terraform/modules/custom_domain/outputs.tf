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
