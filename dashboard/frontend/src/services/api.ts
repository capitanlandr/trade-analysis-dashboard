const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
const USE_STATIC_DATA = true; // Always use static JSON files (same as prod)
console.log('API Configuration:', {
  USE_STATIC_DATA,
  PROD: import.meta.env.PROD,
  API_BASE_URL
});

// Simple fetch wrapper with logging
const apiFetch = async (url: string): Promise<any> => {
  const fullUrl = USE_STATIC_DATA ? url : `${API_BASE_URL}${url}`;
  console.log(`API Request: GET ${fullUrl}`);
  
  try {
    const response = await fetch(fullUrl);
    console.log(`API Response: ${response.status} ${url}`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('API Error:', { url, error });
    throw error;
  }
};

export const api = {
  // Health and status
  health: () => apiFetch('/health'),
  status: () => apiFetch('/status'),

  // Trades
  getTrades: async (params?: {
    startDate?: string;
    endDate?: string;
    teams?: string[];
    minValue?: number;
    maxResults?: number;
  }) => {
    if (USE_STATIC_DATA) {
      return apiFetch('/api-trades.json');
    }
    
    const searchParams = new URLSearchParams();
    if (params?.startDate) searchParams.append('startDate', params.startDate);
    if (params?.endDate) searchParams.append('endDate', params.endDate);
    if (params?.teams?.length) searchParams.append('teams', params.teams.join(','));
    if (params?.minValue) searchParams.append('minValue', params.minValue.toString());
    if (params?.maxResults) searchParams.append('maxResults', params.maxResults.toString());
    
    const queryString = searchParams.toString();
    return apiFetch(`/trades${queryString ? `?${queryString}` : ''}`);
  },

  getTrade: (id: string) => apiFetch(`/trades/${id}`),

  getBlockbusterTrades: (threshold?: number) => {
    const params = threshold ? `?threshold=${threshold}` : '';
    return apiFetch(`/trades/blockbuster${params}`);
  },

  // Teams
  getTeams: async (params?: {
    sortBy?: string;
    order?: 'asc' | 'desc';
  }) => {
    if (USE_STATIC_DATA) {
      return apiFetch('/api-teams.json');
    }
    
    const searchParams = new URLSearchParams();
    if (params?.sortBy) searchParams.append('sortBy', params.sortBy);
    if (params?.order) searchParams.append('order', params.order);
    
    const queryString = searchParams.toString();
    return apiFetch(`/teams${queryString ? `?${queryString}` : ''}`);
  },

  getTeam: (id: string) => apiFetch(`/teams/${id}`),

  // Statistics
  getStatsSummary: () => {
    if (USE_STATIC_DATA) {
      return apiFetch('/api-stats-summary.json');
    }
    return apiFetch('/stats/summary');
  },

  getTrends: (period?: 'week' | 'month') => {
    const params = period ? `?period=${period}` : '';
    return apiFetch(`/stats/trends${params}`);
  },

  // Data management
  loadData: () => apiFetch('/data/load'),
};

export default api;