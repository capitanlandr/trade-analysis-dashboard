export interface WaiverWireTransaction {
  transaction_id: string;
  type: 'waiver' | 'free_agent';
  action: 'add' | 'drop' | 'unknown';
  status: 'complete' | 'failed';
  team_name: string;
  roster_id: number;
  player_name: string;
  player_id: string;
  waiver_bid: number;
  week: number;
  created_date: string;
  status_updated_date: string;
  notes: string;
  sequence: number | null;
  priority: number | null;
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

export interface WaiverWireData {
  all_transactions: WaiverWireTransaction[];
  churn_metrics?: ChurnMetric[];
  efficiency_metrics?: EfficiencyData;
}