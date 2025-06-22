import React, { useState, useEffect } from 'react';
import { Settings, ExternalLink, CheckCircle, X } from 'lucide-react';
import { ApiConfig, defaultConfig, updateConfig } from '../config';

interface ConfigurationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigured: (config: ApiConfig) => void;
  currentConfig?: ApiConfig;
}

export const ConfigurationModal: React.FC<ConfigurationModalProps> = ({ 
  isOpen, 
  onClose, 
  onConfigured,
  currentConfig 
}) => {
  // Load current config from localStorage or use provided config
  const getCurrentConfig = () => {
    if (currentConfig) return currentConfig;
    
    try {
      const stored = localStorage.getItem('pulseshrine-config');
      if (stored) {
        return { ...defaultConfig, ...JSON.parse(stored) };
      }
    } catch (error) {
      console.warn('Failed to load config:', error);
    }
    return defaultConfig;
  };

  const initialConfig = getCurrentConfig();
  const [apiKey, setApiKey] = useState(initialConfig.apiKey);
  const [apiBaseUrl, setApiBaseUrl] = useState(initialConfig.apiBaseUrl);
  const [userId, setUserId] = useState(initialConfig.userId);
  const [isValid, setIsValid] = useState(false);

  // Check if configuration looks valid
  useEffect(() => {
    const keyValid = apiKey.length > 10;
    const urlValid = apiBaseUrl.includes('amazonaws.com') && apiBaseUrl.includes('https://');
    const userValid = userId.length > 0;
    setIsValid(keyValid && urlValid && userValid);
  }, [apiKey, apiBaseUrl, userId]);

  // Check if config has changed from original
  const hasChanged = apiKey !== initialConfig.apiKey || 
                    apiBaseUrl !== initialConfig.apiBaseUrl || 
                    userId !== initialConfig.userId;

  const handleSubmit = () => {
    if (isValid) {
      const newConfig: ApiConfig = {
        apiKey: apiKey.trim(),
        apiBaseUrl: apiBaseUrl.trim(),
        userId: userId.trim()
      };
      
      updateConfig(newConfig);
      onConfigured(newConfig);
      onClose();
    }
  };

  const handleCancel = () => {
    // Reset to original values
    setApiKey(initialConfig.apiKey);
    setApiBaseUrl(initialConfig.apiBaseUrl);
    setUserId(initialConfig.userId);
    onClose();
  };

  // Handle clicking outside the modal
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      handleCancel();
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Settings className="w-6 h-6 text-purple-600" />
              <h2 className="text-2xl font-bold text-gray-800">Configure PulseShrine API</h2>
            </div>
            <button
              onClick={handleCancel}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <p className="text-gray-600 mt-2">
            Connect to your AWS Lambda backend to start tracking pulses
          </p>
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
              Unique identifier for your meditation data (default: jerome)
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

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 flex justify-between space-x-3">
          <button
            onClick={handleCancel}
            className="px-6 py-2 text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!isValid || (!hasChanged && !!currentConfig)}
            className="bg-gradient-to-r from-purple-500 to-blue-500 text-white px-6 py-2 rounded-lg font-semibold hover:from-purple-600 hover:to-blue-600 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {hasChanged || !currentConfig ? 'Save Configuration' : 'No Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};