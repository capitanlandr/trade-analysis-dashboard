/**
 * Draft Order Projection Types
 * 
 * Types for progressive draft order determination system that tracks
 * locked vs uncertain picks during playoffs.
 */

export type PickCertainty = 'locked' | 'pending' | 'unknown';

export type DeterminationLevel = 'none' | 'partial' | 'complete';

/**
 * Possible outcome for an uncertain pick
 */
export interface PickScenario {
  roster_id: number;
  team_name: string;
  condition: string;
  current_owner_roster_id: number;
  current_owner_team_name: string;
  traded: boolean;
}

/**
 * Owner information for a pick
 */
export interface PickOwner {
  roster_id: number;
  team_name: string;
  regular_season_rank?: number;
  description?: string;
}

/**
 * Finalized draft pick (certainty: "locked")
 */
export interface LockedPick {
  pick_number: number;
  pick_label: string;
  tier: string;
  certainty: 'locked';
  original_owner: PickOwner;
  current_owner: PickOwner;
  traded: boolean;
}

/**
 * Uncertain draft pick with possible scenarios (certainty: "pending" or "unknown")
 */
export interface UncertainPick {
  pick_number: number;
  pick_label: string;
  tier: string;
  certainty: 'pending' | 'unknown';
  scenarios: PickScenario[];
  pending_game?: string;
}

/**
 * Union type for all draft picks
 */
export type DraftPick = LockedPick | UncertainPick;

/**
 * Type guard to check if pick is locked
 */
export function isLockedPick(pick: DraftPick): pick is LockedPick {
  return pick.certainty === 'locked';
}

/**
 * Type guard to check if pick is uncertain
 */
export function isUncertainPick(pick: DraftPick): pick is UncertainPick {
  return pick.certainty === 'pending' || pick.certainty === 'unknown';
}

/**
 * Summary statistics for draft order
 */
export interface DraftOrderSummary {
  total_picks: number;
  locked_picks: number;
  uncertain_picks: number;
}

/**
 * Progressive draft order data structure
 */
export interface ProgressiveDraftOrder {
  season: number;
  draft_year: number;
  through_week: number;
  determination_level: DeterminationLevel;
  last_updated: string;
  summary: DraftOrderSummary;
  draft_order: {
    round_1: DraftPick[];
    round_2: DraftPick[];
    round_3: DraftPick[];
    round_4: DraftPick[];
  };
}
