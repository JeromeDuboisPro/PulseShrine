import * as cdk from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";

interface AuthStackProps extends cdk.StackProps {
  usersTable: dynamodb.ITable;
  postConfirmationFunction: lambda.IFunction;
  environment: string; // 'dev', 'stag', 'prod'
}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    // =====================================================
    // Cognito User Pool
    // =====================================================

    this.userPool = new cognito.UserPool(this, "PulseShrineUserPool", {
      userPoolName: `ps-user-pool-${props.environment}`,
      selfSignUpEnabled: true,
      signInAliases: {
        email: true,
        username: false,
      },
      autoVerify: {
        email: true,
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false, // Keep it simple for MVP
        tempPasswordValidity: cdk.Duration.days(7),
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For development - change for production
      lambdaTriggers: {
        postConfirmation: props.postConfirmationFunction,
      },
    });

    // =====================================================
    // User Pool Client
    // =====================================================

    this.userPoolClient = new cognito.UserPoolClient(
      this,
      "PulseShrineUserPoolClient",
      {
        userPool: this.userPool,
        userPoolClientName: "ps-web-client",
        authFlows: {
          userSrp: true,
          userPassword: true, // For easier testing - disable in production
        },
        preventUserExistenceErrors: true,
        refreshTokenValidity: cdk.Duration.days(30),
        accessTokenValidity: cdk.Duration.hours(1),
        idTokenValidity: cdk.Duration.hours(1),
      },
    );

    // =====================================================
    // Outputs
    // =====================================================

    new cdk.CfnOutput(this, "UserPoolId", {
      value: this.userPool.userPoolId,
      description: "Cognito User Pool ID",
    });

    new cdk.CfnOutput(this, "UserPoolClientId", {
      value: this.userPoolClient.userPoolClientId,
      description: "Cognito User Pool Client ID",
    });

    new cdk.CfnOutput(this, "UserPoolArn", {
      value: this.userPool.userPoolArn,
      description: "Cognito User Pool ARN",
    });
  }
}