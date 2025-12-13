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

export interface WaiverWireData {
  all_transactions: WaiverWireTransaction[];
  churn_metrics?: ChurnMetric[];
}