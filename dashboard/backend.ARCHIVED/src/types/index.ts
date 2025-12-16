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
  teamAValueThen: number;
  teamAValueNow: number;
  teamBValueThen: number;
  teamBValueNow: number;
  winnerAtTrade: string;
  winnerCurrent: string;
  marginAtTrade: number;
  marginCurrent: number;
  swingWinner: string;
  swingMargin: number;
}

export interface Team {
  rosterId: number;
  teamName: string;
  realName: string;
  sleeperUsername: string;
  nickname: string;
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
  };
  trades: Trade[];
  teams: Team[];
  statistics: LeagueStats;
}

export interface SocketEvents {
  'trades-updated': {
    newTradesCount: number;
    lastUpdate: string;
  };
  'pipeline-status': {
    isRunning: boolean;
    currentStage: string;
    progress: number;
  };
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}