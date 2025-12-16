#!/usr/bin/env python3
"""
Monte Carlo Playoff Scenario Simulator

Simulates all possible outcomes for remaining games and calculates:
- Playoff probability for each team
- Key game impact analysis
- Clinch/elimination scenarios

Uses 10,000 random simulations with proper tiebreaker rules.
"""

import json
import random
import logging
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from copy import deepcopy
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import fetch_with_retry, APIError
from utils.week_config import get_current_week_from_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Playoff Simulator')

# League configuration
LEAGUE_ID = "1180814327660371968"
SLEEPER_API_BASE = "https://api.sleeper.app/v1"


# Week detection now handled by centralized config (detect_current_week.py)
# get_current_week() function removed - use get_current_week_from_config() instead


def load_standings() -> Dict:
    """Load current standings from JSON"""
    possible_paths = [
        Path(__file__).parent.parent.parent / 'dashboard/frontend/public/api-standings.json',
        Path(__file__).parent.parent / 'dashboard/frontend/public/api-standings.json',
        Path('trade-analysis-dashboard-clean/dashboard/frontend/public/api-standings.json'),
        Path('dashboard/frontend/public/api-standings.json')
    ]
    
    for standings_file in possible_paths:
        if standings_file.exists():
            logger.info(f"Loading standings from: {standings_file}")
            with open(standings_file) as f:
                return json.load(f)
    
    # Log attempted paths for debugging
    logger.error("Standings file not found. Attempted paths:")
    for path in possible_paths:
        logger.error(f"  - {path.absolute()} (exists: {path.exists()})")
    raise FileNotFoundError("Standings file not found")


def get_remaining_schedule(team_schedule: List[Dict], current_week: int) -> List[Dict]:
    """
    Get remaining games for a team.
    
    Args:
        team_schedule: List of game dictionaries with 'week' field
        current_week: Current week number (games with week > current_week are remaining)
        
    Returns:
        List of games that haven't been played yet
    """
    return [game for game in team_schedule if game['week'] > current_week]


def compare_teams_tiebreaker(team1: Dict, team2: Dict) -> int:
    """
    Compare two teams using tiebreaker rules.
    Returns: -1 if team1 better, 1 if team2 better, 0 if tied
    
    Tiebreakers:
    1. Win/Loss record
    2. Head-to-head record (stored in h2h_wins)
    3. Division record
    4. Points for
    5. Points against (lower is better)
    """
    # 1. Win/Loss record
    if team1['sim_wins'] != team2['sim_wins']:
        return -1 if team1['sim_wins'] > team2['sim_wins'] else 1
    
    # 2. Head-to-head record
    h2h_1_vs_2 = team1.get('h2h_wins', {}).get(team2['roster_id'], 0)
    h2h_2_vs_1 = team2.get('h2h_wins', {}).get(team1['roster_id'], 0)
    if h2h_1_vs_2 != h2h_2_vs_1:
        return -1 if h2h_1_vs_2 > h2h_2_vs_1 else 1
    
    # 3. Division record
    div_wins_1 = team1.get('sim_division_wins', 0)
    div_wins_2 = team2.get('sim_division_wins', 0)
    if div_wins_1 != div_wins_2:
        return -1 if div_wins_1 > div_wins_2 else 1
    
    # 4. Points for
    pf_1 = team1.get('sim_points_for', 0)
    pf_2 = team2.get('sim_points_for', 0)
    if abs(pf_1 - pf_2) > 0.01:
        return -1 if pf_1 > pf_2 else 1
    
    # 5. Points against (lower is better)
    pa_1 = team1.get('sim_points_against', 0)
    pa_2 = team2.get('sim_points_against', 0)
    if abs(pa_1 - pa_2) > 0.01:
        return -1 if pa_1 < pa_2 else 1
    
    return 0


