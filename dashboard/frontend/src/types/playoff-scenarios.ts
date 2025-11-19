export interface PlayoffScenario {
  team_name: string;
  division: string;
  current_record: string;
  playoff_probability: number;
  division_winner_probability: number;
  bye_week_probability: number;
  projected_seed: number | null;
  most_likely_seed: number | null;
  seed_probabilities: Record<number, number>;
  playoff_count: number;
  division_winner_count: number;
  bye_week_count: number;
  clinched_playoff: boolean;
  clinched_division: boolean;
  clinched_bye: boolean;
  eliminated: boolean;
}

export interface PlayoffScenariosData {
  num_simulations: number;
  results: PlayoffScenario[];
}

export interface PlayoffScenariosResponse {
  success: boolean;
  data: PlayoffScenariosData;
}
