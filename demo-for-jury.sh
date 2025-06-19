#!/bin/bash

# Single command demo script for jury
set -euo pipefail

# Default AWS profile
AWS_PROFILE=${AWS_PROFILE:-default}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if AWS credentials are configured
if ! aws sts get-caller-identity --profile "$AWS_PROFILE" > /dev/null 2>&1; then
    echo "AWS credentials are not configured for profile $AWS_PROFILE. Please log in or set AWS_PROFILE properly."
    exit 1
fi

echo "AWS credentials are configured for profile $AWS_PROFILE."

echo "🎯 Starting Pulse Demo for Jury..."
echo "This will deploy the backend and start the frontend automatically"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK not found. Please install with: npm install -g aws-cdk"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI and configure credentials"
    exit 1
fi

# Check if serve is available, install if not
if ! command -v serve &> /dev/null; then
    echo "📦 Installing 'serve' package for local development..."
    npm install -g serve
fi

# Install CDK dependencies
echo "📦 Installing CDK dependencies..."
cd packages/infrastructure
npm install
cd ../..

echo "✅ Prerequisites check passed"
echo ""

# Step 1: Deploy CDK stack and capture output
echo "🚀 Deploying backend (AWS CDK)..."
echo "This may take a few minutes..."

# Change to infrastructure directory
cd packages/infrastructure

CDK_OUTPUT=$(cdk deploy --profile=${AWS_PROFILE} ApiGatewayStack --outputs-file ../../cdk-outputs.json --require-approval never)

# Go back to root directory
cd ../..

if [ $? -ne 0 ]; then
    echo "❌ CDK deployment failed. Please check your AWS credentials and try again."
    exit 1
fi

echo "✅ Backend deployed successfully!"
echo ""

# Step 2: Extract API configuration
echo "🔍 Extracting API configuration..."

# Parse the JSON output file for endpoint - look for any key that contains "PulseApiEndpoint"
API_ENDPOINT=""
if [ -f "cdk-outputs.json" ]; then
    # Find the first key that contains "PulseApiEndpoint" and get its value
    API_ENDPOINT=$(jq -r '.ApiGatewayStack | to_entries[] | select(.key | contains("PulseApiEndpoint")) | .value' cdk-outputs.json 2>/dev/null | head -1)
fi

# Alternative: Parse from command output if JSON file method doesn't work
if [ "$API_ENDPOINT" == "null" ] || [ -z "$API_ENDPOINT" ]; then
    API_ENDPOINT=$(echo "$CDK_OUTPUT" | grep -o 'https://[^[:space:]]*execute-api[^[:space:]]*' | head -1)
fi

# If still no endpoint found, try a broader search
if [ -z "$API_ENDPOINT" ] || [ "$API_ENDPOINT" == "null" ]; then
    echo "⚠️  Could not auto-extract API endpoint. Please check CDK output above."
    echo "Please enter the API Gateway URL manually:"
    read -r API_ENDPOINT
fi

# Extract API Key ID from CDK output - look for any key that contains "ApiKey"
API_KEY_ID=""
if [ -f "cdk-outputs.json" ]; then
    # Find the first key that contains "ApiKey" (but not "ApiEndpoint") and get its value
    API_KEY_ID=$(jq -r '.ApiGatewayStack | to_entries[] | select(.key | contains("ApiKey") and (contains("Endpoint") | not)) | .value' cdk-outputs.json 2>/dev/null | head -1)
fi

# Try to extract API Key ID from command output if JSON method fails
if [ "$API_KEY_ID" == "null" ] || [ -z "$API_KEY_ID" ]; then
    # Look for patterns in CDK output that might contain the API Key ID
    API_KEY_ID=$(echo "$CDK_OUTPUT" | grep -o '[a-zA-Z0-9]\{20,\}' | head -1)
fi

# Get the actual API key value using AWS CLI
API_KEY=""
if [ -n "$API_KEY_ID" ] && [ "$API_KEY_ID" != "null" ]; then
    echo "🔑 Retrieving API key value..."
    API_KEY=$(aws apigateway get-api-key --api-key "$API_KEY_ID" --include-value --profile=${AWS_PROFILE} --query 'value' --output text 2>/dev/null || echo "")
    
    if [ -z "$API_KEY" ] || [ "$API_KEY" == "None" ]; then
        echo "⚠️  Could not retrieve API key value automatically."
        echo "Please enter your API key manually (or press Enter if none needed):"
        read -r API_KEY
    fi
else
    echo "⚠️  Could not find API Key ID in CDK output."
    echo "Please enter your API key manually (or press Enter if none needed):"
    read -r API_KEY
fi

echo "📋 API Endpoint: $API_ENDPOINT"
if [ -n "$API_KEY" ]; then
    echo "🔑 API Key: ${API_KEY:0:10}..." # Only show first 10 chars
else
    echo "🔑 API Key: Not configured"
fi
echo ""

# Step 3: Generate the config file
echo "⚙️  Generating frontend configuration..."
cat > packages/frontend/pulse-config.js << EOF
export const config = {
    "apiKey": "$API_KEY",
    "apiBaseUrl": "$API_ENDPOINT"
};
EOF

echo "✅ Frontend configured with backend API"
echo ""

# Step 4: Start the frontend server
echo "🌐 Starting frontend server..."
echo "Frontend will be available at: http://localhost:3000"
echo ""
echo "📋 Demo is ready! The browser should open automatically."
echo "   Backend API: $API_ENDPOINT"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the demo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Clean up temp files
rm -f cdk-outputs.json

# Open browser (try different methods for cross-platform support)
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000 &
elif command -v open &> /dev/null; then
    open http://localhost:3000 &
elif command -v start &> /dev/null; then
    start http://localhost:3000 &
fi

# Start the server (this will block until Ctrl+C)
cd packages/frontend
serve -s . -p 3000