import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import * as cdk from "aws-cdk-lib";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import { Construct } from "constructs";

interface ApiGatewayStackProps extends cdk.StackProps {
  pythonGetStartPulseFunction: PythonFunction;
  pythonGetStopPulsesFunction: PythonFunction;
  pythonGetIngestedPulsesFunction: PythonFunction;
  pythonStartFunction: PythonFunction;
  pythonStopFunction: PythonFunction;
}

export class ApiGatewayStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;

  constructor(scope: Construct, id: string, props: ApiGatewayStackProps) {
    super(scope, id, props);

    const api = new apigateway.RestApi(this, "PulseApi", {
      restApiName: "Pulse Service",
      deployOptions: {
        throttlingRateLimit: 5,
        throttlingBurstLimit: 5,
      },
      apiKeySourceType: apigateway.ApiKeySourceType.HEADER,
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: apigateway.Cors.DEFAULT_HEADERS,
      },
    });

    const apiKey = api.addApiKey("PulseApiKey", {
      apiKeyName: "PulseApiKey",
      value: undefined,
      description: "API Key for Pulse API",
    });

    const usagePlan = api.addUsagePlan("PulseUsagePlan", {
      name: "PulseUsagePlan",
      throttle: {
        rateLimit: 10,
        burstLimit: 10,
      },
      quota: {
        limit: 10000,
        period: cdk.aws_apigateway.Period.DAY,
      },
    });
    usagePlan.addApiKey(apiKey);
    usagePlan.addApiStage({
      stage: api.deploymentStage,
      api,
    });

    const startPulseResource = api.root.addResource("start-pulse");
    startPulseResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(props.pythonStartFunction),
      {
        apiKeyRequired: true,
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
                required: ["user_id", "intent"],
                properties: {
                  user_id: { type: apigateway.JsonSchemaType.STRING },
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
        apiKeyRequired: true,
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
                required: ["user_id", "reflexion"],
                properties: {
                  user_id: { type: apigateway.JsonSchemaType.STRING },
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
        apiKeyRequired: true,
        requestParameters: {
          "method.request.querystring.user_id": true, // Require user_id as a query parameter
        },
      },
    );

    const getStopPulsesResource = api.root.addResource("get-stop-pulses");
    getStopPulsesResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(props.pythonGetStopPulsesFunction),
      {
        apiKeyRequired: true,
        requestParameters: {
          "method.request.querystring.user_id": true, // Require user_id as a query parameter
        },
      },
    );

    const getIngestedPulsesResource = api.root.addResource(
      "get-ingested-pulses",
    );
    getIngestedPulsesResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(props.pythonGetIngestedPulsesFunction),
      {
        apiKeyRequired: true,
        requestParameters: {
          "method.request.querystring.user_id": true, // Require user_id as a query parameter
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

    new cdk.CfnOutput(this, "PulseApiKeyOutput", {
      value: apiKey.keyId,
      description: "The API Key for the Pulse API",
      exportName: "PulseApiKey",
    });
  }
}
