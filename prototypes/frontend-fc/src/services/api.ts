import { useQuery, UseQueryResult } from '@tanstack/react-query';
import type { WaiverWireData } from '../types/waiver-wire';
import type { StandingsData } from '../types/standings';
import type { PlayoffScenariosData } from '../types/playoff-scenarios';
import type { ProgressiveDraftOrder } from '../types/draft-order';
import type { TradeData, Team, LeagueStats } from '../types';
import type { TradeMetricsData } from '../types/trade-metrics';
import {
  fetchTrades,
  fetchTeams,
  fetchStats,
  fetchStandings,
  fetchPlayoffs,
  fetchDraftOrder,
  fetchWaivers,
  fetchTradeMetrics,
} from './api-client';

// ---------------------------------------------------------------------------
// Legacy API object
//
// These methods wrap the new api-client functions so that existing component
// imports (`import api from './api'` or `import { api } from './api'`)
// continue to work without changes.
//
// The underlying api-client respects the VITE_USE_LAMBDA_API toggle:
//   false (default) -> static JSON from /public/*.json
//   true            -> API Gateway Lambda endpoints
// ---------------------------------------------------------------------------

export const api = {
  // Trades
  getTrades: async (_params?: {
    startDate?: string;
    endDate?: string;
    teams?: string[];
    minValue?: number;
    maxResults?: number;
  }) => {
    const data = await fetchTrades();
    // Return in the legacy {success, data} wrapper for backward compatibility
    // with any code that accesses response.data or response.success
    return { success: true, data };
  },

  getTeams: async (_params?: {
    sortBy?: string;
    order?: 'asc' | 'desc';
  }) => {
    const teams = await fetchTeams();
    return { success: true, data: { teams } };
  },

  getStatsSummary: async () => {
    const stats = await fetchStats();
    return { success: true, data: stats };
  },

  getWaiverWireData: async () => {
    return fetchWaivers();
  },

  getTradeMetrics: async (): Promise<TradeMetricsData> => {
    return fetchTradeMetrics();
  },
};

// ---------------------------------------------------------------------------
// React Query hooks
//
// These provide centralized caching with consistent staleTime / gcTime.
// All hooks now go through api-client.ts, which handles the static/Lambda
// toggle. No more hardcoded fetch() calls to static JSON paths.
// ---------------------------------------------------------------------------

const QUERY_STALE_TIME = 5 * 60 * 1000; // 5 minutes
const QUERY_GC_TIME = 30 * 60 * 1000; // 30 minutes

export const useTradesData = (): UseQueryResult<TradeData> => {
  return useQuery({
    queryKey: ['trades'],
    queryFn: () => fetchTrades(),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
  });
};

export const useTeamsData = (): UseQueryResult<Team[]> => {
  return useQuery({
    queryKey: ['teams'],
    queryFn: () => fetchTeams(),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
  });
};

export const useStatsData = (): UseQueryResult<LeagueStats> => {
  return useQuery({
    queryKey: ['stats'],
    queryFn: () => fetchStats(),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
  });
};

export const useWaiverWireData = (): UseQueryResult<WaiverWireData> => {
  return useQuery({
    queryKey: ['waiver-wire'],
    queryFn: () => fetchWaivers(),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
  });
};

export const useStandingsData = (): UseQueryResult<StandingsData> => {
  return useQuery({
    queryKey: ['standings'],
    queryFn: () => fetchStandings(),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
  });
};

export const usePlayoffScenariosData = (): UseQueryResult<PlayoffScenariosData> => {
  return useQuery({
    queryKey: ['playoff-scenarios'],
    queryFn: () => fetchPlayoffs(),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
  });
};

export const useTradeMetricsData = (): UseQueryResult<TradeMetricsData> => {
  return useQuery({
    queryKey: ['trade-metrics'],
    queryFn: () => fetchTradeMetrics(),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
  });
};

export const useDraftOrderData = (): UseQueryResult<ProgressiveDraftOrder> => {
  return useQuery({
    queryKey: ['draft-order'],
    queryFn: () => fetchDraftOrder(),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
  });
};

export default api;
