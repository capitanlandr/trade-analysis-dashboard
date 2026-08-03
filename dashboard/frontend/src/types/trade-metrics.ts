/**
 * Trade Metrics Types
 *
 * Shape of api-trade-metrics.json, produced by
 * pipeline/scripts/generate_trade_metrics.py and served by GET /api/metrics.
 *
 * These metrics were added in June 2026, five months after the Lambda API was
 * built with its original seven routes, which is why they were fetched with a
 * raw fetch() that bypassed api-client.ts and so ignored VITE_USE_LAMBDA_API.
 * The types live here so both consumers share one definition instead of
 * re-deriving the shape with `any`.
 */

/** Per-opponent breakdown inside a manager's opponent-adjusted metrics. */
export interface OpponentBreakdown {
  opponent: string;
  opponent_name: string;
  net_advantage: number;
  trade_count: number;
  avg_per_trade: number;
}

/** Risk-adjusted return on a manager's trades. */
export interface SharpeMetrics {
  value: number;
  mean: number;
  std_dev: number;
  verdict: string;
}

/** Statistical significance of a manager's net advantage. */
export interface SignificanceMetrics {
  [key: string]: unknown;
}

export interface OpponentAdjustedMetrics {
  unique_opponents: number;
  positive_matchups: number;
  top_opponent_concentration_pct: number;
  opponents: OpponentBreakdown[];
}

export interface TradeMetricsManager {
  username: string;
  real_name: string;
  trades: number;
  net_advantage: number;
  sharpe: SharpeMetrics;
  significance: SignificanceMetrics;
  opponent_adjusted: OpponentAdjustedMetrics;
}

export interface TradeMetricsMetadata {
  generated: string;
  total_trades: number;
  description: string;
}

export interface TradeMetricsData {
  metadata: TradeMetricsMetadata;
  managers: TradeMetricsManager[];
}
