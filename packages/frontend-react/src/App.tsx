import { useState } from 'react';
import { ApiConfig, defaultConfig } from './config';
import { SetupScreen } from './components/SetupScreen';
import { PulseApp } from './components/PulseApp';

const App = () => {
  // Check if we have a valid configuration on startup
  const getStoredConfig = (): ApiConfig | null => {
    try {
      const stored = localStorage.getItem('pulseshrine-config');
      if (stored) {
        const config = { ...defaultConfig, ...JSON.parse(stored) };
        // Validate that we have the required fields
        if (config.apiKey && config.apiBaseUrl && config.userId) {
          return config;
        }
      }
    } catch (error) {
      console.warn('Failed to load config from localStorage:', error);
    }
    return null;
  };

  const [config, setConfig] = useState<ApiConfig | null>(getStoredConfig);

  const handleConfigured = (newConfig: ApiConfig) => {
    console.log('App configured with:', { 
      apiBaseUrl: newConfig.apiBaseUrl, 
      userId: newConfig.userId,
      hasApiKey: !!newConfig.apiKey 
    });
    setConfig(newConfig);
  };

  const handleReconfigure = () => {
    console.log('Reconfiguring app...');
    // Clear stored config
    try {
      localStorage.removeItem('pulseshrine-config');
    } catch (error) {
      console.warn('Failed to clear config from localStorage:', error);
    }
    setConfig(null);
  };

  // Show setup screen if no valid configuration
  if (!config) {
    return <SetupScreen onConfigured={handleConfigured} />;
  }

  // Show the actual app with the configuration
  return <PulseApp config={config} onReconfigure={handleReconfigure} />;
};

export default App;