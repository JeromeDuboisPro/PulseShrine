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
    stopPulseTableV1: dynamodb.ITable;
    ingestedPulseTable: dynamodb.ITable;
    pulsesIngestionQueue: sqs.IQueue;
    pulsesIngestionQueueDLQ: sqs.IQueue;
}

export class LambdaStack extends cdk.Stack {
    public readonly pythonStartStopFunction: PythonFunction;
    public readonly pythonIngestPulseFunction: PythonFunction;

    constructor(scope: Construct, id: string, props: LambdaStackProps) {
        super(scope, id, props);

        const sharedLayer = new lambda.LayerVersion(this, 'SharedLayer', {
            code: lambda.Code.fromAsset('../backend/src/shared/lambda_layer'),
            compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
            description: 'Shared dependencies layer',
        });

        this.pythonStartStopFunction = new PythonFunction(this, 'StartPulse', {
            entry: path.resolve('../backend/src/handlers/api/start_pulse'),
            index: 'app.py',
            handler: 'handler',
            architecture: lambda.Architecture.ARM_64,
            runtime: lambda.Runtime.PYTHON_3_13,
            timeout: cdk.Duration.seconds(5),
            functionName: 'ps-start-stop-pulse',
            description: 'Function to start & stop pulses',
            logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,

            layers: [sharedLayer],
            environment: {
                START_PULSE_TABLE_NAME: props.startPulseTable.tableName,
                STOP_PULSE_TABLE_NAME: props.stopPulseTableV1.tableName,
            },
            bundling: {
                assetExcludes: [
                    '**/__pycache__',
                    '**/*.pyc',
                    '**/*.pyo',
                    '**/*.pyd',
                ]
            },
        });

        props.startPulseTable.grantReadWriteData(this.pythonStartStopFunction);
        props.stopPulseTableV1.grantReadWriteData(this.pythonStartStopFunction);

        this.pythonIngestPulseFunction = new PythonFunction(this, 'IngestPulse', {
            entry: path.resolve('../backend/src/handlers/events/ingest_pulse'),
            index: 'app.py',
            handler: 'handler',
            architecture: lambda.Architecture.ARM_64,
            runtime: lambda.Runtime.PYTHON_3_13,
            timeout: cdk.Duration.seconds(60),
            functionName: 'ps-ingest-pulse',
            description: 'Function to ingest pulses',
            logRetention: cdk.aws_logs.RetentionDays.FIVE_DAYS,
            layers: [sharedLayer],
            environment: {
                STOP_PULSE_TABLE_NAME: props.stopPulseTableV1.tableName,
                INGESTED_PULSE_TABLE_NAME: props.ingestedPulseTable.tableName,
                SQS_QUEUE_ARN: props.pulsesIngestionQueue.queueArn,
                SQS_DLQ_ARN: props.pulsesIngestionQueueDLQ.queueArn,
            },
            bundling: {
                assetExcludes: [
                    '**/__pycache__/**',
                    '**/*.pyc',
                    '**/*.pyo',
                    '**/*.pyd',
                ]
            },
        });

        props.stopPulseTableV1.grantWriteData(this.pythonIngestPulseFunction);
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