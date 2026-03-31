variable "name" {
  description = "Base name for resources (e.g., irishtaxhub-mcp)"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g., stage or prod)"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.region))
    error_message = "Region must be a valid AWS region format (e.g., us-east-1, eu-west-1)."
  }
}

variable "lambda_s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package (zip)"
  type        = string
}

variable "lambda_s3_key" {
  description = "S3 key (path) to the Lambda deployment package (zip)"
  type        = string
}

variable "lambda_memory_mb" {
  description = "Lambda memory in MB"
  type        = number
  default     = 512

  validation {
    condition     = var.lambda_memory_mb >= 128 && var.lambda_memory_mb <= 10240
    error_message = "Lambda memory must be between 128 MB and 10240 MB."
  }
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 29

  validation {
    condition     = var.lambda_timeout_seconds > 0 && var.lambda_timeout_seconds <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "env_vars" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "create_domain" {
  description = "Whether to create a custom domain, ACM cert, and API mapping"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Fully qualified domain name for the API custom domain"
  type        = string
  default     = ""
}

variable "certificate_validated" {
  description = "Set to true after ACM certificate DNS validation is complete"
  type        = bool
  default     = false
}

variable "python_runtime" {
  description = "Python runtime version for Lambda"
  type        = string
  default     = "python3.11"

  validation {
    condition     = can(regex("^python3\\.(8|9|10|11|12|13)$", var.python_runtime))
    error_message = "Python runtime must be a valid version (python3.8 through python3.13)."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch Logs retention value."
  }
}

variable "api_stage_name" {
  description = "API Gateway stage name"
  type        = string
  default     = null

  validation {
    condition     = var.api_stage_name == null || can(regex("^[a-zA-Z0-9-_]+$", var.api_stage_name))
    error_message = "API stage name must contain only alphanumeric characters, hyphens, and underscores."
  }
}

variable "lambda_web_adapter_layer_arn" {
  description = "ARN of the AWS Lambda Web Adapter layer for streaming support"
  type        = string
  default     = ""
}

variable "create_streaming_domain" {
  description = "Whether to create CloudFront distribution for streaming endpoint"
  type        = bool
  default     = false
}

variable "streaming_domain_name" {
  description = "Custom domain name for streaming/MCP endpoint"
  type        = string
  default     = ""
}
