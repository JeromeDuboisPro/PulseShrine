import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

interface InfrastructureStackProps extends cdk.StackProps {
  environment: string; // 'dev', 'stag', 'prod'
}

export class InfrastructureStack extends cdk.Stack {
  startPulseTable: cdk.aws_dynamodb.Table;
  stopPulseTable: cdk.aws_dynamodb.Table;
  ingestedPulseTable: cdk.aws_dynamodb.Table;
  aiUsageTrackingTable: cdk.aws_dynamodb.Table;
  usersTable: cdk.aws_dynamodb.Table;
  pulsesIngestionDDBDLQ: cdk.aws_sqs.Queue;
  constructor(scope: Construct, id: string, props: InfrastructureStackProps) {
    super(scope, id, props);

    const env = props.environment;

    const startPulseTable = new dynamodb.Table(this, "PulseTable", {
      tableName: `ps-start-pulse-table-${env}`,
      partitionKey: { name: "user_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });

    const stopPulseTable = new dynamodb.Table(this, "StopPulseTable", {
      tableName: `ps-stop-pulse-table-${env}`,
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
      tableName: `ps-ingested-pulse-table-${env}`,
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

    // AI Usage Tracking Table for detailed event tracking
    const aiUsageTrackingTable = new dynamodb.Table(
      this,
      "AIUsageTrackingTable",
      {
        tableName: `ps-ai-usage-tracking-${env}`,
        partitionKey: { name: "PK", type: dynamodb.AttributeType.STRING }, // USER#userId
        sortKey: { name: "SK", type: dynamodb.AttributeType.STRING }, // EVENT#timestamp#eventId or DAILY#date
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        timeToLiveAttribute: "ttl", // Auto-cleanup old records
      },
    );

    // GSI1: Query by date across all users
    aiUsageTrackingTable.addGlobalSecondaryIndex({
      indexName: "GSI1",
      partitionKey: { name: "GSI1PK", type: dynamodb.AttributeType.STRING }, // DATE#YYYY-MM-DD
      sortKey: { name: "GSI1SK", type: dynamodb.AttributeType.STRING }, // USER#userId#timestamp
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // GSI2: Query by pulse ID to get all AI events for a pulse
    aiUsageTrackingTable.addGlobalSecondaryIndex({
      indexName: "GSI2",
      partitionKey: { name: "GSI2PK", type: dynamodb.AttributeType.STRING }, // PULSE#pulseId
      sortKey: { name: "GSI2SK", type: dynamodb.AttributeType.STRING }, // EVENT#timestamp
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Users Table for user profiles and plan management
    const usersTable = new dynamodb.Table(this, "UsersTable", {
      tableName: `ps-users-${env}`,
      partitionKey: { name: "PK", type: dynamodb.AttributeType.STRING }, // USER#userId
      sortKey: { name: "SK", type: dynamodb.AttributeType.STRING }, // PROFILE or PLAN or SETTINGS
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "ttl", // Optional TTL for temporary data
    });

    // Create the DLQ for the DynamoDB Pipe
    const pulsesIngestionDDBDLQ = new sqs.Queue(this, "pulsesIngestionDDBDLQ", {
      queueName: `ps-pulse-ingestion-ddb-dlq-${env}`,
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
    this.usersTable = usersTable;
    this.pulsesIngestionDDBDLQ = pulsesIngestionDDBDLQ;
  }
}
