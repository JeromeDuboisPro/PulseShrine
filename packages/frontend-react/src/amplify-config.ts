import { Amplify } from 'aws-amplify';

// Configuration interface
export interface AmplifyConfig {
  region: string;
  userPoolId: string;
  userPoolWebClientId: string;
  apiGatewayUrl: string;
}

// Environment-based configuration
const getAmplifyConfig = (): AmplifyConfig => {
  
  // Environment variables from Vite
  const config: AmplifyConfig = {
    region: import.meta.env.VITE_AWS_REGION || 'us-east-1',
    userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
    userPoolWebClientId: import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID || '',
    apiGatewayUrl: import.meta.env.VITE_API_BASE_URL || '',
  };

  // Validate required configuration
  const requiredFields = ['userPoolId', 'userPoolWebClientId', 'apiGatewayUrl'];
  const missingFields = requiredFields.filter(field => !config[field as keyof AmplifyConfig]);
  
  if (missingFields.length > 0) {
    console.warn(`Missing Amplify configuration: ${missingFields.join(', ')}`);
    console.warn('Please set the required environment variables:');
    console.warn('- VITE_COGNITO_USER_POOL_ID');
    console.warn('- VITE_COGNITO_USER_POOL_CLIENT_ID'); 
    console.warn('- VITE_API_BASE_URL');
  }

  return config;
};

// Configure Amplify
export const configureAmplify = () => {
  const config = getAmplifyConfig();
  
  try {
    Amplify.configure({
      Auth: {
        Cognito: {
          userPoolId: config.userPoolId,
          userPoolClientId: config.userPoolWebClientId,
        },
      },
    });
    
    console.log('Amplify configured successfully');
    return config;
  } catch (error) {
    console.error('Failed to configure Amplify:', error);
    throw error;
  }
};

export default getAmplifyConfig;