import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

export class InfrastructureStack extends cdk.Stack {
  startPulseTable: cdk.aws_dynamodb.Table;
  stopPulseTable: cdk.aws_dynamodb.Table;
  ingestedPulseTable: cdk.aws_dynamodb.Table;
  aiUsageTrackingTable: cdk.aws_dynamodb.Table;
  pulsesIngestionQueue: cdk.aws_sqs.Queue;
  pulsesIngestionQueueDLQ: cdk.aws_sqs.Queue;
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const startPulseTable = new dynamodb.Table(this, "PulseTable", {
      tableName: "start-pulse-table",
      partitionKey: { name: "user_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });

    const stopPulseTable = new dynamodb.Table(this, "StopPulseTable", {
      tableName: "stop-pulse-table",
      partitionKey: { name: "pulse_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      stream: dynamodb.StreamViewType.NEW_IMAGE,
    });

    stopPulseTable.addGlobalSecondaryIndex({
      indexName: "UserIdIndex",
      partitionKey: {
        name: "user_id",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: { name: "stopped_at", type: dynamodb.AttributeType.STRING },
    });

    const ingestedPulseTable = new dynamodb.Table(this, "IngestedPulseTable", {
      tableName: "ingested-pulse-table",
      partitionKey: { name: "pulse_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });

    // Add a Global Secondary Index to allow access by user_id and sorting by stopped_at
    ingestedPulseTable.addGlobalSecondaryIndex({
      indexName: "UserIdStoppedAtIndex",
      partitionKey: { name: "user_id", type: dynamodb.AttributeType.STRING },
      sortKey: {
        name: "inverted_timestamp",
        type: dynamodb.AttributeType.NUMBER,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // AI Usage Tracking Table for budget and gamification
    const aiUsageTrackingTable = new dynamodb.Table(
      this,
      "AIUsageTrackingTable",
      {
        tableName: "ai-usage-tracking",
        partitionKey: { name: "user_id", type: dynamodb.AttributeType.STRING },
        sortKey: { name: "date", type: dynamodb.AttributeType.STRING }, // YYYY-MM-DD format
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        timeToLiveAttribute: "ttl", // Auto-cleanup old records
      },
    );

    // GSI for monthly tracking
    aiUsageTrackingTable.addGlobalSecondaryIndex({
      indexName: "UserIdMonthIndex",
      partitionKey: { name: "user_id", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "month", type: dynamodb.AttributeType.STRING }, // YYYY-MM format
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Create the DLQ
    const pulsesIngestionQueueDLQ = new sqs.Queue(
      this,
      "pulsesIngestionQueueDLQ",
      {
        queueName: "ps-pulse-ingestion-dlq",
        retentionPeriod: cdk.Duration.days(14),
      },
    );

    // Create the main SQS queue with DLQ
    const pulsesIngestionQueue = new sqs.Queue(this, "pulsesIngestionQueue", {
      queueName: "ps-pulse-ingestion",
      visibilityTimeout: cdk.Duration.seconds(60), // 30s processing, 60s for safety
      deadLetterQueue: {
        maxReceiveCount: 1,
        queue: pulsesIngestionQueueDLQ,
      },
    });

    // Create the DLQ for the DynamoDB Pipe
    const pulsesIngestionDDBDLQ = new sqs.Queue(this, "pulsesIngestionDDBDLQ", {
      queueName: "ps-pulse-ingestion-ddb-dlq",
      retentionPeriod: cdk.Duration.days(14),
    });

    // =====================================================
    // Parameter Store setup for AI configuration
    // =====================================================
    const aiParameters = {
      targetPercentage: new ssm.StringParameter(this, "AITargetPercentage", {
        parameterName: "/pulseshrine/ai/target_percentage",
        stringValue: "0.10",
        description: "Target percentage of pulses to enhance with AI",
      }),
      durationWeight: new ssm.StringParameter(this, "AIDurationWeight", {
        parameterName: "/pulseshrine/ai/duration_weight",
        stringValue: "0.4",
        description: "Weight for session duration in AI selection",
      }),
      reflectionWeight: new ssm.StringParameter(this, "AIReflectionWeight", {
        parameterName: "/pulseshrine/ai/reflection_weight",
        stringValue: "0.3",
        description: "Weight for reflection quality in AI selection",
      }),
      intentWeight: new ssm.StringParameter(this, "AIIntentWeight", {
        parameterName: "/pulseshrine/ai/intent_weight",
        stringValue: "0.2",
        description: "Weight for intent type in AI selection",
      }),
      maxCostCents: new ssm.StringParameter(this, "AIMaxCostCents", {
        parameterName: "/pulseshrine/ai/max_cost_per_pulse_cents",
        stringValue: "2",
        description: "Maximum cost per pulse in cents",
      }),
      enabled: new ssm.StringParameter(this, "AIEnabled", {
        parameterName: "/pulseshrine/ai/enabled",
        stringValue: "true",
        description: "Enable/disable AI enhancement",
      }),
      bedrockModelId: new ssm.StringParameter(this, "AIBedrockModelId", {
        parameterName: "/pulseshrine/ai/bedrock_model_id",
        stringValue: "amazon.titan-text-express-v1", // Default - backend will use region-appropriate model
        description:
          "Bedrock model ID for AI enhancement (region-appropriate default)",
      }),
    };

    // Note: EventBridge Pipe moved to SfnStack to connect DynamoDB stream to Step Functions

    this.startPulseTable = startPulseTable;
    this.stopPulseTable = stopPulseTable;
    this.ingestedPulseTable = ingestedPulseTable;
    this.aiUsageTrackingTable = aiUsageTrackingTable;
    this.pulsesIngestionQueue = pulsesIngestionQueue;
    this.pulsesIngestionQueueDLQ = pulsesIngestionQueueDLQ;
  }
}
