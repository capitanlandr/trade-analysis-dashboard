import axios from 'axios';
import { ApiResponse, Trade, Team, LeagueStats, TradeData } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? '/api' : 'http://localhost:3001/api');
const USE_STATIC_DATA = import.meta.env.PROD;
console.log('API Configuration:', {
  USE_STATIC_DATA,
  PROD: import.meta.env.PROD,
  API_BASE_URL
});

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and retry logic
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    console.error('API Response Error:', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      data: error.response?.data
    });

    // Retry logic for network errors and 5xx errors
    if (
      !originalRequest._retry &&
      (!error.response || error.response.status >= 500) &&
      originalRequest.method?.toLowerCase() === 'get'
    ) {
      originalRequest._retry = true;
      originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;

      if (originalRequest._retryCount <= 2) {
        const delay = Math.pow(2, originalRequest._retryCount) * 1000; // Exponential backoff
        console.log(`Retrying API request in ${delay}ms... (attempt ${originalRequest._retryCount}/2)`);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        return apiClient(originalRequest);
      }
    }

    // Enhanced error object with user-friendly messages
    const enhancedError = {
      ...error,
      userMessage: getUserFriendlyErrorMessage(error),
      isRetryable: isRetryableError(error),
      timestamp: new Date().toISOString()
    };

    return Promise.reject(enhancedError);
  }
);

// Helper function to generate user-friendly error messages
function getUserFriendlyErrorMessage(error: any): string {
  if (!error.response) {
    return 'Unable to connect to the server. Please check your internet connection.';
  }

  const status = error.response.status;
  
  switch (status) {
    case 400:
      return 'Invalid request. Please try again.';
    case 401:
      return 'Authentication required. Please refresh the page.';
    case 403:
      return 'Access denied. You don\'t have permission to access this resource.';
    case 404:
      return 'The requested data was not found.';
    case 408:
      return 'Request timeout. Please try again.';
    case 429:
      return 'Too many requests. Please wait a moment and try again.';
    case 500:
      return 'Server error. Our team has been notified.';
    case 502:
    case 503:
    case 504:
      return 'Service temporarily unavailable. Please try again in a few moments.';
    default:
      return 'An unexpected error occurred. Please try again.';
  }
}

// Helper function to determine if an error is retryable
function isRetryableError(error: any): boolean {
  if (!error.response) return true; // Network errors are retryable
  
  const status = error.response.status;
  return status >= 500 || status === 408 || status === 429;
}

// Static data fallback for production
const fetchStaticData = async (endpoint: string) => {
  console.log('fetchStaticData called with:', endpoint);
  try {
    const response = await fetch(endpoint);
    console.log('Fetch response:', { status: response.status, ok: response.ok, url: response.url });
    if (!response.ok) {
      throw new Error(`Failed to fetch ${endpoint}: ${response.status} ${response.statusText}`);
    }
    const jsonData = await response.json();
    console.log('Parsed JSON data:', jsonData);
    // JSON files already have { success: true, data: {...} } structure
    return jsonData;
  } catch (error) {
    console.error('Static data fetch error:', error);
    // Return empty data structure to prevent crashes
    if (endpoint.includes('trades')) {
      return { success: true, data: { trades: [] } };
    } else if (endpoint.includes('teams')) {
      return { success: true, data: { teams: [] } };
    } else {
      return { success: true, data: { overview: {}, teamRankings: { byValueGained: [] } } };
    }
  }
};

export const api = {
  // Health and status
  health: () => USE_STATIC_DATA ? Promise.resolve({ data: { success: true } }) : apiClient.get<ApiResponse>('/health'),
  status: () => USE_STATIC_DATA ? Promise.resolve({ data: { success: true } }) : apiClient.get<ApiResponse>('/status'),

  // Trades
  getTrades: (params?: {
    startDate?: string;
    endDate?: string;
    teams?: string[];
    minValue?: number;
    maxResults?: number;
  }) => {
    if (USE_STATIC_DATA) {
      return fetchStaticData('/api-trades.json');
    }
    
    const searchParams = new URLSearchParams();
    if (params?.startDate) searchParams.append('startDate', params.startDate);
    if (params?.endDate) searchParams.append('endDate', params.endDate);
    if (params?.teams?.length) searchParams.append('teams', params.teams.join(','));
    if (params?.minValue) searchParams.append('minValue', params.minValue.toString());
    if (params?.maxResults) searchParams.append('maxResults', params.maxResults.toString());
    
    const queryString = searchParams.toString();
    return apiClient.get<ApiResponse<TradeData>>(`/trades${queryString ? `?${queryString}` : ''}`);
  },

  getTrade: (id: string) => apiClient.get<ApiResponse<{ trade: Trade; relatedTrades: Trade[]; context: any }>>(`/trades/${id}`),

  getBlockbusterTrades: (threshold?: number) => {
    const params = threshold ? `?threshold=${threshold}` : '';
    return apiClient.get<ApiResponse<{ blockbusterTrades: Trade[]; threshold: number; count: number; averageValue: number }>>(`/trades/blockbuster${params}`);
  },

  // Teams
  getTeams: (params?: {
    sortBy?: string;
    order?: 'asc' | 'desc';
  }) => {
    if (USE_STATIC_DATA) {
      return fetchStaticData('/api-teams.json');
    }
    
    const searchParams = new URLSearchParams();
    if (params?.sortBy) searchParams.append('sortBy', params.sortBy);
    if (params?.order) searchParams.append('order', params.order);
    
    const queryString = searchParams.toString();
    return apiClient.get<ApiResponse<{ teams: Team[]; summary: any }>>(`/teams${queryString ? `?${queryString}` : ''}`);
  },

  getTeam: (id: string) => apiClient.get<ApiResponse<{ team: Team; trades: Trade[]; statistics: any }>>(`/teams/${id}`),

  // Statistics
  getStatsSummary: () => {
    if (USE_STATIC_DATA) {
      return fetchStaticData('/api-stats-summary.json');
    }
    return apiClient.get<ApiResponse<{
      overview: LeagueStats;
      tradesByMonth: Record<string, number>;
      valueDistribution: Record<string, number>;
      swingAnalysis: any;
      teamRankings: any;
      recentActivity: any;
    }>>('/stats/summary');
  },

  getTrends: (period?: 'week' | 'month') => {
    const params = period ? `?period=${period}` : '';
    return apiClient.get<ApiResponse<{ trends: any[]; period: string; summary: any }>>(`/stats/trends${params}`);
  },

  // Data management
  loadData: () => apiClient.get<ApiResponse<TradeData>>('/data/load'),
};

export default api;