def calculate_playoff_seeding(teams: List[Dict], divisions_data: List[Dict]) -> List[Dict]:
    """
    Calculate playoff seeding using actual playoff rules with tiebreakers.
    Returns list of 6 playoff teams in seed order.
    
    Rules:
    1. Top team from each division gets automatic playoff berth (3 teams)
    2. Division winners are seeded 1-3 by their records
    3. Next 3 best teams by record get wildcard spots (seeds 4-6)
    """
    from functools import cmp_to_key
    
    # Get division winners (guaranteed playoff spots)
    division_winners = []
    for div_data in divisions_data:
        div_id = div_data['division_id']
        div_teams = [t for t in teams if t['division_id'] == div_id]
        
        if div_teams:
            # Sort by tiebreakers
            div_teams_sorted = sorted(div_teams, key=cmp_to_key(compare_teams_tiebreaker))
            winner = div_teams_sorted[0]
            division_winners.append(winner)
    
    # Sort division winners by record for seeds 1-3
    division_winners.sort(key=cmp_to_key(compare_teams_tiebreaker))
    
    # Get remaining teams (non-division winners)
    division_winner_ids = {t['roster_id'] for t in division_winners}
    remaining_teams = [t for t in teams if t['roster_id'] not in division_winner_ids]
    
    # Sort remaining by tiebreakers for wildcards
    remaining_teams.sort(key=cmp_to_key(compare_teams_tiebreaker))
    
    # Top 3 remaining = wildcards (seeds 4-6)
    wildcards = remaining_teams[:3]
    
    # Combine: division winners (1-3) + wildcards (4-6)
    playoff_teams = division_winners + wildcards
    
    return playoff_teams


def simulate_single_scenario(teams: List[Dict], divisions_data: List[Dict], 
                            matchups_by_week: Dict) -> Dict:
    """
    Simulate one possible outcome for all remaining games.
    Returns dict with playoff teams, division winners, and bye week teams.
    """
    # Deep copy teams to avoid modifying originals
    sim_teams = deepcopy(teams)
    
    # Simulate each week's games
    for week, matchups in matchups_by_week.items():
        for matchup in matchups:
            team1_id = matchup['team1_id']
            team2_id = matchup['team2_id']
            
            # Find teams
            team1 = next(t for t in sim_teams if t['roster_id'] == team1_id)
            team2 = next(t for t in sim_teams if t['roster_id'] == team2_id)
            
            # Random H2H outcome
            h2h_winner = random.choice([team1_id, team2_id])
            
            # Random median outcomes (independent for each team)
            team1_beats_median = random.choice([True, False])
            team2_beats_median = random.choice([True, False])
            
            # Update records
            if h2h_winner == team1_id:
                team1['sim_wins'] += 1
                team1['h2h_wins'][team2_id] = team1['h2h_wins'].get(team2_id, 0) + 1
                if team1['division_id'] == team2['division_id']:
                    team1['sim_division_wins'] += 1
            else:
                team2['sim_wins'] += 1
                team2['h2h_wins'][team1_id] = team2['h2h_wins'].get(team1_id, 0) + 1
                if team1['division_id'] == team2['division_id']:
                    team2['sim_division_wins'] += 1
            
            # Median wins
            if team1_beats_median:
                team1['sim_wins'] += 1
            if team2_beats_median:
                team2['sim_wins'] += 1
            
            # Update points (simplified - just add random points)
            team1['sim_points_for'] += random.uniform(80, 150)
            team2['sim_points_for'] += random.uniform(80, 150)
    
    # Calculate playoff seeding
    playoff_teams = calculate_playoff_seeding(sim_teams, divisions_data)
    
    # Extract division winners (seeds 1-3) and bye week teams (seeds 1-2)
    division_winners = playoff_teams[:3]
    bye_week_teams = playoff_teams[:2]
    
    # Create seed mapping
    seed_mapping = {}
    for i, team in enumerate(playoff_teams, 1):
        seed_mapping[team['team_name']] = i
    
    return {
        'playoff_teams': [t['team_name'] for t in playoff_teams],
        'division_winners': [t['team_name'] for t in division_winners],
        'bye_week_teams': [t['team_name'] for t in bye_week_teams],
        'seed_mapping': seed_mapping
    }


