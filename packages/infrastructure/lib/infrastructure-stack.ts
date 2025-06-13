import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import * as pipes from '@aws-cdk/aws-pipes-alpha';
import * as sources from '@aws-cdk/aws-pipes-sources-alpha';
import * as targets from '@aws-cdk/aws-pipes-targets-alpha';
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import * as path from 'path';

export class InfrastructureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const startPulseTable = new dynamodb.Table(this, 'PulseTable', {
      tableName: 'start-pulse-table',
      partitionKey: { name: 'user_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });

    const stopPulseTablev0 = new dynamodb.Table(this, 'StopPulseTable', {
      tableName: 'stop-pulse-table',
      partitionKey: { name: 'user_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      stream: dynamodb.StreamViewType.NEW_IMAGE,
    });

    const stopPulseTable = new dynamodb.Table(this, 'StopPulseTableV4', {
      tableName: 'stop-pulse-table-v4',
      partitionKey: { name: 'pulse_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      stream: dynamodb.StreamViewType.NEW_IMAGE,
    });

    const ingestedPulseTable = new dynamodb.Table(this, 'IngestedPulseTable', {
      tableName: 'ingested-pulse-table',
      partitionKey: { name: 'pulse_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });

    // Add a Global Secondary Index to allow access by user_id and sorting by stopped_at
    ingestedPulseTable.addGlobalSecondaryIndex({
      indexName: 'UserIdStoppedAtIndex',
      partitionKey: { name: 'user_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'inverted_timestamp', type: dynamodb.AttributeType.NUMBER },
      projectionType: dynamodb.ProjectionType.ALL,
    });


    const pythonStartStopFunction = new PythonFunction(this, 'StartPulse', {
      entry: path.resolve('../backend/src'), // directory containing your .py file
      index: 'handlers/api/start_pulse/app.py', // filename (default is 'index.py')
      handler: 'handler', // function name in the .py file
      architecture: lambda.Architecture.ARM_64, // optional, default is x86_64
      runtime: lambda.Runtime.PYTHON_3_13,
      timeout: cdk.Duration.seconds(5), // optional, default is 3 seconds
      functionName: 'ps-start-stop-pulse',
      description: 'Function to start & stop pulses',
      logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
      environment: {
        START_PULSE_TABLE_NAME: startPulseTable.tableName,
        STOP_PULSE_TABLE_NAME: stopPulseTable.tableName,
      },
      bundling: {
        assetExcludes: [
          // Exclude unnecessary files from the bundle
          '**/__pycache__',
          '**/*.pyc',
          '**/*.pyo',
          '**/*.pyd',
          'shared/data',
          'handlers/events',
          'handlers/scheduled',
        ]
      },
    });

    startPulseTable.grantReadWriteData(pythonStartStopFunction);
    stopPulseTable.grantReadWriteData(pythonStartStopFunction);

    // Create the DLQ
    const pulsesIngestionQueueDLQ = new sqs.Queue(this, 'pulsesIngestionQueueDLQ', {
      queueName: 'ps-pulse-ingestion-dlq',
      retentionPeriod: cdk.Duration.days(14),
    });

    // Create the main SQS queue with DLQ
    const pulsesIngestionQueue = new sqs.Queue(this, 'pulsesIngestionQueue', {
      queueName: 'ps-pulse-ingestion',
      visibilityTimeout: cdk.Duration.seconds(60), // 30s processing, 60s for safety
      deadLetterQueue: {
        maxReceiveCount: 1,
        queue: pulsesIngestionQueueDLQ,
      },
    });

    const pythonIngestPulseFunction = new PythonFunction(this, 'IngestPulse', {
      entry: path.resolve('../backend/src'), // directory containing your .py file
      index: 'handlers/events/ingest_pulse/app.py', // filename (default is 'index.py')
      handler: 'handler', // function name in the .py file
      architecture: lambda.Architecture.ARM_64, // optional, default is x86_64
      runtime: lambda.Runtime.PYTHON_3_13,
      timeout: cdk.Duration.seconds(60), // optional, default is 3 seconds
      functionName: 'ps-ingest-pulse',
      description: 'Function to ingest pulses',
      logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
      environment: {
        STOP_PULSE_TABLE_NAME: stopPulseTable.tableName,
        INGESTED_PULSE_TABLE_NAME: ingestedPulseTable.tableName,
        SQS_QUEUE_ARN: pulsesIngestionQueue.queueArn, // will be set after queue creation
        SQS_DLQ_ARN: pulsesIngestionQueueDLQ.queueArn,   // will be set after DLQ creation
      },
      bundling: {
        assetExcludes: [

          // Exclude unnecessary files from the bundle
          '**/__pycache__/**',
          '**/*.pyc',
          '**/*.pyo',
          '**/*.pyd',
          'handlers/api/**',
          'handlers/scheduled/**',
        ]
      },
    });
    stopPulseTable.grantWriteData(pythonIngestPulseFunction);
    ingestedPulseTable.grantWriteData(pythonIngestPulseFunction)
    // Grant Lambda permissions to read from the SQS queue
    pulsesIngestionQueue.grantConsumeMessages(pythonIngestPulseFunction);

    // Add SQS event source to the Lambda function
    pythonIngestPulseFunction.addEventSource(
      new SqsEventSource(pulsesIngestionQueue, {
        batchSize: 20,
        maxBatchingWindow: cdk.Duration.seconds(10),
        enabled: true,
        maxConcurrency: 2,
      })
    );


    // Create the DLQ for the DynamoDB Pipe
    const pulsesIngestionDDBDLQ = new sqs.Queue(this, 'pulsesIngestionDDBDLQ', {
      queueName: 'ps-pulse-ingestion-ddb-dlq',
      retentionPeriod: cdk.Duration.days(14),
    });

    // Create the DynamoDB source
    const pipeSource = new sources.DynamoDBSource(stopPulseTable, {
      startingPosition: sources.DynamoDBStartingPosition.LATEST,
      batchSize: 1,
      deadLetterTarget: pulsesIngestionDDBDLQ,
      maximumRetryAttempts: 1,
    });

    // Create the SQS target
    const pipeTarget = new targets.SqsTarget(pulsesIngestionQueue);

    // Create the filter - correct syntax
    const sourceFilter = new pipes.Filter([
      pipes.FilterPattern.fromObject({
        eventName: ['INSERT'] // Filter for INSERT events only
      })
    ]);

    // Create the pipe
    new pipes.Pipe(this, 'StopPulseToSqsPipe', {
      pipeName: 'stop-pulse-to-sqs-pipe-v1',
      source: pipeSource,
      target: pipeTarget,
      filter: sourceFilter, // Apply the filter
    });

    const api = new cdk.aws_apigateway.RestApi(this, 'PulseApi', {
      restApiName: 'Pulse Service',
      deployOptions: {
        throttlingRateLimit: 5,
        throttlingBurstLimit: 5,
      },
      apiKeySourceType: cdk.aws_apigateway.ApiKeySourceType.HEADER,
    });

    const apiKey = api.addApiKey('PulseApiKey', {
      apiKeyName: 'PulseApiKey',
      value: undefined,
      description: 'API Key for Pulse API',
    });

    const usagePlan = api.addUsagePlan('PulseUsagePlan', {
      name: 'PulseUsagePlan',
      throttle: {
        rateLimit: 5,
        burstLimit: 5,
      },
      quota: {
        limit: 500,
        period: cdk.aws_apigateway.Period.DAY,
      },
    });
    usagePlan.addApiKey(apiKey);
    usagePlan.addApiStage({
      stage: api.deploymentStage,
      api,
    });

    const pulseResource = api.root.addResource('start-pulse');
    pulseResource.addMethod('POST', new cdk.aws_apigateway.LambdaIntegration(pythonStartStopFunction), {
      apiKeyRequired: true,
      requestModels: {
        'application/json': new cdk.aws_apigateway.Model(this, 'StartPulseRequestModel', {
          restApi: api,
          contentType: 'application/json',
          modelName: 'StartPulseRequest',
          schema: {
            type: cdk.aws_apigateway.JsonSchemaType.OBJECT,
            required: ['user_id', 'intent'],
            properties: {
              user_id: { type: cdk.aws_apigateway.JsonSchemaType.STRING },
              start_time: { type: cdk.aws_apigateway.JsonSchemaType.STRING, format: 'date-time' },
              intent: { type: cdk.aws_apigateway.JsonSchemaType.STRING },
              duration_seconds: { type: cdk.aws_apigateway.JsonSchemaType.INTEGER },
              tags: {
                type: cdk.aws_apigateway.JsonSchemaType.ARRAY,
                items: { type: cdk.aws_apigateway.JsonSchemaType.STRING },
              },
              is_public: { type: cdk.aws_apigateway.JsonSchemaType.BOOLEAN },
            },
          },
        }),
      },
    });

    const StopPulseResource = api.root.addResource('stop-pulse');
    StopPulseResource.addMethod('POST', new cdk.aws_apigateway.LambdaIntegration(pythonStartStopFunction), {
      apiKeyRequired: true,
      requestModels: {
        'application/json': new cdk.aws_apigateway.Model(this, 'StopPulseRequestModel', {
          restApi: api,
          contentType: 'application/json',
          modelName: 'StopPulseRequest',
          schema: {
            type: cdk.aws_apigateway.JsonSchemaType.OBJECT,
            required: ['user_id', 'reflexion'],
            properties: {
              user_id: { type: cdk.aws_apigateway.JsonSchemaType.STRING },
              reflexion: { type: cdk.aws_apigateway.JsonSchemaType.STRING },
            },
          },
        }),
      },
    });

    new cdk.CfnOutput(this, 'StartPulseEndpointUrl', {
      value: `${api.url}start-pulse`,
      description: 'URL of the Start Pulse API endpoint',
    });

    new cdk.CfnOutput(this, 'StopPulseEndpointUrl', {
      value: `${api.url}stop-pulse`,
      description: 'URL of the Post Pulse API endpoint',
    });

  }
}
