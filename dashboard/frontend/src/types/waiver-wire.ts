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

export interface WaiverWireData {
  all_transactions: WaiverWireTransaction[];
}