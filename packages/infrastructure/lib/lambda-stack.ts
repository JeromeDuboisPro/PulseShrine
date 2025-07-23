import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";
import * as path from "path";

interface LambdaStackProps extends cdk.StackProps {
  startPulseTable: dynamodb.ITable;
  stopPulseTable: dynamodb.ITable;
  ingestedPulseTable: dynamodb.ITable;
  aiUsageTrackingTable: dynamodb.ITable;
  usersTable: dynamodb.ITable;
  bedrockModelId?: string;
  environment: string; // 'dev', 'stag', 'prod'
}

export class LambdaStack extends cdk.Stack {
  public readonly pythonStartFunction: PythonFunction;
  public readonly pythonStopFunction: PythonFunction;
  public readonly pythonGetStartPulseFunction: PythonFunction;
  public readonly pythonGetStopPulsesFunction: PythonFunction;
  public readonly pythonGetIngestedPulsesFunction: PythonFunction;
  public readonly aiSelectionFunction: PythonFunction;
  public readonly bedrockEnhancementFunction: PythonFunction;
  public readonly standardEnhancementFunction: PythonFunction;
  public readonly pureIngestFunction: PythonFunction;
  public readonly postConfirmationFunction: PythonFunction;
  public readonly subscriptionFunction: PythonFunction;

