import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import * as path from 'path';

interface LambdaStackProps extends cdk.StackProps {
    startPulseTable: dynamodb.ITable;
    stopPulseTable: dynamodb.ITable;
    ingestedPulseTable: dynamodb.ITable;
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

    constructor(scope: Construct, id: string, props: LambdaStackProps) {
        super(scope, id, props);

        const sharedLayer = new lambda.LayerVersion(this, 'SharedLayer', {
            code: lambda.Code.fromAsset('../backend/src/shared/lambda_layer'),
            compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
            description: 'Shared dependencies layer',

        });

        const bundlingAssetExcludes = [
            '**/__pycache__',
            '**/*.pyc',
            '**/*.pyo',
            '**/*.pyd',
            '**/.pytest_cache'
        ]

        const commonLambdaProps = {
            index: 'app.py',
            handler: 'handler',
            architecture: lambda.Architecture.ARM_64,
            runtime: lambda.Runtime.PYTHON_3_13,
            layers: [sharedLayer],
            bundling: {
                assetExcludes: bundlingAssetExcludes
            },
            timeout: cdk.Duration.seconds(5),
            memorySize: 1024,
        }

        this.pythonStartFunction = new PythonFunction(this, 'StartPulseV1', {
            ...commonLambdaProps,
            entry: path.resolve('../backend/src/handlers/api/start_pulse'),
            functionName: 'ps-start-pulse',
            description: 'Function to start pulses',
            logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
            environment: {
                START_PULSE_TABLE_NAME: props.startPulseTable.tableName,
            },
        });

        this.pythonStopFunction = new PythonFunction(this, 'StopPulse', {
            entry: path.resolve('../backend/src/handlers/api/stop_pulse'),
            ...commonLambdaProps,
            functionName: 'ps-stop-pulse',
            description: 'Function to stop pulses',
            environment: {
                START_PULSE_TABLE_NAME: props.startPulseTable.tableName,
                STOP_PULSE_TABLE_NAME: props.stopPulseTable.tableName,
            },
        });

        props.startPulseTable.grantReadWriteData(this.pythonStartFunction);
        props.startPulseTable.grantReadWriteData(this.pythonStopFunction);
        props.stopPulseTable.grantReadWriteData(this.pythonStopFunction);

        this.pythonGetStartPulseFunction = new PythonFunction(this, 'GetStartPulse', {
            ...commonLambdaProps,
            entry: path.resolve('../backend/src/handlers/api/get_start_pulse'),
            functionName: 'ps-get-start-pulse',
            description: 'Function to get the start pulse',
            logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
            environment: {
                START_PULSE_TABLE_NAME: props.startPulseTable.tableName,
            },
        });
        props.startPulseTable.grantReadData(this.pythonGetStartPulseFunction);

        this.pythonGetStopPulsesFunction = new PythonFunction(this, 'GetStopPulses', {
            ...commonLambdaProps,
            entry: path.resolve('../backend/src/handlers/api/get_stop_pulse'),
            functionName: 'ps-get-stop-pulses',
            description: 'Function to get the stop pulses',
            logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
            environment: {
                STOP_PULSE_TABLE_NAME: props.stopPulseTable.tableName,
            },
        });
        props.stopPulseTable.grantReadData(this.pythonGetStopPulsesFunction);

        this.pythonGetIngestedPulsesFunction = new PythonFunction(this, 'GetIngestedPulses', {
            ...commonLambdaProps,
            entry: path.resolve('../backend/src/handlers/api/get_ingested_pulse'),
            functionName: 'ps-get-ingested-pulses',
            description: 'Function to get the ingested pulses',
            logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
            environment: {
                INGESTED_PULSE_TABLE_NAME: props.ingestedPulseTable.tableName,
            },
        });
        props.ingestedPulseTable.grantReadData(this.pythonGetIngestedPulsesFunction);

        // =====================================================
        // AI Enhancement Lambda Functions
        // =====================================================

        // AI Selection Function - determines which pulses get AI enhancement
        this.aiSelectionFunction = new PythonFunction(this, 'AISelectionFunction', {
            ...commonLambdaProps,
            entry: path.resolve('../backend/src/handlers/events/ai_selection'),
            functionName: 'ps-ai-selection',
            description: 'Function to select pulses for AI enhancement',
            timeout: cdk.Duration.seconds(30),
            environment: {
                PARAMETER_PREFIX: '/pulseshrine/ai/',
            },
        });

        // Bedrock Enhancement Function - performs AI enhancement using Bedrock
        this.bedrockEnhancementFunction = new PythonFunction(this, 'BedrockEnhancementFunction', {
            ...commonLambdaProps,
            entry: path.resolve('../backend/src/handlers/events/bedrock_enhancement'),
            functionName: 'ps-bedrock-enhancement',
            description: 'Function to enhance pulses using AWS Bedrock',
            timeout: cdk.Duration.seconds(120), // Longer for AI processing
            memorySize: 2048, // More memory for AI workloads
            environment: {
                PARAMETER_PREFIX: '/pulseshrine/ai/',
                INGESTED_PULSE_TABLE_NAME: props.ingestedPulseTable.tableName,
            },
        });

        // Grant Parameter Store read permissions to AI functions
        const parameterStorePolicy = new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['ssm:GetParameter', 'ssm:GetParameters', 'ssm:GetParametersByPath'],
            resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter/pulseshrine/ai/*`],
        });

        this.aiSelectionFunction.addToRolePolicy(parameterStorePolicy);
        this.bedrockEnhancementFunction.addToRolePolicy(parameterStorePolicy);

        // Grant Bedrock permissions to enhancement function
        this.bedrockEnhancementFunction.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream'
            ],
            resources: ['arn:aws:bedrock:*:*:foundation-model/*']
        }));

        // Standard Enhancement Function - generates standard titles and badges
        this.standardEnhancementFunction = new PythonFunction(this, 'StandardEnhancementFunction', {
            ...commonLambdaProps,
            entry: path.resolve('../backend/src/handlers/events/standard_enhancement'),
            functionName: 'ps-standard-enhancement',
            description: 'Function to generate standard titles and badges',
            timeout: cdk.Duration.seconds(30),
        });

        // Pure Ingest Function - DynamoDB operations only
        this.pureIngestFunction = new PythonFunction(this, 'PureIngestFunction', {
            ...commonLambdaProps,
            entry: path.resolve('../backend/src/handlers/events/pure_ingest'),
            functionName: 'ps-pure-ingest',
            description: 'Function to store pulses in DynamoDB',
            timeout: cdk.Duration.seconds(30),
            environment: {
                STOP_PULSE_TABLE_NAME: props.stopPulseTable.tableName,
                INGESTED_PULSE_TABLE_NAME: props.ingestedPulseTable.tableName,
            },
        });

        // Grant DynamoDB permissions
        props.ingestedPulseTable.grantWriteData(this.bedrockEnhancementFunction);
        props.ingestedPulseTable.grantWriteData(this.pureIngestFunction);
        props.stopPulseTable.grantReadWriteData(this.pureIngestFunction);

    }
}