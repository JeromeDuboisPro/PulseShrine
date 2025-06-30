# PulseShrine Infrastructure

AWS CDK infrastructure for PulseShrine - a serverless productivity tracking application.

## Architecture

- **Backend**: AWS Lambda (Python 3.13) + DynamoDB + Step Functions
- **Event Processing**: DynamoDB Streams → EventBridge Pipes → Step Functions → Lambda chain
- **AI Enhancement**: Bedrock integration with cost-optimized selection

## Stacks

- `InfrastructureStack`: Core infrastructure (DynamoDB tables, S3 buckets)
- `LambdaStack`: Lambda functions and shared layers
- `ApiGatewayStack`: REST API with authentication and CORS
- `SfnStack`: Step Functions workflows for AI processing

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Node.js** 18+ and npm
3. **AWS CDK** installed globally: `npm install -g aws-cdk`
4. **Bedrock Model Access**: Enable these models in AWS Bedrock Console:
   - `us.amazon.nova-lite-v1:0` (primary)
   - `anthropic.claude-3-haiku-20240307-v1:0` (fallback)

## Quick Start

### Automated Deployment (Recommended)

```bash
# One-command deployment with automatic region detection
./scripts/deploy.sh

# With specific AWS profile
AWS_PROFILE=myprofile ./scripts/deploy.sh

# Show deployment help
./scripts/deploy.sh --help
```

### Manual Deployment

```bash
# Install dependencies
npm install

# Deploy all stacks
cdk deploy --all --require-approval never

# Deploy specific stack
cdk deploy LambdaStack
```

## Cost Optimization

### Lambda Power Tuning

```bash
# Deploy power tuning infrastructure
./scripts/deploy-power-tuning.sh

# Run cost optimization tests (takes ~2 hours)
./scripts/test-lambda-costs.sh

# Monitor progress
aws stepfunctions list-executions --state-machine-arn <arn> --status-filter RUNNING
```

Expected cost savings: **40-60%** after optimization.

See `scripts/COST_OPTIMIZATION_GUIDE.md` for detailed instructions.

## Useful Commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `cdk deploy --all`  deploy all stacks
* `cdk diff`    compare deployed stack with current state
* `cdk synth`   emits the synthesized CloudFormation template
* `cdk destroy --all`  cleanup all resources

## Environment Variables

- `BEDROCK_MODEL_ID`: Override default model selection
- `AWS_REGION`: Target deployment region

## Key Resources

- **API Gateway**: `Pulse Service` REST API with throttling and API keys
- **DynamoDB Tables**: `ps-start-pulse`, `ps-stop-pulse`, `ps-ingested-pulse`
- **Lambda Functions**: `ps-ai-selection`, `ps-bedrock-enhancement`, `ps-standard-enhancement`
- **Step Functions**: `ps-ai-ingestion-workflow`

### API Endpoints

- `POST /start-pulse`: Start a new pulse session
- `POST /stop-pulse`: Stop active pulse and trigger AI processing
- `GET /get-start-pulse`: Retrieve active pulse for user
- `GET /get-stop-pulses`: Get completed pulses for user
- `GET /get-ingested-pulses`: Get AI-enhanced pulses for user
