// Team data structure interfaces
export interface Team {
  sleeperUsername: string;
  realName: string;
  tradeCount: number;
  totalValueGained: number;
  winRate: number;
}

export interface TeamsApiResponse {
  data: {
    data: {
      teams: Team[];
    };
  };
}

// Sorting configuration
export type TeamSortField = keyof Team;
export type SortDirection = 'asc' | 'desc';

export interface SortConfig {
  field: TeamSortField;
  direction: SortDirection;
}

// Filter configuration
export interface TeamFilters {
  searchTerm: string;
  minTrades: number;
  minWinRate?: number;
  maxWinRate?: number;
  performanceTier?: 'all' | 'winners' | 'losers';
}