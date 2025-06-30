#!/bin/bash
# Deploy AWS Lambda Power Tuning for PulseShrine cost optimization

set -e

echo "🔧 Deploying AWS Lambda Power Tuning Tool"
echo "=========================================="

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI not found. Installing SAM CLI..."
    # Install SAM CLI
    pip3 install aws-sam-cli
fi

# Verify AWS credentials
echo "✅ Checking AWS credentials..."
aws sts get-caller-identity > /dev/null || {
    echo "❌ AWS credentials not configured. Please run 'aws configure' or set AWS_PROFILE"
    exit 1
}

REGION=$(aws configure get region || echo $AWS_DEFAULT_REGION || echo "us-east-1")
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

echo "📍 Deploying to region: $REGION"
echo "🏢 Account: $ACCOUNT"

# Create temporary directory for power tuning
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

echo "📥 Downloading AWS Lambda Power Tuning..."
git clone https://github.com/alexcasalboni/aws-lambda-power-tuning.git
cd aws-lambda-power-tuning

echo "🚀 Deploying Lambda Power Tuning State Machine..."
sam deploy \
    --guided \
    --stack-name lambda-power-tuning \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --parameter-overrides \
        PowerValues="128,256,512,1024,2048,3008" \
        lambdaResource="*" \
        totalExecutionTimeout=900

echo "✅ Lambda Power Tuning deployed successfully!"
echo ""
echo "🎯 State Machine ARN:"
aws stepfunctions list-state-machines \
    --query "stateMachines[?name=='lambda-power-tuning'].stateMachineArn" \
    --output text \
    --region "$REGION"

echo ""
echo "📖 Next steps:"
echo "1. Use the AWS Console or CLI to run power tuning executions"
echo "2. Target your PulseShrine Lambda functions for optimization"
echo "3. Analyze results to find cost-optimal configurations"

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo "🧹 Cleanup completed."