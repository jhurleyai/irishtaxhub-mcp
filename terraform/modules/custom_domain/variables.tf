variable "create_domain" {
  description = "Whether to create a custom domain, ACM cert, and API mapping"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Fully qualified domain name for the API custom domain"
  type        = string
  default     = ""

  validation {
    condition     = var.domain_name == "" || can(regex("^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z]{2,}$", var.domain_name))
    error_message = "Domain name must be a valid FQDN format."
  }
}

variable "api_id" {
  description = "API Gateway HTTP API ID to map the custom domain to"
  type        = string
}

variable "api_stage_id" {
  description = "API Gateway stage ID to map the custom domain to"
  type        = string
}

variable "certificate_validated" {
  description = "Set to true after ACM certificate DNS validation is complete. Controls API Gateway domain creation."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}
