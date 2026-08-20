// Standings data structure interfaces

export interface TeamRecord {
  wins: number;
  losses: number;
  ties?: number;
}

export interface WeeklyMatchup {
  week: number;
  opponent_id: number | null;
  opponent_name: string;
  points_for: number;
  points_against: number;
  result: 'W' | 'L' | 'T' | 'UPCOMING';
  beat_median: boolean | null;
  median_score: number;
}

export interface StandingsTeam {
  roster_id: number;
  team_name: string;
  owner_name: string;
  rank: number;
  record: TeamRecord;
  matchup_record: TeamRecord;
  median_record: TeamRecord;
  division_record: TeamRecord;
  points_for: number;
  points_against: number;
  schedule: WeeklyMatchup[];
}

export interface Division {
  division_id: number;
  division_name: string;
  teams: StandingsTeam[];
}

export interface StandingsMetadata {
  current_week: number;
  total_weeks: number;
  last_updated: string;
  season: number;
}

export interface StandingsData {
  divisions: Division[];
  metadata: StandingsMetadata;
}

// Helper type for table sorting
export type StandingsSortField = 
  | 'rank'
  | 'teamName'
  | 'ownerName'
  | 'record'
  | 'medianRecord'
  | 'divisionRecord'
  | 'pointsFor'
  | 'pointsAgainst';

export interface StandingsSortConfig {
  field: StandingsSortField;
  direction: 'asc' | 'desc';
}
