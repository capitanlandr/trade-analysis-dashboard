export interface WaiverWireTransaction {
  transaction_id: string;
  type: 'waiver' | 'free_agent';
  action: 'add' | 'drop' | 'unknown';
  status: 'complete' | 'failed';
  team_name: string;
  roster_id: number;
  player_name: string;
  player_id: string;
  player_value?: number | null;
  waiver_bid: number;
  week: number;
  created_date: string;
  status_updated_date: string;
  notes: string;
  sequence: number | null;
  priority: number | null;
  season: string;
  year: number;
}

export interface ChurnMetric {
  roster_id: number;
  team_name: string;
  total_adds: number;
  total_drops: number;
  overall_churn_rate: number;
  management_style: 'extreme' | 'active' | 'moderate' | 'passive';
  position_churn?: {
    position: string;
    churn_rate: number;
    total_moves: number;
  }[];
}

export interface EfficiencyMetric {
  roster_id: number;
  team_name: string;
  total_points_from_adds: number;
  faab_spent: number;
  free_agent_count: number;
  raw_wwes: number;
  normalized_wwes: number;
  league_percentile: number;
}

export interface EfficiencyData {
  manager_metrics: EfficiencyMetric[];
  league_stats: {
    mean_wwes: number;
    std_dev_wwes: number;
    median_wwes: number;
  };
}

export interface NotableHit {
  player_name: string;
  player_id: string;
  acquisition_week: number;
  weeks_started: number;
  total_weeks_available: number;
  tier: number | null;
}

export interface HitRateMetric {
  roster_id: number;
  team_name: string;
  total_adds: number;
  tier1_hits: number;
  tier2_hits: number;
  tier3_hits: number;
  misses: number;
  overall_hit_rate: number;
  notable_hits: NotableHit[];
}

export interface HitRateData {
  manager_metrics: HitRateMetric[];
  league_stats: {
    avg_hit_rate: number;
    median_hit_rate: number;
  };
}

export interface NotableTimingHit {
  player_name: string;
  points: number;
  tier: number;
}

export interface TimingMetric {
  roster_id: number;
  team_name: string;
  early_week_hits: number;
  late_week_hits: number;
  early_avg_points: number;
  late_avg_points: number;
  timing_score: number;
  strategy_type: 'proactive' | 'balanced' | 'reactive';
  notable_early_hits: NotableTimingHit[];
  notable_late_hits: NotableTimingHit[];
}

export interface TimingData {
  manager_metrics: TimingMetric[];
  league_stats: {
    avg_timing_score: number;
    median_timing_score: number;
  };
}

export interface ContestedPlayer {
  player_id: string;
  player_name: string;
  total_claims: number;
  successful_claims: number;
  highest_bid: number;
}

export interface BiddingPatterns {
  distribution: Record<string, number>;
  highest_bids: {
    player_id: string;
    player_name: string;
    waiver_bid: number;
    team_name: string;
    status: string;
  }[];
  zero_bid_success_rate?: number;
}

export interface WeeklyActivity {
  week: number;
  waiver_transactions: number;
  free_agent_transactions: number;
  total_transactions: number;
}

export interface ManagerActivity {
  roster_id: number;
  team_name: string;
  total_claims: number;
  successful_claims: number;
  success_rate: number;
  total_bid: number;
  avg_bid: number;
  max_bid: number;
}

export interface WaiverMetadata {
  generated_at?: string;
  total_waiver_transactions?: number;
  total_free_agent_transactions?: number;
  successful_waivers?: number;
  failed_waivers?: number;
  success_rate?: number;
  total_waiver_bids?: number;
  average_waiver_bid?: number;
  seasonsIncluded?: string[];
}

export interface WaiverWireData {
  all_transactions: WaiverWireTransaction[];
  metadata?: WaiverMetadata;
  churn_metrics?: ChurnMetric[];
  efficiency_metrics?: EfficiencyData | null;
  hit_rate_metrics?: HitRateData | null;
  timing_metrics?: TimingData | null;
  manager_activity?: ManagerActivity[];
  contested_players?: ContestedPlayer[];
  bidding_patterns?: BiddingPatterns;
  weekly_activity?: WeeklyActivity[];
}

// ---------------------------------------------------------------------------
// Client-derived dynasty waiver metrics
//
// The production /api/waivers response returns efficiency_metrics,
// hit_rate_metrics, and timing_metrics as null (they require post-acquisition
// weekly scoring the backend does not yet emit). These three metrics are
// instead derived on the client from fields that DO exist -- most importantly
// `player_value`, which is each player's DYNASTY trade value (long-term worth),
// not a weekly box score. That makes them dynasty-specific by construction.
// ---------------------------------------------------------------------------

/** Net long-term dynasty asset value a manager added vs. shed on the wire. */
export interface DynastyValueMetric {
  roster_id: number;
  team_name: string;
  add_value: number;
  drop_value: number;
  net_value: number;
  add_count: number;
  /** Net value per completed add -- separates "value builder" from "active churner". */
  avg_per_add: number;
}

/** Share of a manager's completed adds that were genuine high-value assets. */
export interface BlueChipMetric {
  roster_id: number;
  team_name: string;
  blue_chip_adds: number;
  total_adds: number;
  rate: number;
}

/** How often a manager won CONTESTED, high-value (blue-chip) players. */
export interface ContestedWinMetric {
  roster_id: number;
  team_name: string;
  won: number;
  attempts: number;
  rate: number;
}

export interface DerivedDynastyMetrics {
  dynastyValue: DynastyValueMetric[];
  blueChip: { threshold: number; managers: BlueChipMetric[] };
  contested: { contestedCount: number; valueThreshold: number; managers: ContestedWinMetric[] };
}