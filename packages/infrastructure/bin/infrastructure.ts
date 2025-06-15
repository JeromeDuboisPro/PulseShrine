#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ApiGatewayStack } from '../lib/api-gateway-stack';
import { InfrastructureStack } from '../lib/infrastructure-stack';
import { LambdaStack } from '../lib/lambda-stack';

const app = new cdk.App();
const infraStack = new InfrastructureStack(app, 'InfrastructureStack', {
  //env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },

});

// LambdaStack depends on resources from InfrastructureStack
const lambdaStack = new LambdaStack(app, 'LambdaStack', {
  startPulseTable: infraStack.startPulseTable,
  stopPulseTableV1: infraStack.stopPulseTable,
  ingestedPulseTable: infraStack.ingestedPulseTable,
  pulsesIngestionQueue: infraStack.pulsesIngestionQueue,
  pulsesIngestionQueueDLQ: infraStack.pulsesIngestionQueueDLQ,
});

new ApiGatewayStack(app, 'ApiGatewayStack', {
  pythonStartStopFunction: lambdaStack.pythonStartStopFunction,
});