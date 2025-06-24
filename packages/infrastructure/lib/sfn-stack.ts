import * as pipes from '@aws-cdk/aws-pipes-alpha';
import * as sources from '@aws-cdk/aws-pipes-sources-alpha';
import * as targets from '@aws-cdk/aws-pipes-targets-alpha';
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { Construct } from 'constructs';

interface SfnStackProps extends cdk.StackProps {
    stopPulseTable: dynamodb.ITable;
    ingestedPulseTable: dynamodb.ITable;
    pulsesIngestionDDBDLQ: sqs.IQueue;
    aiSelectionFunction: lambda.IFunction;
    bedrockEnhancementFunction: lambda.IFunction;
    standardEnhancementFunction: lambda.IFunction;
    pureIngestFunction: lambda.IFunction;
}

export class SfnStack extends cdk.Stack {
    public readonly aiIngestionWorkflow: sfn.StateMachine;

    constructor(scope: Construct, id: string, props: SfnStackProps) {
        super(scope, id, props);

        // =====================================================
        // Step Functions Tasks
        // =====================================================

        // AI Selection Task - determines which pulses get AI enhancement
        const aiSelectionTask = new tasks.LambdaInvoke(this, 'AISelectionTask', {
            lambdaFunction: props.aiSelectionFunction,
            payloadResponseOnly: true,
            comment: 'Determine if pulse should be AI-enhanced',
        });

        // Bedrock Enhancement Task - performs AI enhancement using Bedrock
        const bedrockEnhancementTask = new tasks.LambdaInvoke(this, 'BedrockEnhancementTask', {
            lambdaFunction: props.bedrockEnhancementFunction,
            payloadResponseOnly: true,
            comment: 'Enhance pulse with AI using Bedrock',
        });

        // Standard Enhancement Task - generates standard title and badge
        const standardEnhancementTask = new tasks.LambdaInvoke(this, 'StandardEnhancementTask', {
            lambdaFunction: props.standardEnhancementFunction,
            payloadResponseOnly: true,
            comment: 'Generate standard title and badge',
        });

        // Pure Ingest Task - DynamoDB operations only
        const pureIngestTask = new tasks.LambdaInvoke(this, 'PureIngestTask', {
            lambdaFunction: props.pureIngestFunction,
            payloadResponseOnly: true,
            comment: 'Store pulse in DynamoDB',
        });

        // =====================================================
        // Step Functions Workflow Definition
        // =====================================================

        // Create choice condition for AI routing
        const aiWorthyChoice = new sfn.Choice(this, 'IsAIWorthy', {
            comment: 'Route to AI enhancement or standard processing',
        })
            .when(
                sfn.Condition.booleanEquals('$.aiWorthy', true),
                bedrockEnhancementTask.next(pureIngestTask)
            )
            .otherwise(standardEnhancementTask.next(pureIngestTask));

        // Define the complete workflow
        const workflowDefinition = aiSelectionTask.next(aiWorthyChoice);

        // =====================================================
        // Create State Machine
        // =====================================================

        const sFNLogGroup = new cdk.aws_logs.LogGroup(this, 'SfnLogGroup', {
            logGroupName: '/aws/vendedlogs/states/ps-ai-ingestion-workflow',
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            retention: cdk.aws_logs.RetentionDays.ONE_WEEK,
        });

        this.aiIngestionWorkflow = new sfn.StateMachine(this, 'AIIngestionWorkflow', {
            stateMachineType: sfn.StateMachineType.EXPRESS,
            stateMachineName: 'ps-ai-ingestion-workflow',
            definition: workflowDefinition,
            timeout: cdk.Duration.seconds(300),
            comment: 'AI-enhanced pulse ingestion workflow with smart selection',
            logs: {
                destination: sFNLogGroup,
                level: cdk.aws_stepfunctions.LogLevel.ALL,
                includeExecutionData: true,
            },

        });

        // =====================================================
        // Permissions
        // =====================================================

        // Grant Step Functions permission to invoke Lambda functions
        props.aiSelectionFunction.grantInvoke(this.aiIngestionWorkflow.role);
        props.bedrockEnhancementFunction.grantInvoke(this.aiIngestionWorkflow.role);
        props.standardEnhancementFunction.grantInvoke(this.aiIngestionWorkflow.role);
        props.pureIngestFunction.grantInvoke(this.aiIngestionWorkflow.role);

        // =====================================================
        // EventBridge Pipe - DynamoDB Stream to Step Functions
        // =====================================================

        // Create the DynamoDB source
        const pipeSource = new sources.DynamoDBSource(props.stopPulseTable, {
            startingPosition: sources.DynamoDBStartingPosition.LATEST,
            batchSize: 1,
            deadLetterTarget: props.pulsesIngestionDDBDLQ,
            maximumRetryAttempts: 1,
        });

        // Create the Step Functions target
        // Note: For EventBridge Pipes, the DynamoDB stream event is automatically passed as input
        // We use FIRE_AND_FORGET for async processing to avoid blocking the pipe
        const pipeTarget = new targets.SfnStateMachine(this.aiIngestionWorkflow, {
            invocationType: targets.StateMachineInvocationType.FIRE_AND_FORGET,
        });

        // Create the filter - only process INSERT events
        const sourceFilter = new pipes.Filter([
            pipes.FilterPattern.fromObject({
                eventName: ['INSERT'] // Filter for INSERT events only
            })
        ]);

        // Create the EventBridge Pipe
        new pipes.Pipe(this, 'StopPulseToStepFunctionsPipe', {
            pipeName: 'stop-pulse-to-step-functions-pipe',
            source: pipeSource,
            target: pipeTarget,
            filter: sourceFilter,
        });

        // =====================================================
        // Outputs
        // =====================================================

        new cdk.CfnOutput(this, 'AIIngestionWorkflowArn', {
            value: this.aiIngestionWorkflow.stateMachineArn,
            description: 'ARN of the AI ingestion Step Functions workflow',
        });

        new cdk.CfnOutput(this, 'AIIngestionWorkflowName', {
            value: this.aiIngestionWorkflow.stateMachineName,
            description: 'Name of the AI ingestion Step Functions workflow',
        });
    }
}