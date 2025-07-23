#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ApiGatewayStack } from '../lib/api-gateway-stack';
import { AuthStack } from '../lib/auth-stack';
import { FrontendStack } from '../lib/frontend-stack';
import { InfrastructureStack } from '../lib/infrastructure-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { SfnStack } from '../lib/sfn-stack';

const app = new cdk.App();

// Get environment from env var
const environment = process.env.ENVIRONMENT || 'dev';

const infraStack = new InfrastructureStack(app, 'InfrastructureStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
  environment,
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
  environment,
});

// AuthStack depends on InfrastructureStack for usersTable and LambdaStack for postConfirmationFunction
const authStack = new AuthStack(app, 'AuthStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
  usersTable: infraStack.usersTable,
  postConfirmationFunction: lambdaStack.postConfirmationFunction,
  environment,
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
  pureIngestFunction: lambdaStack.pureIngestFunction,
  environment,
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
  subscriptionFunction: lambdaStack.subscriptionFunction,
  userPool: authStack.userPool,
  environment,
});

// =====================================================
// Environment Configuration
// =====================================================

// const environment is already declared above
const market = process.env.MARKET || 'global'; // 'global' for .com, 'fr' for .fr

const domainConfig = {
  global: {
    dev: {
      domainName: 'pulseshrine.com',
      subdomain: 'app.dev',
      apiSubdomain: 'api.dev',
      // Results in: app.dev.pulseshrine.com, api.dev.pulseshrine.com
    },
    stag: {
      domainName: 'pulseshrine.com',
      subdomain: 'app.stag',
      apiSubdomain: 'api.stag',
      // Results in: app.stag.pulseshrine.com, api.stag.pulseshrine.com
    },
    prod: {
      domainName: 'pulseshrine.com',
      subdomain: 'app',
      apiSubdomain: 'api',
      // Results in: app.pulseshrine.com, api.pulseshrine.com
    }
  },
  fr: {
    dev: {
      domainName: 'pulseshrine.fr',
      subdomain: 'app.dev',
      apiSubdomain: 'api.dev',
      // Results in: app.dev.pulseshrine.fr, api.dev.pulseshrine.fr
    },
    stag: {
      domainName: 'pulseshrine.fr',
      subdomain: 'app.stag',
      apiSubdomain: 'api.stag',
      // Results in: app.stag.pulseshrine.fr, api.stag.pulseshrine.fr
    },
    prod: {
      domainName: 'pulseshrine.fr',
      subdomain: 'app',
      apiSubdomain: 'api',
      // Results in: app.pulseshrine.fr, api.pulseshrine.fr
    }
  }
};

const marketConfig = domainConfig[market as keyof typeof domainConfig];
const currentDomainConfig = marketConfig?.[environment as keyof typeof marketConfig];

// FrontendStack for website hosting and CDN
// Skip domain configuration for dev environment to avoid hosted zone requirements
new FrontendStack(app, 'FrontendStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
  environment,
  domainName: environment === 'dev' ? undefined : currentDomainConfig?.domainName,
  subdomain: environment === 'dev' ? undefined : currentDomainConfig?.subdomain,
});