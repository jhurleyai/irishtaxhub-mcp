variable "create_domain" {
  description = "Whether to create CloudFront distribution and ACM certificate for streaming domain"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Custom domain name for streaming endpoint"
  type        = string
  default     = ""
}

variable "lambda_function_url_hostname" {
  description = "Lambda Function URL hostname (without https://)"
  type        = string
}

variable "certificate_validated" {
  description = "Set to true after ACM cert DNS validation is complete. Controls CloudFront creation."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
