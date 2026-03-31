terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = ">= 5.0"
      configuration_aliases = [aws.us_east_1]
    }
  }
}

locals {
  full_name = "${var.name}-${var.environment}"
}

resource "aws_iam_role" "lambda_role" {
  name               = "${local.full_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.full_name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_lambda_function" "this" {
  function_name = local.full_name
  role          = aws_iam_role.lambda_role.arn
  runtime       = var.python_runtime
  handler       = "lambda_handler.handler"

  s3_bucket        = var.lambda_s3_bucket
  s3_key           = var.lambda_s3_key
  source_code_hash = var.lambda_s3_key

  memory_size = var.lambda_memory_mb
  timeout     = var.lambda_timeout_seconds

  environment {
    variables = merge(
      var.env_vars,
      {
        API_GATEWAY_STAGE = coalesce(var.api_stage_name, var.environment)
      }
    )
  }

  tags = var.tags
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${local.full_name}-api"
  protocol_type = "HTTP"
  tags          = var.tags
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigwv2/${aws_apigatewayv2_api.http.name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_apigatewayv2_stage" "env" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = coalesce(var.api_stage_name, var.environment)
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      httpMethod              = "$context.httpMethod"
      path                    = "$context.path"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }

  tags = var.tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.this.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "root" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

############################
# Optional Custom Domain
############################

module "custom_domain" {
  source = "../custom_domain"

  create_domain         = var.create_domain
  domain_name           = var.domain_name
  certificate_validated = var.certificate_validated
  api_id                = aws_apigatewayv2_api.http.id
  api_stage_id          = aws_apigatewayv2_stage.env.id
  tags                  = var.tags
}

############################
# Streaming Lambda (MCP SSE support via Lambda Function URL)
############################

resource "aws_lambda_function" "streaming" {
  function_name = "${local.full_name}-streaming"
  role          = aws_iam_role.lambda_role.arn
  runtime       = var.python_runtime
  handler       = var.lambda_web_adapter_layer_arn == "" ? "lambda_handler.handler" : "run.sh"

  s3_bucket        = var.lambda_s3_bucket
  s3_key           = var.lambda_s3_key
  source_code_hash = var.lambda_s3_key

  memory_size = var.lambda_memory_mb
  timeout     = var.lambda_timeout_seconds

  layers = var.lambda_web_adapter_layer_arn == "" ? [] : [var.lambda_web_adapter_layer_arn]

  environment {
    variables = merge(
      var.env_vars,
      {
        AWS_LAMBDA_EXEC_WRAPPER = var.lambda_web_adapter_layer_arn == "" ? "/var/task/bootstrap" : "/opt/bootstrap"
        AWS_LWA_INVOKE_MODE     = "response_stream"
        AWS_LWA_PORT            = "8080"
      }
    )
  }

  tags = merge(var.tags, {
    Purpose = "MCP streaming endpoint"
  })
}

resource "aws_cloudwatch_log_group" "streaming_lambda" {
  name              = "/aws/lambda/${local.full_name}-streaming"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_lambda_function_url" "streaming" {
  function_name      = aws_lambda_function.streaming.function_name
  authorization_type = "NONE"
  invoke_mode        = "RESPONSE_STREAM"

  cors {
    allow_credentials = false
    allow_headers     = ["content-type", "authorization", "accept", "mcp-session-id"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]
    expose_headers    = ["mcp-session-id"]
    max_age           = 86400
  }
}

# Extract hostname from Lambda Function URL
locals {
  lambda_url_hostname = replace(replace(aws_lambda_function_url.streaming.function_url, "https://", ""), "/", "")
}

############################
# Streaming Custom Domain (CloudFront)
############################

module "streaming_domain" {
  source = "../streaming_domain"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  create_domain                = var.create_streaming_domain
  domain_name                  = var.streaming_domain_name
  certificate_validated        = var.streaming_certificate_validated
  lambda_function_url_hostname = local.lambda_url_hostname
  tags                         = var.tags
}
