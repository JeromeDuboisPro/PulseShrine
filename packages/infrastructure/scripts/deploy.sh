#!/bin/bash

# PulseShrine Infrastructure Deployment Script
# This script ensures the infrastructure is deployed with proper region configuration

set -e

# Handle help flag
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "🚀 PulseShrine Infrastructure Deployment Script"
    echo "=============================================="
    echo ""
    echo "This script deploys PulseShrine infrastructure to AWS using CDK."
    echo "It automatically detects your AWS credentials and region configuration."
    echo ""
    echo "📋 Usage:"
    echo "  ./deploy.sh                          # Use default AWS configuration"
    echo "  ./deploy.sh --help                   # Show this help message"
    echo ""
    echo "🔐 AWS Credential Methods:"
    echo ""
    echo "1. AWS Profile (Recommended):"
    echo "   AWS_PROFILE=myprofile ./deploy.sh"
    echo "   export AWS_PROFILE=myprofile && ./deploy.sh"
    echo ""
    echo "2. Environment Variables:"
    echo "   AWS_DEFAULT_REGION=eu-west-3 AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=yyy ./deploy.sh"
    echo ""
    echo "3. AWS SSO:"
    echo "   aws sso login --profile myprofile"
    echo "   AWS_PROFILE=myprofile ./deploy.sh"
    echo ""
    echo "4. AWS CLI Default:"
    echo "   aws configure set region eu-west-3"
    echo "   ./deploy.sh"
    echo ""
    echo "5. IAM Roles (EC2/Container):"
    echo "   AWS_DEFAULT_REGION=eu-west-3 ./deploy.sh"
    echo ""
    echo "📍 Supported Regions:"
    echo "   • us-east-1, us-west-2"
    echo "   • eu-west-1, eu-west-3"
    echo "   • ap-southeast-2"
    echo "   • Any AWS region (with automatic service adaptation)"
    echo ""
    echo "✅ Prerequisites:"
    echo "   • AWS credentials configured"
    echo "   • Node.js and npm installed"
    echo "   • AWS CDK CLI (optional - will use npx)"
    echo ""
    exit 0
fi

echo "🚀 PulseShrine Infrastructure Deployment"
echo "========================================"
echo ""
echo "💡 Usage examples:"
echo "   AWS_PROFILE=myprofile ./deploy.sh"
echo "   AWS_DEFAULT_REGION=eu-west-3 ./deploy.sh"
echo "   AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=yyy AWS_DEFAULT_REGION=eu-west-3 ./deploy.sh"
echo "   aws sso login --profile myprofile && AWS_PROFILE=myprofile ./deploy.sh"
echo ""

# Display current AWS configuration method
if [ ! -z "$AWS_PROFILE" ]; then
    echo "📋 Using AWS Profile: $AWS_PROFILE"
elif [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "📋 Using AWS environment variables"
else
    echo "📋 Using default AWS configuration"
fi

# Try multiple methods to get AWS region
AWS_REGION=""
if [ ! -z "$AWS_DEFAULT_REGION" ]; then
    AWS_REGION="$AWS_DEFAULT_REGION"
elif [ ! -z "$AWS_REGION" ]; then
    AWS_REGION="$AWS_REGION"
else
    # Try to get from AWS CLI config
    AWS_REGION=$(aws configure get region 2>/dev/null || echo "")
fi

# Try to get AWS account ID
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")

if [ -z "$AWS_REGION" ]; then
    echo "⚠️  No AWS region found. Please configure your region using one of:"
    echo "   • AWS Profile: aws configure set region eu-west-3 --profile your-profile"
    echo "   • Environment: export AWS_DEFAULT_REGION=eu-west-3"
    echo "   • AWS CLI: aws configure set region eu-west-3"
    echo "   • AWS SSO: aws sso login --profile your-profile"
    exit 1
fi

if [ -z "$AWS_ACCOUNT" ]; then
    echo "⚠️  Cannot determine AWS account. Please check your AWS credentials:"
    echo "   • If using profiles: export AWS_PROFILE=your-profile"
    echo "   • If using SSO: aws sso login --profile your-profile"
    echo "   • If using environment variables: ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set"
    echo "   • Test with: aws sts get-caller-identity"
    exit 1
fi

echo "📍 Deploying to:"
echo "   Region: $AWS_REGION"
echo "   Account: $AWS_ACCOUNT"
echo ""

# Set environment variables for CDK
export CDK_DEFAULT_REGION=$AWS_REGION
export CDK_DEFAULT_ACCOUNT=$AWS_ACCOUNT

echo "🔧 Environment variables set:"
echo "   CDK_DEFAULT_REGION=$CDK_DEFAULT_REGION"
echo "   CDK_DEFAULT_ACCOUNT=$CDK_DEFAULT_ACCOUNT"
echo ""

# Check if we're in the right directory
if [ ! -f "cdk.json" ]; then
    echo "❌ Error: cdk.json not found. Please run this script from the infrastructure directory."
    exit 1
fi

# Install dependencies if needed
echo "📦 Installing dependencies..."
npm install

# Bootstrap CDK if needed (safe to run multiple times)
echo "🏗️  Bootstrapping CDK for region $AWS_REGION..."
npx cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION

# Deploy the infrastructure
echo "🚀 Deploying infrastructure..."
npx cdk deploy --all --require-approval never

echo ""
echo "✅ Deployment completed successfully!"
echo "🌍 Infrastructure deployed to region: $AWS_REGION"
echo ""
echo "📊 Next steps:"
echo "   1. Check AWS Console in $AWS_REGION region"
echo "   2. Update frontend configuration with new API endpoints"
echo "   3. Test the application"