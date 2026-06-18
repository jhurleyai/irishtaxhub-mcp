variable "name" {
  description = "Base name for the Web ACL and its metrics (e.g. irishtaxhub-mcp-prod)"
  type        = string
}

variable "enable" {
  description = "Whether to create the WAF Web ACL"
  type        = bool
  default     = false
}

variable "block_mode" {
  description = "false = COUNT (observe only), true = BLOCK (enforce the rate limit)"
  type        = bool
  default     = false
}

variable "rate_limit_per_5min" {
  description = "Max requests allowed per source IP per 5-minute window before the rule trips"
  type        = number
  default     = 600

  validation {
    condition     = var.rate_limit_per_5min >= 100
    error_message = "WAFv2 rate-based rules require a limit of at least 100."
  }
}

variable "tags" {
  description = "Tags to apply to the Web ACL"
  type        = map(string)
  default     = {}
}
