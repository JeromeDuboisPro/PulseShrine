#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ApiGatewayStack } from '../lib/api-gateway-stack';
import { AuthStack } from '../lib/auth-stack';
import { InfrastructureStack } from '../lib/infrastructure-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { SfnStack } from '../lib/sfn-stack';

const app = new cdk.App();
const infraStack = new InfrastructureStack(app, 'InfrastructureStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
});

// AuthStack depends on InfrastructureStack for usersTable
const authStack = new AuthStack(app, 'AuthStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
  usersTable: infraStack.usersTable,
});

// LambdaStack depends on resources from InfrastructureStack
const lambdaStack = new LambdaStack(app, 'LambdaStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
  startPulseTable: infraStack.startPulseTable,
  stopPulseTable: infraStack.stopPulseTable,
  ingestedPulseTable: infraStack.ingestedPulseTable,
  aiUsageTrackingTable: infraStack.aiUsageTrackingTable,
  usersTable: infraStack.usersTable,
  bedrockModelId: process.env.BEDROCK_MODEL_ID, // Allow override via env var
});

// SfnStack depends on both InfrastructureStack and LambdaStack
const sfnStack = new SfnStack(app, 'SfnStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
  stopPulseTable: infraStack.stopPulseTable,
  ingestedPulseTable: infraStack.ingestedPulseTable,
  pulsesIngestionDDBDLQ: infraStack.pulsesIngestionDDBDLQ,
  aiSelectionFunction: lambdaStack.aiSelectionFunction,
  bedrockEnhancementFunction: lambdaStack.bedrockEnhancementFunction,
  standardEnhancementFunction: lambdaStack.standardEnhancementFunction,
  pureIngestFunction: lambdaStack.pureIngestFunction
});

new ApiGatewayStack(app, 'ApiGatewayStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
  pythonGetStartPulseFunction: lambdaStack.pythonGetStartPulseFunction,
  pythonGetStopPulsesFunction: lambdaStack.pythonGetStopPulsesFunction,
  pythonGetIngestedPulsesFunction: lambdaStack.pythonGetIngestedPulsesFunction,
  pythonStartFunction: lambdaStack.pythonStartFunction,
  pythonStopFunction: lambdaStack.pythonStopFunction,
});