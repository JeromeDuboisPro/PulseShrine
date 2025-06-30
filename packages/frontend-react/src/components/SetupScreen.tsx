import React, { useState } from 'react';
import { Settings, ExternalLink, CheckCircle, Sparkles } from 'lucide-react';
import { ApiConfig } from '../config';
import { PulseShrineLogoSvg } from './PulseShrineLogoSvg';

interface SetupScreenProps {
  onConfigured: (config: ApiConfig) => void;
}

export const SetupScreen: React.FC<SetupScreenProps> = ({ onConfigured }) => {
  const [apiKey, setApiKey] = useState('');
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [userId, setUserId] = useState('jerome');
  const [isValid, setIsValid] = useState(false);

  // Check if configuration looks valid
  React.useEffect(() => {
    const keyValid = apiKey.length > 10;
    const urlValid = apiBaseUrl.includes('amazonaws.com') && apiBaseUrl.includes('https://');
    const userValid = userId.length > 0;
    setIsValid(keyValid && urlValid && userValid);
  }, [apiKey, apiBaseUrl, userId]);

  const handleSubmit = () => {
    if (isValid) {
      const config: ApiConfig = {
        apiKey: apiKey.trim(),
        apiBaseUrl: apiBaseUrl.trim(),
        userId: userId.trim()
      };
      
      // Save to localStorage
      try {
        localStorage.setItem('pulseshrine-config', JSON.stringify(config));
      } catch (error) {
        console.warn('Failed to save config to localStorage:', error);
      }
      
      // Notify parent
      onConfigured(config);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full">
        
        {/* Header */}
        <div className="p-8 border-b border-gray-200 text-center">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <PulseShrineLogoSvg size={64} className="drop-shadow-lg transition-transform duration-300 hover:scale-110" />
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
              PulseShrine
            </h1>
          </div>
          <p className="text-gray-600 text-lg">Mindful Space of Focused Productivity</p>
          <p className="text-sm text-gray-500 mt-2">Please configure your AWS API connection to begin</p>
        </div>

        {/* Instructions */}
        <div className="p-6 bg-blue-50 border-b border-blue-200">
          <h3 className="font-semibold text-blue-800 mb-3 flex items-center">
            <Settings className="w-5 h-5 mr-2" />
            📋 How to get your API configuration:
          </h3>
          <ol className="text-sm text-blue-700 space-y-2 list-decimal list-inside">
            <li>Deploy your CDK stack: <code className="bg-blue-100 px-2 py-1 rounded font-mono">cdk deploy --all</code></li>
            <li>Look for outputs like:</li>
          </ol>
          <div className="bg-blue-100 rounded-lg p-3 mt-3 font-mono text-xs">
            <div className="text-green-600">✅ InfrastructureStack</div>
            <div className="text-gray-700 mt-1">
              <strong>ApiGatewayRestApiEndpoint</strong> = https://abc123.execute-api.us-east-1.amazonaws.com/prod<br/>
              <strong>ApiKey</strong> = abc123def456ghi789jkl
            </div>
          </div>
          <p className="text-xs text-blue-600 mt-2">
            Or check AWS Console → API Gateway → Your API → Stages → prod
          </p>
        </div>

        {/* Form */}
        <div className="p-8 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🔑 API Key
            </label>
            <input
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="abc123def456ghi789jkl..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              From CDK output or AWS Console → API Gateway → API Keys
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🌐 API Base URL
            </label>
            <input
              type="url"
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              placeholder="https://abc123.execute-api.us-east-1.amazonaws.com/prod"
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              From CDK output or AWS Console → API Gateway → Stages → prod → Invoke URL
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              👤 User ID
            </label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="jerome"
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Unique identifier for your focus data (default: jerome)
            </p>
          </div>

          {/* Validation Status */}
          {isValid ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center space-x-3">
              <CheckCircle className="w-6 h-6 text-green-600" />
              <div>
                <span className="text-green-800 font-medium">Configuration looks good!</span>
                <p className="text-green-700 text-sm">Ready to connect to your AWS Lambda backend</p>
              </div>
            </div>
          ) : (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-amber-800 text-sm">
                ⚠️ Please fill in all fields. API URL should be a valid AWS API Gateway URL starting with https://
              </p>
            </div>
          )}

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={!isValid}
            className="w-full bg-gradient-to-r from-purple-500 to-blue-500 text-white py-4 px-6 rounded-lg font-semibold hover:from-purple-600 hover:to-blue-600 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            <Sparkles className="w-5 h-5" />
            <span>Connect to PulseShrine</span>
          </button>

          {/* Help Links */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-800 mb-2">Need help?</h4>
            <div className="space-y-2 text-sm">
              <a 
                href="https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-call-api.html"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 text-blue-600 hover:text-blue-800"
              >
                <ExternalLink className="w-4 h-4" />
                <span>AWS API Gateway Documentation</span>
              </a>
              <p className="text-gray-600">
                Check the JURY_TESTING_GUIDE.md for detailed instructions
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};