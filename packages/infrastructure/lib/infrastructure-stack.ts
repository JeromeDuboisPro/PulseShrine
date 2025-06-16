import * as pipes from '@aws-cdk/aws-pipes-alpha';
import * as sources from '@aws-cdk/aws-pipes-sources-alpha';
import * as targets from '@aws-cdk/aws-pipes-targets-alpha';
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';


export class InfrastructureStack extends cdk.Stack {
  startPulseTable: cdk.aws_dynamodb.Table;
  stopPulseTable: cdk.aws_dynamodb.Table;
  ingestedPulseTable: cdk.aws_dynamodb.Table;
  pulsesIngestionQueue: cdk.aws_sqs.Queue;
  pulsesIngestionQueueDLQ: cdk.aws_sqs.Queue;
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const startPulseTable = new dynamodb.Table(this, 'PulseTable', {
      tableName: 'start-pulse-table',
      partitionKey: { name: 'user_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });

    const stopPulseTable = new dynamodb.Table(this, 'StopPulseTable', {
      tableName: 'stop-pulse-table',
      partitionKey: { name: 'pulse_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      stream: dynamodb.StreamViewType.NEW_IMAGE,
    });

    stopPulseTable.addGlobalSecondaryIndex({
      indexName: "UserIdIndex",
      partitionKey: {
        name: "user_id",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: { name: "stopped_at", type: dynamodb.AttributeType.STRING }
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

    // Create the DLQ for the DynamoDB Pipe
    const pulsesIngestionDDBDLQ = new sqs.Queue(this, 'pulsesIngestionDDBDLQ', {
      queueName: 'ps-pulse-ingestion-ddb-dlq',
      retentionPeriod: cdk.Duration.days(14),
    });

    // Create the DynamoDB source
    const pipeSourceV0 = new sources.DynamoDBSource(stopPulseTable, {
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

    new pipes.Pipe(this, 'StopPulseToSqsPipeV1', {
      pipeName: 'stop-pulse-to-sqs-pipe',
      source: pipeSourceV0,
      target: pipeTarget,
      filter: sourceFilter, // Apply the filter
    });

    this.startPulseTable = startPulseTable;
    this.stopPulseTable = stopPulseTable;
    this.ingestedPulseTable = ingestedPulseTable;
    this.pulsesIngestionQueue = pulsesIngestionQueue;
    this.pulsesIngestionQueueDLQ = pulsesIngestionQueueDLQ;

  }
}
