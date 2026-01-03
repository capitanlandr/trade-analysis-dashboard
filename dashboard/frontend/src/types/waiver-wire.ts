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

export interface WaiverWireData {
  all_transactions: WaiverWireTransaction[];
  churn_metrics?: ChurnMetric[];
  efficiency_metrics?: EfficiencyData;
  hit_rate_metrics?: HitRateData;
  timing_metrics?: TimingData;
}