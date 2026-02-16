/**
 * Lambda API Client -- Mock Mode (Task 2.5)
 *
 * Provides 7 fetch functions matching the 7 API Gateway endpoints.
 * Controlled by two environment variables:
 *
 *   VITE_USE_LAMBDA_API  -- "true" to call Lambda, anything else for static JSON (default: false)
 *   VITE_API_BASE_URL    -- API Gateway base URL (default: production API Gateway URL)
 *
 * In static mode (default), functions fetch from /public/*.json files -- identical
 * to the dashboard's original behavior.
 *
 * In Lambda mode, functions call API Gateway endpoints and return the same data shapes.
 *
 * Wrapper normalization:
 *   - 3 static files use {success: true, data: {...}} wrappers (trades, teams, stats)
 *   - 4 static files are raw JSON (standings, playoffs, draft order, waivers)
 *   - This client normalizes so consumers always receive the inner data type.
 *   - When Lambda API is active, responses are expected to be raw JSON (no wrapper),
 *     matching the DynamoDB enriched data format.
 */

import type { TradeData, Team, LeagueStats } from '../types';
import type { StandingsData } from '../types/standings';
import type { PlayoffScenariosData } from '../types/playoff-scenarios';
import type { ProgressiveDraftOrder } from '../types/draft-order';
import type { WaiverWireData } from '../types/waiver-wire';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const USE_LAMBDA_API =
  import.meta.env.VITE_USE_LAMBDA_API === 'true';

const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ||
  'https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod';

if (import.meta.env.DEV) {
  console.log('[api-client] Configuration:', {
    USE_LAMBDA_API,
    API_BASE_URL: USE_LAMBDA_API ? API_BASE_URL : '(static JSON -- not used)',
  });
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Shared fetch helper with error handling and logging.
 */
async function fetchJson<T>(url: string, label: string): Promise<T> {
  if (import.meta.env.DEV) {
    console.log(`[api-client] ${label}: GET ${url}`);
  }

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(
      `[api-client] ${label} failed: HTTP ${response.status} ${response.statusText}`
    );
  }

  const json = await response.json();
  return json as T;
}

/**
 * Build the Lambda endpoint URL for a given path.
 */
