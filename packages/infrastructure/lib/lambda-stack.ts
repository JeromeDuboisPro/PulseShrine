import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import * as path from 'path';

interface LambdaStackProps extends cdk.StackProps {
    startPulseTable: dynamodb.ITable;
    stopPulseTable: dynamodb.ITable;
    ingestedPulseTable: dynamodb.ITable;
    pulsesIngestionQueue: sqs.IQueue;
    pulsesIngestionQueueDLQ: sqs.IQueue;
}

export class LambdaStack extends cdk.Stack {
    public readonly pythonStartFunction: PythonFunction;
    public readonly pythonStopFunction: PythonFunction;
    public readonly pythonIngestPulseFunction: PythonFunction;

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

        this.pythonIngestPulseFunction = new PythonFunction(this, 'IngestPulse', {
            ...commonLambdaProps,
            entry: path.resolve('../backend/src/handlers/events/ingest_pulse'),
            timeout: cdk.Duration.seconds(60),
            functionName: 'ps-ingest-pulse',
            description: 'Function to ingest pulses',
            logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
            layers: [sharedLayer],
            environment: {
                STOP_PULSE_TABLE_NAME: props.stopPulseTable.tableName,
                INGESTED_PULSE_TABLE_NAME: props.ingestedPulseTable.tableName,
                SQS_QUEUE_ARN: props.pulsesIngestionQueue.queueArn,
                SQS_DLQ_ARN: props.pulsesIngestionQueueDLQ.queueArn,
            },
            bundling: {
                assetExcludes: bundlingAssetExcludes
            },
        });

        props.stopPulseTable.grantWriteData(this.pythonIngestPulseFunction);
        props.ingestedPulseTable.grantWriteData(this.pythonIngestPulseFunction);
        props.pulsesIngestionQueue.grantConsumeMessages(this.pythonIngestPulseFunction);

        this.pythonIngestPulseFunction.addEventSource(
            new SqsEventSource(props.pulsesIngestionQueue, {
                batchSize: 20,
                maxBatchingWindow: cdk.Duration.seconds(10),
                enabled: true,
                maxConcurrency: 2,
            })
        );
    }
}