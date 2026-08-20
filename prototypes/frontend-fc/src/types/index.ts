export interface AssetDetail {
  name: string;
  type: string;
  valueThen: number;
  valueNow: number;
}

export interface Trade {
  tradeId: string;
  tradeDate: string;
  transactionId: string;
  teamA: string;
  teamB: string;
  teamAReceived: string[];
  teamBReceived: string[];
  teamAAssets?: AssetDetail[];
  teamBAssets?: AssetDetail[];
  teamAValueThen?: number;
  teamAValueNow?: number;
  teamBValueThen?: number;
  teamBValueNow?: number;
  winnerAtTrade: string;
  winnerCurrent: string;
  marginAtTrade: number;
  marginCurrent: number;
  swingWinner: string;
  swingMargin: number;
  season?: string; // Season identifier (e.g., "season_2", "season_3")
}

export interface Team {
  rosterId: number;
  teamName: string;
  realName: string;
  sleeperUsername: string;
  tradeCount: number;
  winRate: number;
  avgMargin: number;
  totalValueGained: number;
}

export interface LeagueStats {
  totalTrades: number;
  totalTradeValue: number;
  avgTradeMargin: number;
  mostActiveTrader: string;
  biggestWinner: string;
  blockbusterCount: number;
  dateRange: {
    earliest: string;
    latest: string;
  };
}

export interface TradeData {
  metadata: {
    lastUpdated: string;
    totalTrades: number;
    dateRange: {
      earliest: string;
      latest: string;
    };
    filteredCount?: number;
    totalCount?: number;
    filters?: any;
    // Multi-season metadata
    schema_version?: string;
    last_updated?: string;
    seasons_included?: string[];
    total_trades?: number;
    trades_by_season?: Record<string, number>;
    season_info?: Record<string, SeasonInfo>;
  };
  trades: Trade[];
  teams?: Team[];
  statistics?: LeagueStats;
}

export interface SeasonInfo {
  status: 'active' | 'static';
  last_fetched: string;
  league_id?: string;
  year?: number;
  backfill_completed?: boolean;
  incremental_updates?: number;
}

export interface SeasonFilter {
  type: 'all' | 'individual' | 'combination';
  seasons: string[];
  label: string;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

export interface FilterState {
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
  selectedTeams: string[];
  minTradeValue: number;
  blockbusterThreshold: number;
}