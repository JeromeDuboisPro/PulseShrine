import { getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
import getAmplifyConfig from './amplify-config';

// Types based on your existing API structure
export interface StartPulse {
  pulse_id: string;
  user_id: string;
  intent: string;
  timestamp?: number;
  inverted_timestamp?: number;
  start_time?: string;
  duration_seconds: number;
  intent_emotion?: string;
  gen_title?: string;
  gen_badge?: string;
  remaining_seconds?: number;
  server_time?: string;
  subscription?: SubscriptionInfo; // Added subscription info to pulse responses
}

export interface StopPulse {
  pulse_id: string;
  user_id: string;
  intent: string;
  reflection: string;
  reflection_emotion?: string;
  timestamp: number;
  inverted_timestamp: number;
  duration_seconds?: number;
  intent_emotion?: string;
  gen_title?: string;
  gen_badge?: string;
  // AI Enhancement Data (may be present during processing)
  ai_enhanced?: boolean;
  ai_cost_cents?: number;
  triggered_rewards?: Array<{
    type: string;
    ai_credits: number;
    message: string;
    achievement?: string;
  }>;
  selection_info?: {
    decision_reason: string;
    worthiness_score: number;
    estimated_cost_cents: number;
    could_be_enhanced?: boolean;
  };
  ai_selection_info?: {
    decision_reason: string;
    worthiness_score: number;
    estimated_cost_cents: number;
    could_be_enhanced: boolean;
    budget_status: {
      daily_used: number;
      monthly_used: number;
      user_tier: string;
    };
    timestamp: string;
  };
}

export interface IngestedPulse {
  pulse_id: string;
  user_id: string;
  intent: string;
  reflection: string;
  reflection_emotion?: string;
  timestamp: number;
  inverted_timestamp: number;
  duration_seconds?: number;
  intent_emotion?: string;
  gen_title: string;
  gen_badge: string;
  gen_rune_name?: string;
  // AI Enhancement Data
  ai_enhanced?: boolean;
  ai_cost_cents?: number;
  ai_insights?: {
    productivity_score: number;
    key_insight: string;
    next_suggestion: string;
    mood_assessment: string;
    emotion_pattern?: string;
  };
  triggered_rewards?: Array<{
    type: string;
    ai_credits: number;
    message: string;
    achievement?: string;
  }>;
  // Selection metadata (for plan limitation awareness)
  selection_info?: {
    decision_reason: string;
    worthiness_score: number;
    estimated_cost_cents: number;
    could_be_enhanced?: boolean;
  };
  ai_selection_info?: {
    decision_reason: string;
    worthiness_score: number;
    estimated_cost_cents: number;
    could_be_enhanced: boolean;
    budget_status: {
      daily_used: number;
      monthly_used: number;
      user_tier: string;
    };
    timestamp: string;
  };
}

// Subscription and Usage Types
export interface SubscriptionInfo {
  subscription_tier: 'free' | 'pro' | 'enterprise';
  subscription_status: 'active' | 'canceled' | 'past_due' | 'trial' | 'incomplete';
  billing_cycle: {
    start: string;
    end: string;
    days_remaining: number;
  };
  usage: {
    pulses: {
      used: number;
      quota: number;
      percentage: number;
      unlimited: boolean;
    };
    ai_enhancements: {
      used: number;
      quota: number;
      percentage: number;
      unlimited: boolean;
    };
    ai_cost_cents: number;
  };
  features: {
    advanced_analytics: boolean;
    export_enabled: boolean;
    priority_processing: boolean;
    custom_prompts: boolean;
    team_workspaces: number;
  };
}

export interface PricingTier {
  name: string;
  price: number;
  currency: string;
  interval: string;
  features: {
    monthly_pulses: number;
    ai_enhancements: number;
    advanced_analytics: boolean;
    export_enabled: boolean;
    priority_processing: boolean;
    custom_prompts: boolean;
    team_workspaces: number;
  };
  description: string;
  popular?: boolean;
}

export interface PricingInfo {
  tiers: {
    free: PricingTier;
    pro: PricingTier;
    enterprise: PricingTier;
  };
  currency_symbol: string;
  trial_days: number;
}

// API Error handling
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Get JWT token from Cognito
async function getAuthToken(): Promise<string> {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    
    if (!token) {
      throw new ApiError('No authentication token available. Please sign in.', 401, 'NO_AUTH_TOKEN');
    }
    
    return token;
  } catch (error) {
    console.error('Failed to get auth token:', error);
    throw new ApiError('Authentication failed. Please sign in again.', 401, 'AUTH_FAILED');
  }
}

