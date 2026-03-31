#!/bin/bash
set -e

# AWS Prerequisites Setup Script for IrishTaxHub MCP Server

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/aws_config.env"

if [ -f "$CONFIG_FILE" ]; then
    log_info "Loading configuration from $CONFIG_FILE"
    source "$CONFIG_FILE"
fi

PROJECT_NAME="${PROJECT_NAME:-irishtaxhub-mcp}"
AWS_REGION="${AWS_REGION:-eu-west-1}"
ARTIFACTS_BUCKET="${ARTIFACTS_BUCKET:-artifacts-${PROJECT_NAME}}"
TF_STATE_BUCKET="${TF_STATE_BUCKET:-tf-state-${PROJECT_NAME}}"
TF_STATE_DYNAMODB_TABLE="${TF_STATE_DYNAMODB_TABLE:-tf-locks-${PROJECT_NAME}}"

check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install AWS CLI first."
        exit 1
    fi
    log_info "AWS CLI version: $(aws --version)"
}

check_aws_credentials() {
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid."
        log_info "Run 'aws configure' to set up your credentials."
        exit 1
    fi
    local caller_identity=$(aws sts get-caller-identity)
    if command -v jq &> /dev/null; then
        log_success "AWS credentials valid for: $(echo $caller_identity | jq -r '.Arn')"
    else
        log_success "AWS credentials valid"
    fi
}

bucket_exists() { aws s3 ls "s3://$1" &> /dev/null; }
table_exists() { aws dynamodb describe-table --table-name "$1" --region "$AWS_REGION" &> /dev/null 2>&1; }

create_artifacts_bucket() {
    log_info "Creating S3 artifacts bucket: $ARTIFACTS_BUCKET"
    if bucket_exists "$ARTIFACTS_BUCKET"; then
        log_warning "S3 bucket '$ARTIFACTS_BUCKET' already exists"
        return 0
    fi
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3 mb "s3://$ARTIFACTS_BUCKET"
    else
        aws s3 mb "s3://$ARTIFACTS_BUCKET" --region "$AWS_REGION"
    fi
    aws s3api put-bucket-versioning --bucket "$ARTIFACTS_BUCKET" --versioning-configuration Status=Enabled
    aws s3api put-public-access-block --bucket "$ARTIFACTS_BUCKET" \
        --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    log_success "Created artifacts bucket: $ARTIFACTS_BUCKET"
}

create_tf_state_bucket() {
    log_info "Creating S3 Terraform state bucket: $TF_STATE_BUCKET"
    if bucket_exists "$TF_STATE_BUCKET"; then
        log_warning "S3 bucket '$TF_STATE_BUCKET' already exists"
        return 0
    fi
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3 mb "s3://$TF_STATE_BUCKET"
    else
        aws s3 mb "s3://$TF_STATE_BUCKET" --region "$AWS_REGION"
    fi
    aws s3api put-bucket-versioning --bucket "$TF_STATE_BUCKET" --versioning-configuration Status=Enabled
    aws s3api put-bucket-encryption --bucket "$TF_STATE_BUCKET" \
        --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
    aws s3api put-public-access-block --bucket "$TF_STATE_BUCKET" \
        --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    log_success "Created Terraform state bucket: $TF_STATE_BUCKET"
}

create_tf_locks_table() {
    log_info "Creating DynamoDB table for Terraform locks: $TF_STATE_DYNAMODB_TABLE"
    if table_exists "$TF_STATE_DYNAMODB_TABLE"; then
        log_warning "DynamoDB table '$TF_STATE_DYNAMODB_TABLE' already exists"
        return 0
    fi
    aws dynamodb create-table \
        --table-name "$TF_STATE_DYNAMODB_TABLE" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION"
    log_info "Waiting for DynamoDB table to be active..."
    aws dynamodb wait table-exists --table-name "$TF_STATE_DYNAMODB_TABLE" --region "$AWS_REGION"
    log_success "Created DynamoDB locks table: $TF_STATE_DYNAMODB_TABLE"
}

generate_backend_configs() {
    log_info "Generating backend configuration files..."
    local stage_backend="$SCRIPT_DIR/../terraform/envs/stage/backend.hcl"
    local prod_backend="$SCRIPT_DIR/../terraform/envs/prod/backend.hcl"

    cat > "$stage_backend" << EOF
bucket         = "$TF_STATE_BUCKET"
key            = "state/irishtaxhub-mcp/stage.tfstate"
region         = "$AWS_REGION"
encrypt        = true
dynamodb_table = "$TF_STATE_DYNAMODB_TABLE"
EOF

    cat > "$prod_backend" << EOF
bucket         = "$TF_STATE_BUCKET"
key            = "state/irishtaxhub-mcp/prod.tfstate"
region         = "$AWS_REGION"
encrypt        = true
dynamodb_table = "$TF_STATE_DYNAMODB_TABLE"
EOF

    log_success "Generated backend configuration files"
}

print_summary() {
    echo ""
    log_success "AWS Prerequisites Setup Complete!"
    echo ""
    echo "Created Resources:"
    echo "   Artifacts bucket: $ARTIFACTS_BUCKET"
    echo "   Terraform state bucket: $TF_STATE_BUCKET"
    echo "   DynamoDB locks table: $TF_STATE_DYNAMODB_TABLE"
    echo "   Region: $AWS_REGION"
    echo ""
    echo "Next Steps:"
    echo "   1. Run: ./scripts/setup_github_oidc.sh"
    echo "   2. Set GitHub repository secrets:"
    echo "      ARTIFACTS_BUCKET = $ARTIFACTS_BUCKET"
    echo "      TF_STATE_BUCKET = $TF_STATE_BUCKET"
    echo "      TF_STATE_DYNAMODB_TABLE = $TF_STATE_DYNAMODB_TABLE"
    echo ""
}

main() {
    echo "Setting up AWS Prerequisites for IrishTaxHub MCP Server"
    echo "======================================================="
    echo ""
    check_aws_cli
    check_aws_credentials
    echo ""
    log_info "Configuration:"
    echo "   Project: $PROJECT_NAME"
    echo "   Region: $AWS_REGION"
    echo "   Artifacts bucket: $ARTIFACTS_BUCKET"
    echo "   TF state bucket: $TF_STATE_BUCKET"
    echo "   TF locks table: $TF_STATE_DYNAMODB_TABLE"
    echo ""
    read -p "Continue with this configuration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    echo ""
    create_artifacts_bucket
    create_tf_state_bucket
    create_tf_locks_table
    generate_backend_configs
    print_summary
}

if ! command -v jq &> /dev/null; then
    log_warning "jq not found. JSON output may not be formatted nicely."
fi

main "$@"
