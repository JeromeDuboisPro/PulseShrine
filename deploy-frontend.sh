#!/bin/bash

# PulseShrine Frontend Deployment Script
# This script builds and deploys the React frontend to S3 with CloudFront cache invalidation

set -e  # Exit on any error

# Configuration
ENVIRONMENT=${ENVIRONMENT:-dev}
MARKET=${MARKET:-global}
AWS_PROFILE=${AWS_PROFILE:-pulse-admin}
REGION=${REGION:-eu-west-3}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to get stack outputs
get_stack_output() {
    local stack_name=$1
    local output_key=$2
    aws cloudformation describe-stacks \
        --profile $AWS_PROFILE \
        --region $REGION \
        --stack-name $stack_name \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null || echo ""
}

# Function to update frontend environment configuration
update_frontend_env() {
    local api_url=$1
    local user_pool_id=$2
    local user_pool_client_id=$3
    
    log_info "Updating frontend environment configuration..."
    
    # Create .env.local file for the frontend
    cat > packages/frontend-react/.env.local << EOF
# Auto-generated environment configuration for ${ENVIRONMENT}
VITE_API_BASE_URL=${api_url}
VITE_COGNITO_USER_POOL_ID=${user_pool_id}
VITE_COGNITO_USER_POOL_CLIENT_ID=${user_pool_client_id}
VITE_COGNITO_REGION=${REGION}
VITE_ENVIRONMENT=${ENVIRONMENT}
VITE_MARKET=${MARKET}
EOF
    
    log_success "Environment configuration updated"
}

# Main deployment function
deploy_frontend() {
    log_info "Starting frontend deployment for environment: $ENVIRONMENT"
    
    # Check if AWS CLI is available
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed or not in PATH"
        exit 1
    fi
    
    # Check if profile exists
    if ! aws configure list-profiles | grep -q "^$AWS_PROFILE$"; then
        log_error "AWS profile '$AWS_PROFILE' not found"
        exit 1
    fi
    
    # Get deployment outputs
    log_info "Retrieving deployment information..."
    
    API_URL=$(get_stack_output "ApiGatewayStack" "PulseApiUrl")
    USER_POOL_ID=$(get_stack_output "AuthStack" "UserPoolId")
    USER_POOL_CLIENT_ID=$(get_stack_output "AuthStack" "UserPoolClientId")
    S3_BUCKET=$(get_stack_output "FrontendStack" "WebsiteBucketName")
    DISTRIBUTION_ID=$(get_stack_output "FrontendStack" "DistributionId")
    
    # Validate required outputs
    if [[ -z "$API_URL" || -z "$USER_POOL_ID" || -z "$USER_POOL_CLIENT_ID" || -z "$S3_BUCKET" ]]; then
        log_error "Could not retrieve all required deployment outputs"
        log_error "API_URL: $API_URL"
        log_error "USER_POOL_ID: $USER_POOL_ID"
        log_error "USER_POOL_CLIENT_ID: $USER_POOL_CLIENT_ID"
        log_error "S3_BUCKET: $S3_BUCKET"
        exit 1
    fi
    
    log_success "Retrieved deployment configuration:"
    log_info "  API URL: $API_URL"
    log_info "  User Pool ID: $USER_POOL_ID"
    log_info "  User Pool Client ID: $USER_POOL_CLIENT_ID"
    log_info "  S3 Bucket: $S3_BUCKET"
    log_info "  Distribution ID: $DISTRIBUTION_ID"
    
    # Update frontend environment configuration
    update_frontend_env "$API_URL" "$USER_POOL_ID" "$USER_POOL_CLIENT_ID"
    
    # Navigate to frontend directory
    cd packages/frontend-react
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        npm install
        log_success "Dependencies installed"
    fi
    
    # Build the frontend
    log_info "Building React frontend..."
    npm run build
    log_success "Frontend built successfully"
    
    # Deploy to S3
    log_info "Deploying to S3 bucket: $S3_BUCKET"
    aws s3 sync dist/ s3://$S3_BUCKET/ \
        --profile $AWS_PROFILE \
        --region $REGION \
        --delete \
        --cache-control "max-age=31536000" \
        --exclude "index.html" \
        --exclude "*.map"
    
    # Deploy index.html with no cache
    aws s3 cp dist/index.html s3://$S3_BUCKET/index.html \
        --profile $AWS_PROFILE \
        --region $REGION \
        --cache-control "max-age=0, no-cache, no-store, must-revalidate"
    
    log_success "Files uploaded to S3"
    
    # Invalidate CloudFront cache if distribution exists
    if [[ -n "$DISTRIBUTION_ID" ]]; then
        log_info "Invalidating CloudFront cache..."
        aws cloudfront create-invalidation \
            --profile $AWS_PROFILE \
            --distribution-id $DISTRIBUTION_ID \
            --paths "/*" \
            --query "Invalidation.Id" \
            --output text
        log_success "CloudFront cache invalidated"
    fi
    
    # Get website URL
    WEBSITE_URL=$(get_stack_output "FrontendStack" "WebsiteURL")
    
    log_success "🎉 Frontend deployment completed!"
    log_info "Website URL: $WEBSITE_URL"
    log_info "Note: CloudFront may take a few minutes to propagate changes"
    
    # Clean up
    cd ../..
    rm -f packages/frontend-react/.env.local
}

# Script entry point
main() {
    echo "=================================================="
    echo "🚀 PulseShrine Frontend Deployment"
    echo "=================================================="
    echo "Environment: $ENVIRONMENT"
    echo "Market: $MARKET"
    echo "AWS Profile: $AWS_PROFILE"
    echo "Region: $REGION"
    echo "=================================================="
    
    deploy_frontend
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi