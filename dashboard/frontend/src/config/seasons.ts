/**
 * Seasons Configuration
 *
 * Single source of truth for league season metadata on the frontend.
 * Mirrors pipeline/config/seasons.yaml — update this when a new season starts.
 */

export interface SeasonConfig {
  /** Season key (e.g. "season_2", "season_3") */
  key: string;
  /** Sleeper league ID */
  leagueId: string;
  /** Season display number */
  number: number;
  /** Sleeper/NFL season year */
  year: number;
  /** Calendar display year (year + 1 for offseason context) */
  displayYear: number;
  /** Season status */
  status: 'active' | 'static';
  /** Human-readable description */
  description: string;
}

export const seasons: Record<string, SeasonConfig> = {
  season_2: {
    key: 'season_2',
    leagueId: '1180814327660371968',
    number: 2,
    year: 2024,
    displayYear: 2025,
    status: 'static',
    description: 'Season 2 - Historical data (2024)',
  },
  season_3: {
    key: 'season_3',
    leagueId: '1312166810505719808',
    number: 3,
    year: 2025,
    displayYear: 2026,
    status: 'active',
    description: 'Season 3 - Current season (2025)',
  },
};

/** The currently active season */
export const activeSeason: SeasonConfig =
  Object.values(seasons).find((s) => s.status === 'active') || Object.values(seasons).slice(-1)[0];

/** Look up a season by its Sleeper league ID */
export const getSeasonByLeagueId = (leagueId: string): SeasonConfig | undefined =>
  Object.values(seasons).find((s) => s.leagueId === leagueId);

/** Look up a season by its key */
export const getSeason = (key: string): SeasonConfig | undefined => seasons[key];
