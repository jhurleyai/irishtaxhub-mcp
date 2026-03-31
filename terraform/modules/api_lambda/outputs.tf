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