function lambdaUrl(baseUrl: string, path: string): string {
  // Strip trailing slash from base, ensure path starts with /
  const base = baseUrl.replace(/\/+$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

// ---------------------------------------------------------------------------
// Wrapper-aware static JSON types
// ---------------------------------------------------------------------------

/** Shape of the {success, data} wrapper used by trades, teams, and stats JSON files. */
interface WrappedResponse<T> {
  success: boolean;
  data: T;
}

/** api-trades.json wraps TradeData inside {success, data}. */
interface WrappedTradeData {
  success: boolean;
  data: TradeData;
}

/**
 * api-teams.json wraps {teams: Team[]} inside {success, data}.
 * The inner shape has a `teams` array.
 */
interface TeamsPayload {
  teams: Team[];
}

/**
 * api-stats-summary.json wraps the stats object inside {success, data}.
 * The inner shape has an `overview` object matching LeagueStats plus extra fields.
 */
interface StatsPayload {
  overview: LeagueStats;
  teamRankings?: unknown;
  recentActivity?: unknown;
}

// ---------------------------------------------------------------------------
// Public fetch functions
// ---------------------------------------------------------------------------

/**
 * Fetch trade data.
 *
 * Static mode: reads /api-trades.json, unwraps {success, data} envelope.
 * Lambda mode: calls GET /api/trades, expects raw TradeData.
 */
export async function fetchTrades(baseUrl?: string): Promise<TradeData> {
  if (USE_LAMBDA_API) {
    const url = lambdaUrl(baseUrl || API_BASE_URL, '/api/trades');
    // Lambda returns {success, data} wrapper (same as static JSON)
    const wrapped = await fetchJson<WrappedTradeData>(url, 'fetchTrades');
    return wrapped.data;
  }

  // Static JSON -- has {success, data} wrapper
  const wrapped = await fetchJson<WrappedTradeData>(
    '/api-trades.json',
    'fetchTrades (static)'
  );
  return wrapped.data;
}

/**
 * Fetch team data.
 *
 * Static mode: reads /api-teams.json, unwraps {success, data.teams}.
 * Lambda mode: calls GET /api/teams, expects raw Team[].
 */
export async function fetchTeams(baseUrl?: string): Promise<Team[]> {
  if (USE_LAMBDA_API) {
    const url = lambdaUrl(baseUrl || API_BASE_URL, '/api/teams');
    // Lambda returns {success, data: {teams: [...]}} wrapper (same as static JSON)
    const wrapped = await fetchJson<WrappedResponse<TeamsPayload>>(url, 'fetchTeams');
    return wrapped.data.teams;
  }

  // Static JSON -- has {success, data: {teams: [...]}} wrapper
  const wrapped = await fetchJson<WrappedResponse<TeamsPayload>>(
    '/api-teams.json',
    'fetchTeams (static)'
  );
  return wrapped.data.teams;
}

/**
 * Fetch league statistics summary.
 *
 * Static mode: reads /api-stats-summary.json, unwraps {success, data.overview}.
 * Lambda mode: calls GET /api/stats, expects raw LeagueStats.
 */
export async function fetchStats(baseUrl?: string): Promise<LeagueStats> {
  if (USE_LAMBDA_API) {
    const url = lambdaUrl(baseUrl || API_BASE_URL, '/api/stats');
    // Lambda returns {success, data: {overview, teamRankings, recentActivity, ...}}
    const wrapped = await fetchJson<WrappedResponse<StatsPayload>>(url, 'fetchStats');
    return wrapped.data as unknown as LeagueStats;
  }

  // Static JSON -- has {success, data: {overview, teamRankings, ...}} wrapper
  const wrapped = await fetchJson<WrappedResponse<StatsPayload>>(
    '/api-stats-summary.json',
    'fetchStats (static)'
  );
  return wrapped.data as unknown as LeagueStats;
}

/**
 * Fetch standings data.
 *
 * Static mode: reads /api-standings.json (raw, no wrapper).
 * Lambda mode: calls GET /api/standings.
 */
export async function fetchStandings(baseUrl?: string): Promise<StandingsData> {
  if (USE_LAMBDA_API) {
    const url = lambdaUrl(baseUrl || API_BASE_URL, '/api/standings');
    return fetchJson<StandingsData>(url, 'fetchStandings');
  }

  return fetchJson<StandingsData>(
    '/api-standings.json',
    'fetchStandings (static)'
  );
}

/**
 * Fetch playoff scenarios data.
 *
 * Static mode: reads /api-playoff-scenarios.json (raw, no wrapper).
 * Lambda mode: calls GET /api/playoffs.
 */
export async function fetchPlayoffs(
  baseUrl?: string
): Promise<PlayoffScenariosData> {
  if (USE_LAMBDA_API) {
    const url = lambdaUrl(baseUrl || API_BASE_URL, '/api/playoffs');
    return fetchJson<PlayoffScenariosData>(url, 'fetchPlayoffs');
  }

  return fetchJson<PlayoffScenariosData>(
    '/api-playoff-scenarios.json',
    'fetchPlayoffs (static)'
  );
}

/**
 * Fetch draft order projection data.
 *
 * Static mode: reads /api-draft-order.json (raw, no wrapper).
 * Lambda mode: calls GET /api/draft-order.
 */
export async function fetchDraftOrder(
  baseUrl?: string
): Promise<ProgressiveDraftOrder> {
  if (USE_LAMBDA_API) {
    const url = lambdaUrl(baseUrl || API_BASE_URL, '/api/draft-order');
    return fetchJson<ProgressiveDraftOrder>(url, 'fetchDraftOrder');
  }

  return fetchJson<ProgressiveDraftOrder>(
    '/api-draft-order.json',
    'fetchDraftOrder (static)'
  );
}

/**
 * Fetch waiver wire data.
 *
 * Static mode: reads /waiver-wire-page.json (raw, no wrapper).
 * Lambda mode: calls GET /api/waivers.
 */
export async function fetchWaivers(
  baseUrl?: string
): Promise<WaiverWireData> {
  if (USE_LAMBDA_API) {
    const url = lambdaUrl(baseUrl || API_BASE_URL, '/api/waivers');
    return fetchJson<WaiverWireData>(url, 'fetchWaivers');
  }

  return fetchJson<WaiverWireData>(
    '/waiver-wire-page.json',
    'fetchWaivers (static)'
  );
}
