import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import * as cdk from "aws-cdk-lib";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as cognito from "aws-cdk-lib/aws-cognito";
import { Construct } from "constructs";

interface ApiGatewayStackProps extends cdk.StackProps {
  pythonGetStartPulseFunction: PythonFunction;
  pythonGetStopPulsesFunction: PythonFunction;
  pythonGetIngestedPulsesFunction: PythonFunction;
  pythonStartFunction: PythonFunction;
  pythonStopFunction: PythonFunction;
  subscriptionFunction: PythonFunction;
  userPool: cognito.UserPool;
  environment: string; // 'dev', 'stag', 'prod'
}

export class ApiGatewayStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;

  constructor(scope: Construct, id: string, props: ApiGatewayStackProps) {
    super(scope, id, props);

    const api = new apigateway.RestApi(this, "PulseApi", {
      restApiName: `Pulse Service ${props.environment}`,
      deployOptions: {
        throttlingRateLimit: 100,  // Increased for authenticated users
        throttlingBurstLimit: 200,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          "Content-Type",
          "X-Amz-Date", 
          "Authorization",
          "X-Api-Key",
          "X-Amz-Security-Token",
          "X-Amz-User-Agent"
        ],
      },
    });

    // =====================================================
    // Cognito Authorizer
    // =====================================================

    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(
      this,
      "PulseCognitoAuthorizer",
      {
        cognitoUserPools: [props.userPool],
        authorizerName: "ps-cognito-authorizer",
        identitySource: "method.request.header.Authorization",
      }
    );

    const startPulseResource = api.root.addResource("start-pulse");
    startPulseResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(props.pythonStartFunction),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        requestModels: {
          "application/json": new apigateway.Model(
            this,
            "StartPulseRequestModel",
            {
              restApi: api,
              contentType: "application/json",
              modelName: "StartPulseRequest",
              schema: {
                type: apigateway.JsonSchemaType.OBJECT,
                required: ["intent"],
                properties: {
                  start_time: {
                    type: apigateway.JsonSchemaType.STRING,
                    format: "date-time",
                  },
                  intent: { type: apigateway.JsonSchemaType.STRING },
                  duration_seconds: { type: apigateway.JsonSchemaType.INTEGER },
                  tags: {
                    type: apigateway.JsonSchemaType.ARRAY,
                    items: { type: apigateway.JsonSchemaType.STRING },
                  },
                  is_public: { type: apigateway.JsonSchemaType.BOOLEAN },
                },
              },
            },
          ),
        },
      },
    );

    const stopPulseResource = api.root.addResource("stop-pulse");
    stopPulseResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(props.pythonStopFunction),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        requestModels: {
          "application/json": new apigateway.Model(
            this,
            "StopPulseRequestModel",
            {
              restApi: api,
              contentType: "application/json",
              modelName: "StopPulseRequest",
              schema: {
                type: apigateway.JsonSchemaType.OBJECT,
                required: ["reflexion"],
                properties: {
                  reflexion: { type: apigateway.JsonSchemaType.STRING },
                },
              },
            },
          ),
        },
      },
    );

    const getStartPulseResource = api.root.addResource("get-start-pulse");
    getStartPulseResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(props.pythonGetStartPulseFunction),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        requestParameters: {},  // user_id will be extracted from JWT
      },
    );

    const getStopPulsesResource = api.root.addResource("get-stop-pulses");
    getStopPulsesResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(props.pythonGetStopPulsesFunction),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        requestParameters: {},  // user_id will be extracted from JWT
      },
    );

    const getIngestedPulsesResource = api.root.addResource(
      "get-ingested-pulses",
    );
    getIngestedPulsesResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(props.pythonGetIngestedPulsesFunction),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        requestParameters: {
          "method.request.querystring.nb_items": false, // Optional nb_items as a query parameter
        },  // user_id will be extracted from JWT
      },
    );

    // =====================================================
    // Subscription API Routes
    // =====================================================

    const subscriptionResource = api.root.addResource("subscription");
    
    // GET /subscription - Get user subscription info
    subscriptionResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(props.subscriptionFunction),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
      },
    );

    // POST /subscription/upgrade - Upgrade subscription tier
    const upgradeResource = subscriptionResource.addResource("upgrade");
    upgradeResource.addMethod(
      "POST", 
      new apigateway.LambdaIntegration(props.subscriptionFunction),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        requestModels: {
          "application/json": new apigateway.Model(
            this,
            "SubscriptionUpgradeRequestModel",
            {
              restApi: api,
              contentType: "application/json",
              modelName: "SubscriptionUpgradeRequest",
              schema: {
                type: apigateway.JsonSchemaType.OBJECT,
                required: ["tier"],
                properties: {
                  tier: { 
                    type: apigateway.JsonSchemaType.STRING,
                    enum: ["pro", "enterprise"]
                  },
                  stripe_subscription_id: { type: apigateway.JsonSchemaType.STRING },
                },
              },
            },
          ),
        },
      },
    );

    // GET /subscription/pricing - Get pricing information (public)
    const pricingResource = subscriptionResource.addResource("pricing");
    pricingResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(props.subscriptionFunction),
      {
        // No authorizer - this is public information
      },
    );

    // POST /subscription/create-customer - Create Stripe customer
    const createCustomerResource = subscriptionResource.addResource("create-customer");
    createCustomerResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(props.subscriptionFunction),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        requestModels: {
          "application/json": new apigateway.Model(
            this,
            "CreateCustomerRequestModel",
            {
              restApi: api,
              contentType: "application/json",
              modelName: "CreateCustomerRequest",
              schema: {
                type: apigateway.JsonSchemaType.OBJECT,
                required: ["email"],
                properties: {
                  email: { type: apigateway.JsonSchemaType.STRING },
                },
              },
            },
          ),
        },
      },
    );

    // Add CORS headers to all gateway responses (including 4XX and 5XX)
    const corsResponseParameters = {
      "gatewayresponse.header.Access-Control-Allow-Origin": "'*'",
      "gatewayresponse.header.Access-Control-Allow-Headers": "'*'",
      "gatewayresponse.header.Access-Control-Allow-Methods":
        "'GET,POST,OPTIONS'",
    };

    api.addGatewayResponse("Default4xx", {
      type: apigateway.ResponseType.DEFAULT_4XX,
      responseHeaders: corsResponseParameters,
    });

    api.addGatewayResponse("Default5xx", {
      type: apigateway.ResponseType.DEFAULT_5XX,
      responseHeaders: corsResponseParameters,
    });

    this.api = api;

    // =====================================================
    // Outputs
    // =====================================================

    new cdk.CfnOutput(this, "PulseApiUrl", {
      value: api.url,
      description: "Base URL for the Pulse API",
      exportName: "PulseApiUrl",
    });

    new cdk.CfnOutput(this, "PulseCognitoAuthorizerId", {
      value: cognitoAuthorizer.authorizerId,
      description: "ID of the Cognito authorizer",
    });
  }
}
