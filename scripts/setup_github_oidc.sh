#!/bin/bash
set -e

# GitHub OIDC IAM Role Setup Script for IrishTaxHub MCP Server

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
GITHUB_REPO="${GITHUB_REPO:-jhurleyai/irishtaxhub-mcp}"
GITHUB_ORG="${GITHUB_ORG:-jhurleyai}"
ROLE_NAME="${ROLE_NAME:-GitHubActions-${PROJECT_NAME}}"
OIDC_PROVIDER_ARN=""
ARTIFACTS_BUCKET="${ARTIFACTS_BUCKET:-artifacts-${PROJECT_NAME}}"
TF_STATE_BUCKET="${TF_STATE_BUCKET:-tf-state-${PROJECT_NAME}}"
TF_STATE_DYNAMODB_TABLE="${TF_STATE_DYNAMODB_TABLE:-tf-locks-${PROJECT_NAME}}"
LWA_LAYER_ARN="${LWA_LAYER_ARN:-}"

check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found."
        exit 1
    fi
    log_info "AWS CLI version: $(aws --version)"
}

check_aws_credentials() {
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid."
        exit 1
    fi
    local caller_identity=$(aws sts get-caller-identity)
    if command -v jq &> /dev/null; then
        log_success "AWS credentials valid for: $(echo $caller_identity | jq -r '.Arn')"
    else
        log_success "AWS credentials valid"
    fi
}

get_aws_account_id() { aws sts get-caller-identity --query Account --output text; }

oidc_provider_exists() {
    aws iam get-open-id-connect-provider --open-id-connect-provider-arn "arn:aws:iam::$(get_aws_account_id):oidc-provider/token.actions.githubusercontent.com" &> /dev/null
}

role_exists() { aws iam get-role --role-name "$ROLE_NAME" &> /dev/null 2>&1; }

create_oidc_provider() {
    log_info "Creating GitHub OIDC provider..."
    if oidc_provider_exists; then
        log_warning "GitHub OIDC provider already exists"
        OIDC_PROVIDER_ARN="arn:aws:iam::$(get_aws_account_id):oidc-provider/token.actions.githubusercontent.com"
        return 0
    fi
    OIDC_PROVIDER_ARN=$(aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 1c58a3a8518e8759bf075b76b750d4f2df264fcd d89e3bd43d5d909b47a18977aa9d5ce36cee184c \
        --query 'OpenIDConnectProviderArn' \
        --output text)
    log_success "Created GitHub OIDC provider: $OIDC_PROVIDER_ARN"
}

create_trust_policy() {
    local account_id=$(get_aws_account_id)
    cat > /tmp/trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::${account_id}:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": [
                        "repo:${GITHUB_REPO}:*"
                    ]
                }
            }
        }
    ]
}
EOF
    log_info "Generated trust policy for repository: $GITHUB_REPO"
}

create_permissions_policy() {
    local account_id=$(get_aws_account_id)
    cat > /tmp/permissions-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaManagement",
            "Effect": "Allow",
            "Action": ["lambda:*"],
            "Resource": ["arn:aws:lambda:${AWS_REGION}:${account_id}:function:${PROJECT_NAME}-*"]
        },
        {
            "Sid": "APIGatewayFull",
            "Effect": "Allow",
            "Action": ["apigateway:*"],
            "Resource": "*"
        },
        {
            "Sid": "IAMComprehensive",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole", "iam:GetRole", "iam:DeleteRole",
                "iam:AttachRolePolicy", "iam:DetachRolePolicy",
                "iam:ListAttachedRolePolicies", "iam:ListRolePolicies",
                "iam:GetRolePolicy", "iam:PutRolePolicy", "iam:DeleteRolePolicy",
                "iam:ListInstanceProfilesForRole", "iam:PassRole",
                "iam:TagRole", "iam:UntagRole", "iam:UpdateAssumeRolePolicy",
                "iam:CreateServiceLinkedRole",
                "iam:GetServiceLinkedRoleDeletionStatus", "iam:DeleteServiceLinkedRole",
                "iam:CreatePolicy", "iam:GetPolicy", "iam:DeletePolicy",
                "iam:CreatePolicyVersion", "iam:DeletePolicyVersion",
                "iam:ListPolicyVersions", "iam:GetPolicyVersion",
                "iam:SetDefaultPolicyVersion",
                "iam:TagPolicy", "iam:UntagPolicy", "iam:GetAccountSummary"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CloudWatchLogsFull",
            "Effect": "Allow",
            "Action": ["logs:*"],
            "Resource": "*"
        },
        {
            "Sid": "ACMCertificates",
            "Effect": "Allow",
            "Action": ["acm:*"],
            "Resource": "*"
        },
        {
            "Sid": "S3ArtifactsBucket",
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject"],
            "Resource": ["arn:aws:s3:::${ARTIFACTS_BUCKET}/*"]
        },
        {
            "Sid": "S3TerraformState",
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
            "Resource": [
                "arn:aws:s3:::${TF_STATE_BUCKET}",
                "arn:aws:s3:::${TF_STATE_BUCKET}/*"
            ]
        },
        {
            "Sid": "DynamoDBStateLocking",
            "Effect": "Allow",
            "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"],
            "Resource": ["arn:aws:dynamodb:${AWS_REGION}:${account_id}:table/${TF_STATE_DYNAMODB_TABLE}"]
        },
        {
            "Sid": "CloudFrontManagement",
            "Effect": "Allow",
            "Action": [
                "cloudfront:CreateDistribution",
                "cloudfront:GetDistribution",
                "cloudfront:GetDistributionConfig",
                "cloudfront:UpdateDistribution",
                "cloudfront:DeleteDistribution",
                "cloudfront:TagResource",
                "cloudfront:UntagResource",
                "cloudfront:ListTagsForResource"
            ],
            "Resource": "*"
        }
    ]
}
EOF

    # Add Lambda Web Adapter layer permission if ARN is provided
    if [ -n "$LWA_LAYER_ARN" ]; then
        if command -v jq &> /dev/null; then
            tmpfile=$(mktemp)
            jq --arg arn "$LWA_LAYER_ARN" '.Statement += [{
              "Sid": "LambdaWebAdapterLayerRead",
              "Effect": "Allow",
              "Action": ["lambda:GetLayerVersion"],
              "Resource": [$arn]
            }]' /tmp/permissions-policy.json > "$tmpfile" && mv "$tmpfile" /tmp/permissions-policy.json
            log_info "Included Lambda Web Adapter layer permission for $LWA_LAYER_ARN"
        else
            log_warning "jq not found; cannot inject Lambda Web Adapter layer permission automatically."
        fi
    fi

    log_info "Generated permissions policy"
}

