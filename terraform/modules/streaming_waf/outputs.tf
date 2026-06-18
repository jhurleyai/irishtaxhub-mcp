output "web_acl_arn" {
  description = "ARN of the streaming Web ACL, or null when disabled. Pass to the CloudFront distribution's web_acl_id."
  value       = var.enable ? aws_wafv2_web_acl.streaming[0].arn : null
}