def run_simulations(standings: Dict, current_week: int, num_simulations: int = 10000) -> Dict:
    """
    Run Monte Carlo simulations to calculate playoff probabilities.
    
    Args:
        standings: Standings data with team records and schedules
        current_week: Current week number for filtering remaining games
        num_simulations: Number of simulations to run
        
    Returns:
        Dictionary with playoff probabilities for each team
    """
    logger.info(f"Starting playoff simulation for Week {current_week}")
    logger.info(f"Running {num_simulations:,} simulations...")
    
    # Prepare teams data
    all_teams = []
    for div in standings['divisions']:
        for team in div['teams']:
            # Build historical H2H record from completed games
            historical_h2h = {}
            for game in team['schedule']:
                if game['result'] in ['W', 'L', 'T'] and game.get('opponent_id'):
                    opponent_id = game['opponent_id']
                    if game['result'] == 'W':
                        historical_h2h[opponent_id] = historical_h2h.get(opponent_id, 0) + 1
            
            team_data = {
                'roster_id': team['roster_id'],
                'team_name': team['team_name'],
                'division_id': div['division_id'],
                'division_name': div['division_name'],
                'current_wins': team['record']['wins'],
                'current_losses': team['record']['losses'],
                'current_h2h_wins': team['matchup_record']['wins'],
                'current_division_wins': team['division_record']['wins'],
                'points_for': team['points_for'],
                'points_against': team['points_against'],
                'schedule': team['schedule'],
                'historical_h2h': historical_h2h,  # H2H wins from completed games
                'h2h_wins': {},  # Will be populated during simulation
                'playoff_count': 0,
                'division_winner_count': 0,
                'bye_week_count': 0,
                'seed_counts': defaultdict(int)  # Track how often they get each seed
            }
            all_teams.append(team_data)
    
    # Calculate current playoff seeding (if season ended today)
    logger.info("Calculating current playoff seeding...")
    current_seeding_teams = []
    for team in all_teams:
        current_seeding_teams.append({
            'roster_id': team['roster_id'],
            'team_name': team['team_name'],
            'division_id': team['division_id'],
            'sim_wins': team['current_wins'],
            'sim_division_wins': team['current_division_wins'],
            'sim_points_for': team['points_for'],
            'sim_points_against': team['points_against'],
            'h2h_wins': team['historical_h2h'].copy()
        })
    
    current_playoff_teams = calculate_playoff_seeding(current_seeding_teams, standings['divisions'])
    current_seed_map = {team['team_name']: idx + 1 for idx, team in enumerate(current_playoff_teams)}
    
    # Build matchup schedule for remaining weeks
    matchups_by_week = defaultdict(list)
    processed_matchups = set()
    
    for team in all_teams:
        remaining = get_remaining_schedule(team['schedule'], current_week)
        for game in remaining:
            week = game['week']
            opponent_name = game['opponent_name']
            
            # Find opponent
            opponent = next((t for t in all_teams if t['team_name'] == opponent_name), None)
            if not opponent:
                continue
            
            # Create unique matchup key (sorted to avoid duplicates)
            matchup_key = tuple(sorted([team['roster_id'], opponent['roster_id']]))
            week_key = (week, matchup_key)
            
            if week_key not in processed_matchups:
                matchups_by_week[week].append({
                    'team1_id': team['roster_id'],
                    'team2_id': opponent['roster_id']
                })
                processed_matchups.add(week_key)
    
    total_matchups = sum(len(m) for m in matchups_by_week.values())
    logger.info(f"Found {total_matchups} remaining matchups across {len(matchups_by_week)} weeks")
    
    if total_matchups == 0:
        logger.warning("No remaining matchups found - season may be complete")
    
    # Run simulations
    for i in range(num_simulations):
        if (i + 1) % 1000 == 0:
            logger.info(f"  Completed {i + 1}/{num_simulations} simulations...")
        
        # Reset simulation state for each team
        for team in all_teams:
            team['sim_wins'] = team['current_wins']
            team['sim_division_wins'] = team['current_division_wins']
            team['sim_points_for'] = team['points_for']
            team['sim_points_against'] = team['points_against']
            # Start with historical H2H wins, will add simulated games on top
            team['h2h_wins'] = team['historical_h2h'].copy()
        
        # Simulate and get results
        sim_result = simulate_single_scenario(all_teams, standings['divisions'], matchups_by_week)
        
        # Increment counts for teams that made it
        for team in all_teams:
            team_name = team['team_name']
            
            if team_name in sim_result['playoff_teams']:
                team['playoff_count'] += 1
                
                # Track seed
                seed = sim_result['seed_mapping'].get(team_name)
                if seed:
                    team['seed_counts'][seed] += 1
            
            if team_name in sim_result['division_winners']:
                team['division_winner_count'] += 1
            if team_name in sim_result['bye_week_teams']:
                team['bye_week_count'] += 1
    
    # Calculate probabilities
    results = []
    for team in all_teams:
        playoff_prob = (team['playoff_count'] / num_simulations) * 100
        division_prob = (team['division_winner_count'] / num_simulations) * 100
        bye_prob = (team['bye_week_count'] / num_simulations) * 100
        
        # Calculate seed probabilities
        seed_probabilities = {}
        for seed, count in team['seed_counts'].items():
            seed_probabilities[seed] = round((count / num_simulations) * 100, 1)
        
        results.append({
            'team_name': team['team_name'],
            'division': team['division_name'],
            'current_record': f"{team['current_wins']}-{team['current_losses']}",
            'playoff_probability': round(playoff_prob, 1),
            'division_winner_probability': round(division_prob, 1),
            'bye_week_probability': round(bye_prob, 1),
            'seed_probabilities': seed_probabilities,
            'playoff_count': team['playoff_count'],
            'division_winner_count': team['division_winner_count'],
            'bye_week_count': team['bye_week_count'],
            'clinched_playoff': playoff_prob == 100.0,
            'clinched_division': division_prob == 100.0,
            'clinched_bye': bye_prob == 100.0,
            'eliminated': playoff_prob == 0.0,
            'current_seed': current_seed_map.get(team['team_name'])  # Seed if season ended today
        })
    
    # Sort by playoff probability
    results.sort(key=lambda r: r['playoff_probability'], reverse=True)
    
    # Assign most_likely_seed (projected seed from simulations) to top 6 teams
    for i, result in enumerate(results):
        if i < 6 and result['seed_probabilities']:
            # Find the seed they get most often in simulations
            result['most_likely_seed'] = max(result['seed_probabilities'].items(), key=lambda x: x[1])[0]
        else:
            result['most_likely_seed'] = None
        
        # projected_seed = most likely seed from simulations (different from current_seed)
        result['projected_seed'] = result['most_likely_seed']
    
    # Log summary statistics
    clinched_playoff = sum(1 for r in results if r['clinched_playoff'])
    clinched_division = sum(1 for r in results if r['clinched_division'])
    clinched_bye = sum(1 for r in results if r['clinched_bye'])
    eliminated = sum(1 for r in results if r['eliminated'])
    
    logger.info(f"Simulation complete - Summary:")
    logger.info(f"  Teams clinched playoff: {clinched_playoff}")
    logger.info(f"  Teams clinched division: {clinched_division}")
    logger.info(f"  Teams clinched bye: {clinched_bye}")
    logger.info(f"  Teams eliminated: {eliminated}")
    
    return {
        'metadata': {
            'current_week': current_week,
            'last_updated': datetime.now().isoformat(),
            'season': 2025
        },
        'num_simulations': num_simulations,
        'results': results
    }


