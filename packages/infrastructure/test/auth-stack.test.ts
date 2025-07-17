import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { AuthStack } from '../lib/auth-stack';
import { InfrastructureStack } from '../lib/infrastructure-stack';

describe('AuthStack', () => {
  let app: cdk.App;
  let infraStack: InfrastructureStack;
  let authStack: AuthStack;
  let template: Template;

  beforeAll(() => {
    app = new cdk.App();
    
    // Create infrastructure stack first (for usersTable dependency)
    infraStack = new InfrastructureStack(app, 'TestInfraStack', {
      env: { account: '123456789012', region: 'us-east-1' }
    });
    
    // Create auth stack
    authStack = new AuthStack(app, 'TestAuthStack', {
      env: { account: '123456789012', region: 'us-east-1' },
      usersTable: infraStack.usersTable
    });
    
    template = Template.fromStack(authStack);
  });

  test('Creates Cognito User Pool with correct configuration', () => {
    template.hasResourceProperties('AWS::Cognito::UserPool', {
      UserPoolName: 'ps-user-pool',
      AutoVerifiedAttributes: ['email'],
      Policies: {
        PasswordPolicy: {
          MinimumLength: 8,
          RequireLowercase: true,
          RequireUppercase: true,
          RequireNumbers: true,
          RequireSymbols: false,
        }
      },
      UsernameAttributes: ['email'],
      AccountRecoverySetting: {
        RecoveryMechanisms: [
          {
            Name: 'verified_email',
            Priority: 1
          }
        ]
      }
    });
  });

  test('Creates User Pool Client with correct settings', () => {
    template.hasResourceProperties('AWS::Cognito::UserPoolClient', {
      ClientName: 'ps-web-client',
      PreventUserExistenceErrors: 'ENABLED',
      RefreshTokenValidity: 30,
      AccessTokenValidity: 1,
      IdTokenValidity: 1,
    });
  });

  test('Outputs are created', () => {
    const outputs = template.toJSON().Outputs;
    expect(outputs).toHaveProperty('UserPoolId');
    expect(outputs).toHaveProperty('UserPoolClientId');
    expect(outputs).toHaveProperty('UserPoolArn');
  });
});