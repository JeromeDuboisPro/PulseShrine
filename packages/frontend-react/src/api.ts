import { config } from './config';

// Types based on your existing API structure
export interface StartPulse {
  pulse_id: string;
  user_id: string;
  intent: string;
  timestamp?: number;
  inverted_timestamp?: number;
  start_time?: string;
  duration_seconds?: number;
  intent_emotion?: string;
  gen_title?: string;
  gen_badge?: string;
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

// Base API call function
async function callPulseAPI<T>(
  method: string,
  endpoint: string,
  body?: Record<string, any>
): Promise<T> {
  if (!config.apiKey || !config.apiBaseUrl) {
    throw new ApiError('API configuration is missing. Please check your environment variables or configuration.');
  }

  const url = new URL(config.apiBaseUrl + endpoint);
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': config.apiKey
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
  // Get active pulse for user
  getStartPulse: async (userId: string): Promise<StartPulse | null> => {
    try {
      const result = await callPulseAPI<StartPulse>('GET', '/get-start-pulse', { user_id: userId });
      return result;
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null; // No active pulse
      }
      throw error;
    }
  },

  // Get completed pulses for user
  getStopPulses: async (userId: string): Promise<StopPulse[]> => {
    try {
      const result = await callPulseAPI<StopPulse[]>('GET', '/get-stop-pulses', { user_id: userId });
      return Array.isArray(result) ? result : [];
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return []; // No stopped pulses
      }
      throw error;
    }
  },

  // Get processed/ingested pulses for user
  getIngestedPulses: async (userId: string): Promise<IngestedPulse[]> => {
    try {
      const result = await callPulseAPI<IngestedPulse[]>('GET', '/get-ingested-pulses', { user_id: userId });
      return Array.isArray(result) ? result : [];
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return []; // No ingested pulses
      }
      throw error;
    }
  },

  // Start a new pulse
  startPulse: async (userId: string, intent: string, durationSeconds?: number, intentEmotion?: string): Promise<StartPulse> => {
    if (!intent.trim()) {
      throw new ApiError('Intention cannot be empty', 400, 'INVALID_INPUT');
    }
    
    const payload: any = {
      user_id: userId,
      intent: intent.trim()
    };
    
    if (durationSeconds !== undefined) {
      payload.duration_seconds = durationSeconds;
    }
    
    if (intentEmotion) {
      payload.intent_emotion = intentEmotion;
    }
    
    return await callPulseAPI<StartPulse>('POST', '/start-pulse', payload);
  },

  // Stop active pulse
  stopPulse: async (userId: string, reflection: string, reflectionEmotion?: string): Promise<StopPulse> => {
    const payload: any = {
      user_id: userId,
      reflection: reflection.trim()
    };
    
    if (reflectionEmotion) {
      payload.reflection_emotion = reflectionEmotion;
    }
    
    return await callPulseAPI<StopPulse>('POST', '/stop-pulse', payload);
  }
};