  constructor(scope: Construct, id: string, props: LambdaStackProps) {
    super(scope, id, props);

    // Determine default Bedrock model based on region
    const getDefaultBedrockModel = (region: string): string => {
      const regionModels: { [key: string]: string } = {
        "us-east-1": "us.amazon.nova-lite-v1:0",
        "us-west-2": "us.amazon.nova-lite-v1:0",
        "eu-west-1": "eu.amazon.nova-lite-v1:0",
        "eu-west-3": "eu.amazon.nova-lite-v1:0",
        "ap-southeast-2": "apac.amazon.nova-lite-v1:0",
      };
      return regionModels[region] || "anthropic.claude-3-haiku-20240307-v1:0"; // Universal fallback
    };

    const bedrockModelId =
      props.bedrockModelId || getDefaultBedrockModel(this.region);

    const sharedLayer = new lambda.LayerVersion(this, "SharedLayer", {
      code: lambda.Code.fromAsset("../backend/src/shared/lambda_layer"),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: "Shared dependencies layer",
    });

    // AWS Managed Layer for Powertools
    const awsLambdaPowertoolsLayerArn = `arn:aws:lambda:${this.region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-arm64:18`;

    // X-Ray SDK Layer
    const xrayLayer = new lambda.LayerVersion(this, "XRaySDKLayer", {
      code: lambda.Code.fromAsset("layers/xray-sdk", {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output/python && cp -au . /asset-output/'
          ],
        },
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      compatibleArchitectures: [lambda.Architecture.ARM_64, lambda.Architecture.X86_64],
      description: "AWS X-Ray SDK for Python",
    });

    const bundlingAssetExcludes = [
      "**/__pycache__",
      "**/*.pyc",
      "**/*.pyo",
      "**/*.pyd",
      "**/.pytest_cache",
    ];

    // Cost-optimized Lambda configurations
    const costOptimizedLambdaProps = {
      architecture: lambda.Architecture.ARM_64, // Better price/performance ratio
      runtime: lambda.Runtime.PYTHON_3_13,
      layers: [
        lambda.LayerVersion.fromLayerVersionArn(this, "PowertoolsLayerCostOpt", awsLambdaPowertoolsLayerArn),
        xrayLayer,
        sharedLayer
      ],
      bundling: {
        assetExcludes: bundlingAssetExcludes,
      },
      timeout: cdk.Duration.seconds(10), // Longer timeout for cost optimization
      memorySize: 256, // Start with lower memory for cost savings
    };

    const apiLambdaProps = {
      ...costOptimizedLambdaProps,
      timeout: cdk.Duration.seconds(15), // APIs need reasonable response times
      memorySize: 512, // Balance between cost and user experience
      layers: [
        lambda.LayerVersion.fromLayerVersionArn(this, "PowertoolsLayerApi", awsLambdaPowertoolsLayerArn),
        xrayLayer,
        sharedLayer
      ],
    };

    const enhancementLambdaProps = {
      ...costOptimizedLambdaProps,
      timeout: cdk.Duration.seconds(120), // AI processing can be slower
      memorySize: 1024, // AI workloads may need more memory
      layers: [
        lambda.LayerVersion.fromLayerVersionArn(this, "PowertoolsLayerEnhance", awsLambdaPowertoolsLayerArn),
        xrayLayer,
        sharedLayer
      ],
    };

    // Props for handlers with nested module structure (new pattern)
    const nestedApiProps = {
      ...apiLambdaProps,
      handler: "handler",
    };

    const nestedEnhancementProps = {
      ...enhancementLambdaProps,
      handler: "handler",
    };

    const nestedCostOptimizedProps = {
      ...costOptimizedLambdaProps,
      handler: "handler",
    };

    this.pythonStartFunction = new PythonFunction(this, "StartPulseV1", {
      ...nestedApiProps,
      entry: path.resolve("../backend/src/handlers/api/start_pulse"),
      index: "start_pulse/app.py",
      functionName: `ps-start-pulse-${props.environment}`,
      description: "Function to start pulses",
      logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
      environment: {
        START_PULSE_TABLE_NAME: props.startPulseTable.tableName,
        SUBSCRIPTION_TABLE_NAME: props.usersTable.tableName,
      },
      memorySize: 128
    });

    this.pythonStopFunction = new PythonFunction(this, "StopPulse", {
      ...nestedApiProps,
      entry: path.resolve("../backend/src/handlers/api/stop_pulse"),
      index: "stop_pulse/app.py",
      functionName: `ps-stop-pulse-${props.environment}`,
      description: "Function to stop pulses",
      environment: {
        START_PULSE_TABLE_NAME: props.startPulseTable.tableName,
        STOP_PULSE_TABLE_NAME: props.stopPulseTable.tableName,
      },
      memorySize: 128
    });

    props.startPulseTable.grantReadWriteData(this.pythonStartFunction);
    props.startPulseTable.grantReadWriteData(this.pythonStopFunction);
    props.stopPulseTable.grantReadWriteData(this.pythonStopFunction);
    
    // Grant subscription access to start pulse function
    props.usersTable.grantReadWriteData(this.pythonStartFunction);

    this.pythonGetStartPulseFunction = new PythonFunction(
      this,
      "GetStartPulse",
      {
        ...nestedApiProps,
        entry: path.resolve("../backend/src/handlers/api/get_start_pulse"),
        index: "get_start_pulse/app.py",
        functionName: `ps-get-start-pulse-${props.environment}`,
        description: "Function to get the start pulse",
        logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
        environment: {
          START_PULSE_TABLE_NAME: props.startPulseTable.tableName,
        },
        memorySize: 192
      },
    );
    props.startPulseTable.grantReadData(this.pythonGetStartPulseFunction);

    this.pythonGetStopPulsesFunction = new PythonFunction(
      this,
      "GetStopPulses",
      {
        ...nestedApiProps,
        entry: path.resolve("../backend/src/handlers/api/get_stop_pulse"),
        index: "get_stop_pulse/app.py",
        functionName: `ps-get-stop-pulses-${props.environment}`,
        description: "Function to get the stop pulses",
        logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
        environment: {
          STOP_PULSE_TABLE_NAME: props.stopPulseTable.tableName,
        },
        memorySize: 192
      },
    );
    props.stopPulseTable.grantReadData(this.pythonGetStopPulsesFunction);

    this.pythonGetIngestedPulsesFunction = new PythonFunction(
      this,
      "GetIngestedPulses",
      {
        ...nestedApiProps,
        entry: path.resolve("../backend/src/handlers/api/get_ingested_pulse"),
        index: "get_ingested_pulse/app.py",
        functionName: `ps-get-ingested-pulses-${props.environment}`,
        description: "Function to get the ingested pulses",
        logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
        environment: {
          INGESTED_PULSE_TABLE_NAME: props.ingestedPulseTable.tableName,
        },
        memorySize: 192
      },
    );
    props.ingestedPulseTable.grantReadData(
      this.pythonGetIngestedPulsesFunction,
    );

    // =====================================================
    // AI Enhancement Lambda Functions
    // =====================================================

    // AI Selection Function - determines which pulses get AI enhancement
    this.aiSelectionFunction = new PythonFunction(this, "AISelectionFunction", {
      ...nestedCostOptimizedProps,
      entry: path.resolve("../backend/src/handlers/events/ai_selection"),
      index: "ai_selection/app.py",
      functionName: `ps-ai-selection-${props.environment}`,
      description: "Function to select pulses for AI enhancement",
      timeout: cdk.Duration.seconds(30),
      environment: {
        PARAMETER_PREFIX: "/pulseshrine/ai/",
        AI_USAGE_TRACKING_TABLE_NAME: props.aiUsageTrackingTable.tableName,
        USERS_TABLE_NAME: props.usersTable.tableName,
      },
    });

    // Bedrock Enhancement Function - performs AI enhancement using Bedrock
    this.bedrockEnhancementFunction = new PythonFunction(
      this,
      "BedrockEnhancementFunction",
      {
        ...nestedEnhancementProps,
        entry: path.resolve(
          "../backend/src/handlers/events/bedrock_enhancement",
        ),
        index: "bedrock_enhancement/app.py",
        functionName: `ps-bedrock-enhancement-${props.environment}`,
        description: "Function to enhance pulses using AWS Bedrock",
        // Using cost-optimized settings - AI can be slower for cost savings
        environment: {
          PARAMETER_PREFIX: "/pulseshrine/ai/",
          INGESTED_PULSE_TABLE_NAME: props.ingestedPulseTable.tableName,
          DEFAULT_BEDROCK_MODEL_ID: bedrockModelId,
          AI_USAGE_TRACKING_TABLE_NAME: props.aiUsageTrackingTable.tableName,
          USERS_TABLE_NAME: props.usersTable.tableName,
        },
        memorySize: 256
      },
    );

    // Grant Parameter Store read permissions to AI functions
    const parameterStorePolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
      ],
      resources: [
        `arn:aws:ssm:${this.region}:${this.account}:parameter/pulseshrine/ai/*`,
      ],
    });

    this.aiSelectionFunction.addToRolePolicy(parameterStorePolicy);
    this.bedrockEnhancementFunction.addToRolePolicy(parameterStorePolicy);

    // Grant AI Usage Tracking table access to AI selection function
    props.aiUsageTrackingTable.grantReadWriteData(this.aiSelectionFunction);

    // Grant AI Usage Tracking table access to bedrock enhancement function (for recording usage)
    props.aiUsageTrackingTable.grantReadWriteData(
      this.bedrockEnhancementFunction,
    );

    // Grant Users table read/write access to AI functions (for plan lookup and auto-creating profiles)
    props.usersTable.grantReadWriteData(this.aiSelectionFunction);
    props.usersTable.grantReadWriteData(this.bedrockEnhancementFunction);

    // Grant Bedrock permissions to enhancement function
    this.bedrockEnhancementFunction.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ],
        resources: [
          "arn:aws:bedrock:*:*:foundation-model/*",
          "arn:aws:bedrock:*:*:inference-profile/*"
        ],
      }),
    );

    // Standard Enhancement Function - generates standard titles and badges
    this.standardEnhancementFunction = new PythonFunction(
      this,
      "StandardEnhancementFunction",
      {
        ...nestedCostOptimizedProps,
        entry: path.resolve(
          "../backend/src/handlers/events/standard_enhancement",
        ),
        index: "standard_enhancement/app.py",
        functionName: `ps-standard-enhancement-${props.environment}`,
        description: "Function to generate standard titles and badges",
      },
    );

    // Pure Ingest Function - DynamoDB operations only
    this.pureIngestFunction = new PythonFunction(this, "PureIngestFunction", {
      ...nestedCostOptimizedProps,
      entry: path.resolve("../backend/src/handlers/events/pure_ingest"),
      index: "pure_ingest/app.py",
      functionName: `ps-pure-ingest-${props.environment}`,
      description: "Function to store pulses in DynamoDB",
      environment: {
        STOP_PULSE_TABLE_NAME: props.stopPulseTable.tableName,
        INGESTED_PULSE_TABLE_NAME: props.ingestedPulseTable.tableName,
        USERS_TABLE_NAME: props.usersTable.tableName,
      },
      memorySize: 192
    });

    // =====================================================
    // Post-Confirmation Lambda Function
    // =====================================================

    // Post-Confirmation Function - initializes users after Cognito registration
    this.postConfirmationFunction = new PythonFunction(
      this,
      "PostConfirmationFunction",
      {
        ...nestedCostOptimizedProps,
        entry: path.resolve("../backend/src/handlers/events/post_confirmation"),
        index: "post_confirmation/app.py",
        functionName: `ps-post-confirmation-${props.environment}`,
        description: "Initialize users in DynamoDB after Cognito registration",
        timeout: cdk.Duration.seconds(30),
        environment: {
          USERS_TABLE_NAME: props.usersTable.tableName,
          AI_USAGE_TRACKING_TABLE_NAME: props.aiUsageTrackingTable.tableName,
        },
      },
    );

    // Grant DynamoDB permissions
    props.ingestedPulseTable.grantWriteData(this.bedrockEnhancementFunction);
    props.ingestedPulseTable.grantWriteData(this.pureIngestFunction);
    props.stopPulseTable.grantReadWriteData(this.pureIngestFunction);

    // Grant Users table read/write access to pure ingest function (for stats tracking)
    props.usersTable.grantReadWriteData(this.pureIngestFunction);

    // Grant permissions to post-confirmation function
    props.usersTable.grantReadWriteData(this.postConfirmationFunction);
    props.aiUsageTrackingTable.grantReadWriteData(this.postConfirmationFunction);

    // =====================================================
    // Subscription Management Function
    // =====================================================

    this.subscriptionFunction = new PythonFunction(this, "SubscriptionFunction", {
      ...nestedApiProps,
      entry: path.resolve("../backend/src/handlers/api/subscription"),
      index: "subscription/app.py", 
      functionName: `ps-subscription-${props.environment}`,
      description: "Function to manage user subscriptions and billing",
      timeout: cdk.Duration.seconds(30),
      environment: {
        SUBSCRIPTION_TABLE_NAME: props.usersTable.tableName,
      },
      memorySize: 256
    });

    // Grant subscription function access to users table
    props.usersTable.grantReadWriteData(this.subscriptionFunction);
  }
}