update_policy() {
    local account_id=$(get_aws_account_id)
    local policy_name="${ROLE_NAME}-Policy"
    local policy_arn="arn:aws:iam::${account_id}:policy/${policy_name}"

    log_info "Updating IAM policy: $policy_name"
    if ! aws iam get-policy --policy-arn "$policy_arn" &> /dev/null; then
        log_error "Policy does not exist: $policy_name"
        return 1
    fi
    create_permissions_policy

    local versions=$(aws iam list-policy-versions --policy-arn "$policy_arn" --query 'Versions[*].[VersionId,IsDefaultVersion]' --output json)
    local version_count=$(echo "$versions" | jq 'length')

    if [ "$version_count" -ge 5 ]; then
        log_warning "Policy has maximum versions (5). Deleting oldest non-default version..."
        local oldest_version=$(echo "$versions" | jq -r '.[] | select(.[1] == false) | .[0]' | head -1)
        if [ -n "$oldest_version" ]; then
            aws iam delete-policy-version --policy-arn "$policy_arn" --version-id "$oldest_version"
            log_success "Deleted old policy version: $oldest_version"
        fi
    fi

    local new_version=$(aws iam create-policy-version \
        --policy-arn "$policy_arn" \
        --policy-document file:///tmp/permissions-policy.json \
        --set-as-default \
        --query 'PolicyVersion.VersionId' \
        --output text)
    log_success "Updated policy to version: $new_version"
}

create_iam_role() {
    log_info "Setting up IAM role: $ROLE_NAME"
    create_trust_policy
    create_permissions_policy

    if role_exists; then
        log_warning "IAM role '$ROLE_NAME' already exists"
        log_info "Updating the attached policy with latest permissions..."
        update_policy
        rm -f /tmp/trust-policy.json /tmp/permissions-policy.json
        return 0
    fi

    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "GitHub Actions OIDC role for $PROJECT_NAME deployment" \
        --max-session-duration 3600

    local policy_name="${ROLE_NAME}-Policy"
    local policy_arn=$(aws iam create-policy \
        --policy-name "$policy_name" \
        --policy-document file:///tmp/permissions-policy.json \
        --description "Permissions for GitHub Actions to deploy $PROJECT_NAME" \
        --query 'Policy.Arn' \
        --output text)

    aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$policy_arn"

    log_success "Created IAM role: $ROLE_NAME"
    log_success "Created and attached policy: $policy_name"
    rm -f /tmp/trust-policy.json /tmp/permissions-policy.json
}

print_summary() {
    local account_id=$(get_aws_account_id)
    local role_arn="arn:aws:iam::${account_id}:role/${ROLE_NAME}"
    echo ""
    log_success "GitHub OIDC Setup Complete!"
    echo ""
    echo "Created Resources:"
    echo "   OIDC Provider: token.actions.githubusercontent.com"
    echo "   IAM Role: $ROLE_NAME"
    echo "   IAM Policy: ${ROLE_NAME}-Policy"
    echo "   Repository: $GITHUB_REPO"
    echo ""
    echo "Role ARN:"
    echo "   $role_arn"
    echo ""
    echo "Next Steps:"
    echo "   1. Set GitHub repository secret (in both 'stage' and 'prod' environments):"
    echo "      AWS_ROLE_TO_ASSUME = $role_arn"
    echo ""
}

validate_github_repo() {
    if [[ ! "$GITHUB_REPO" =~ ^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$ ]]; then
        log_error "Invalid GitHub repository format: $GITHUB_REPO"
        exit 1
    fi
}

main() {
    echo "Setting up GitHub OIDC IAM Role for IrishTaxHub MCP Server"
    echo "==========================================================="
    echo ""
    validate_github_repo
    check_aws_cli
    check_aws_credentials
    echo ""
    log_info "Configuration:"
    echo "   Project: $PROJECT_NAME"
    echo "   AWS Region: $AWS_REGION"
    echo "   GitHub Repository: $GITHUB_REPO"
    echo "   IAM Role Name: $ROLE_NAME"
    echo "   Artifacts Bucket: $ARTIFACTS_BUCKET"
    echo "   TF State Bucket: $TF_STATE_BUCKET"
    echo "   TF Locks Table: $TF_STATE_DYNAMODB_TABLE"
    echo ""
    read -p "Continue with this configuration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    echo ""
    create_oidc_provider
    create_iam_role
    print_summary
}

if ! command -v jq &> /dev/null; then
    log_error "jq is required for this script but not found."
    log_info "Install jq: brew install jq"
    exit 1
fi

main "$@"