// Get current user ID from Cognito
export async function getCurrentUserId(): Promise<string> {
  try {
    const user = await getCurrentUser();
    return user.userId;
  } catch (error) {
    console.error('Failed to get current user:', error);
    throw new ApiError('Unable to get user information. Please sign in again.', 401, 'USER_INFO_FAILED');
  }
}

// Base API call function with JWT authentication
async function callPulseAPI<T>(
  method: string,
  endpoint: string,
  body?: Record<string, any>
): Promise<T> {
  const config = getAmplifyConfig();
  
  if (!config.apiGatewayUrl) {
    throw new ApiError('API configuration is missing. Please check your environment variables.');
  }

  // Get JWT token for authentication
  const authToken = await getAuthToken();

  const url = new URL(config.apiGatewayUrl + endpoint);
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    }
  };

  if (method === 'GET' && body && Object.keys(body).length) {
    Object.entries(body).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        url.searchParams.append(k, String(v));
      }
    });
  } else if (method !== 'GET' && body) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      let errorCode = '';
      
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorData.error || errorMessage;
        errorCode = errorData.code || '';
      } catch {
        // If response is not JSON, use the default error message
      }
      
      if (response.status === 401) {
        throw new ApiError('Authentication failed. Please sign in again.', 401, 'UNAUTHORIZED');
      }
      
      if (response.status === 429) {
        throw new ApiError('Too many requests. Please wait a moment before trying again.', 429, 'RATE_LIMIT');
      }
      
      throw new ApiError(errorMessage, response.status, errorCode);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    
    // Network or other fetch errors
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new ApiError('Network error. Please check your internet connection and API configuration.', 0, 'NETWORK_ERROR');
    }
    
    throw new ApiError(`Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`, 0, 'UNKNOWN_ERROR');
  }
}

// API methods
export const PulseAPI = {
  // Get active pulse for current user
  getStartPulse: async (): Promise<StartPulse | null> => {
    try {
      const result = await callPulseAPI<StartPulse>('GET', '/get-start-pulse');
      return result;
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null; // No active pulse
      }
      throw error;
    }
  },

  // Get completed pulses for current user
  getStopPulses: async (): Promise<StopPulse[]> => {
    try {
      const result = await callPulseAPI<StopPulse[]>('GET', '/get-stop-pulses');
      return Array.isArray(result) ? result : [];
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return []; // No stopped pulses
      }
      throw error;
    }
  },

  // Get processed/ingested pulses for current user
  getIngestedPulses: async (nbItems?: number): Promise<IngestedPulse[]> => {
    try {
      const params: any = {};
      if (nbItems !== undefined) {
        params.nb_items = nbItems;
      }
      const result = await callPulseAPI<IngestedPulse[]>('GET', '/get-ingested-pulses', params);
      return Array.isArray(result) ? result : [];
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return []; // No ingested pulses
      }
      throw error;
    }
  },

  // Start a new pulse for current user
  startPulse: async (intent: string, durationSeconds: number, intentEmotion?: string): Promise<StartPulse> => {
    if (!intent.trim()) {
      throw new ApiError('Intention cannot be empty', 400, 'INVALID_INPUT');
    }
    
    const payload: any = {
      intent: intent.trim(),
      duration_seconds: durationSeconds
    };
    
    if (intentEmotion) {
      payload.intent_emotion = intentEmotion;
    }
    
    return await callPulseAPI<StartPulse>('POST', '/start-pulse', payload);
  },

  // Stop active pulse for current user
  stopPulse: async (reflection: string, reflectionEmotion?: string): Promise<StopPulse> => {
    const payload: any = {
      reflection: reflection.trim()
    };
    
    if (reflectionEmotion) {
      payload.reflection_emotion = reflectionEmotion;
    }
    
    return await callPulseAPI<StopPulse>('POST', '/stop-pulse', payload);
  },

  // Subscription Management
  getSubscription: async (): Promise<SubscriptionInfo> => {
    return await callPulseAPI<SubscriptionInfo>('GET', '/subscription');
  },

  getPricing: async (): Promise<PricingInfo> => {
    return await callPulseAPI<PricingInfo>('GET', '/subscription/pricing');
  },

  upgradeSubscription: async (tier: 'pro' | 'enterprise', stripeSubscriptionId?: string): Promise<{success: boolean; message: string; subscription: SubscriptionInfo}> => {
    const payload: any = { tier };
    if (stripeSubscriptionId) {
      payload.stripe_subscription_id = stripeSubscriptionId;
    }
    return await callPulseAPI('POST', '/subscription/upgrade', payload);
  },

  createCustomer: async (email: string): Promise<{success: boolean; customer_id: string; message: string}> => {
    return await callPulseAPI('POST', '/subscription/create-customer', { email });
  }
};