def main():
    """Main execution"""
    try:
        # Use centralized week detection from config
        # Week is determined by detect_current_week.py using roster validation
        current_week = get_current_week_from_config()
        logger.info(f"Current week from centralized config: {current_week}")
        
        logger.info("Loading standings data...")
        standings = load_standings()
        
        # Run simulations
        simulation_results = run_simulations(standings, current_week, num_simulations=20000)
        
        # Write results to single source of truth
        dashboard_file = Path(__file__).parent.parent.parent / 'dashboard/frontend/public/api-playoff-scenarios.json'
        dashboard_file.parent.mkdir(parents=True, exist_ok=True)
        with open(dashboard_file, 'w') as f:
            json.dump(simulation_results, f, indent=2)
        logger.info(f"✓ Generated {dashboard_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("PLAYOFF PROBABILITY SIMULATION RESULTS")
        print("="*80)
        print(f"Simulations: {simulation_results['num_simulations']:,}")
        print()
        
        print(f"{'Team':<30} {'Record':<10} {'Seed':<6} {'Playoff':<10} {'Division':<10} {'Bye':<10}")
        print("-" * 90)
        
        for result in simulation_results['results']:
            status = ""
            if result['clinched_playoff']:
                status = " ✓"
            elif result['eliminated']:
                status = " ✗"
            
            seed_str = str(result['projected_seed']) if result['projected_seed'] else "N/A"
            
            print(f"{result['team_name']:<30} {result['current_record']:<10} "
                  f"{seed_str:<6} "
                  f"{result['playoff_probability']:>5.1f}%{status:<4} "
                  f"{result['division_winner_probability']:>5.1f}%     "
                  f"{result['bye_week_probability']:>5.1f}%")
        
        print("="*80)
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to run simulations: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
