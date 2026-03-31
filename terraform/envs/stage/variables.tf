variable "name" {
  description = "Base name for resources"
  type        = string
  default     = "irishtaxhub-mcp"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "lambda_s3_bucket" {
  description = "S3 bucket containing the Lambda deployment zip"
  type        = string
}

variable "lambda_s3_key" {
  description = "S3 key/path for the Lambda deployment zip"
  type        = string
}

variable "lambda_memory_mb" {
  description = "Lambda function memory allocation in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout_seconds" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 29
}

variable "python_runtime" {
  description = "Python runtime version for Lambda"
  type        = string
  default     = "python3.11"
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
}

variable "env_vars" {
  description = "Environment variables for Lambda"
  type        = map(string)
  default     = {}
}

variable "stage_domain" {
  description = "Stage environment domain name"
  type        = string
  default     = "mcp-stage.aws.irishtaxhub.ie"

  validation {
    condition     = can(regex("^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z]{2,}$", var.stage_domain))
    error_message = "Stage domain must be a valid FQDN format."
  }
}
