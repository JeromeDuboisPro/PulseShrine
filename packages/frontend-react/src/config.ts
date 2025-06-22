// API Configuration
export interface ApiConfig {
  apiKey: string;
  apiBaseUrl: string;
  userId: string;
}

// Default configuration - these will be overridden by environment variables or config file
export const defaultConfig: ApiConfig = {
  apiKey: (import.meta.env?.VITE_API_KEY as string) || '',
  apiBaseUrl: (import.meta.env?.VITE_API_BASE_URL as string) || '',
  userId: (import.meta.env?.VITE_USER_ID as string) || 'jerome'
};

// Load configuration from localStorage if available (for manual configuration)
let config: ApiConfig = { ...defaultConfig };

try {
  const storedConfig = localStorage.getItem('pulseshrine-config');
  if (storedConfig) {
    const parsed = JSON.parse(storedConfig);
    config = { ...config, ...parsed };
  }
} catch (error) {
  console.warn('Failed to load configuration from localStorage:', error);
}

export { config };

// Helper to update configuration
export const updateConfig = (newConfig: Partial<ApiConfig>) => {
  config = { ...config, ...newConfig };
  try {
    localStorage.setItem('pulseshrine-config', JSON.stringify(config));
  } catch (error) {
    console.warn('Failed to save configuration to localStorage:', error);
  }
};