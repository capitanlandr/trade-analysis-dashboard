#!/usr/bin/env python3
"""
Calculate Playoff Scenarios for All Teams

Determines:
- Playoff clinch scenarios (guaranteed top 6)
- Division clinch scenarios (guaranteed division winner)
- Elimination scenarios (cannot make top 6)
- Magic numbers and key matchups

Outputs: playoff_scenarios.json
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Playoff Scenarios Calculator')


def load_standings() -> Dict:
    """Load current standings from JSON"""
    # Try multiple possible locations
    possible_paths = [
        Path(__file__).parent.parent / 'dashboard/frontend/public/api-standings.json',
        Path(__file__).parent.parent.parent / 'trade-analysis-dashboard-clean/dashboard/frontend/public/api-standings.json',
        Path('trade-analysis-dashboard-clean/dashboard/frontend/public/api-standings.json')
    ]
    
    for standings_file in possible_paths:
        if standings_file.exists():
            logger.info(f"Loading standings from: {standings_file}")
            with open(standings_file) as f:
                return json.load(f)
    
    raise FileNotFoundError(f"Standings file not found in any of: {possible_paths}")


def get_remaining_schedule(team_schedule: List[Dict], current_week: int = 11) -> List[Dict]:
    """Get remaining games for a team"""
    return [game for game in team_schedule if game['week'] > current_week]


def get_current_playoff_seeding(all_teams: List[Dict], divisions_data: List[Dict]) -> Tuple[List[Dict], Dict]:
    """
    Calculate current playoff seeding using actual playoff rules:
    - Seeds 1-3: Division winners (best record in each division)
    - Seeds 4-6: Best remaining records (wildcards)
    
    Returns:
        Tuple of (playoff_teams, seventh_place_team)
    """
    # Get division winners
    division_winners = []
    for div_data in divisions_data:
        div_teams = div_data['teams']
        if div_teams:
            # Sort by wins (simplified tiebreaker)
            winner = max(div_teams, key=lambda t: t['record']['wins'])
            division_winners.append(winner)
    
    # Sort division winners by record for seeds 1-3
    division_winners.sort(key=lambda t: t['record']['wins'], reverse=True)
    
    # Get remaining teams (non-division winners)
    division_winner_names = {t['team_name'] for t in division_winners}
    remaining_teams = [t for t in all_teams if t['team_name'] not in division_winner_names]
    
    # Sort remaining by record for wildcards
    remaining_teams.sort(key=lambda t: t['record']['wins'], reverse=True)
    
    # Top 3 remaining = wildcards (seeds 4-6)
    wildcards = remaining_teams[:3]
    
    # Combine for playoff teams
    playoff_teams = division_winners + wildcards
    
    # 7th place = first wildcard out
    seventh_place = remaining_teams[3] if len(remaining_teams) > 3 else None
    
    return playoff_teams, seventh_place


def calculate_team_scenarios(team: Dict, all_teams: List[Dict], division_teams: List[Dict], 
                            playoff_teams: List[Dict], seventh_place: Dict) -> Dict:
    """
    Calculate playoff scenarios for a single team.
    
    Returns:
        Dict with clinch/elimination info and magic numbers
    """
    team_name = team['team_name']
    current_wins = team['record']['wins']
    current_losses = team['record']['losses']
    
    # Get remaining games
    remaining = get_remaining_schedule(team['schedule'])
    num_remaining = len(remaining)
    max_possible_wins = current_wins + (num_remaining * 2)
    min_possible_wins = current_wins
    
    logger.info(f"Calculating scenarios for {team_name} ({current_wins}-{current_losses})")
    
    # Check if currently in playoffs
    is_in_playoffs = team_name in [t['team_name'] for t in playoff_teams]
    current_seed = next((i for i, t in enumerate(playoff_teams, 1) if t['team_name'] == team_name), None)
    
    # PLAYOFF CLINCH: Different logic for division leaders vs wildcards
    playoff_clinched = False
    playoff_magic_number = None
    playoff_elimination = False
    
    # Check if currently a division leader
    is_division_leader = False
    if is_in_playoffs and current_seed and current_seed <= 3:
        is_division_leader = True
    
    if is_division_leader:
        # Division leaders: clinch playoffs if they can maintain division lead
        # They're guaranteed a playoff spot as long as they stay division winner
        # So playoff clinch = division clinch
        logger.info(f"  Currently division leader (Seed {current_seed})")
        # Playoff status will be determined by division clinch
        playoff_clinched = False  # Will be set based on division status
    elif seventh_place:
        # Wildcards: need to beat 7th place team
        seventh_remaining = get_remaining_schedule(seventh_place['schedule'])
        seventh_best = seventh_place['record']['wins'] + len(seventh_remaining) * 2
        
        logger.info(f"  7th place: {seventh_place['team_name']} ({seventh_place['record']['wins']}-{seventh_place['record']['losses']}, best: {seventh_best})")
        
        if min_possible_wins > seventh_best:
            playoff_clinched = True
            logger.info(f"  ✓ {team_name} has clinched playoffs")
        elif max_possible_wins <= seventh_best:
            playoff_elimination = True
            logger.info(f"  ✗ {team_name} has been eliminated from playoffs")
        else:
            playoff_magic_number = seventh_best - current_wins + 1
            logger.info(f"  • {team_name} needs {playoff_magic_number} wins to clinch playoffs")
    
    # DIVISION CLINCH: Need to finish ahead of all division rivals
    division_clinched = False
    division_magic_numbers = {}
    division_eliminated = False
    
    division_rivals = [t for t in division_teams if t['team_name'] != team_name]
    
    for rival in division_rivals:
        rival_remaining = get_remaining_schedule(rival['schedule'])
        rival_best = rival['record']['wins'] + len(rival_remaining) * 2
        
        if min_possible_wins > rival_best:
            # Already clinched over this rival
            continue
        elif max_possible_wins <= rival_best:
            # Cannot catch this rival
            division_eliminated = True
        else:
            magic = rival_best - current_wins + 1
            # Only include if achievable
            if magic <= num_remaining * 2:
                division_magic_numbers[rival['team_name']] = magic
    
    if not division_magic_numbers and not division_eliminated:
        division_clinched = True
        logger.info(f"  ✓ {team_name} has clinched division")
    elif division_eliminated:
        logger.info(f"  ✗ {team_name} eliminated from division race")
    elif division_magic_numbers:
        max_division_magic = max(division_magic_numbers.values())
        logger.info(f"  • {team_name} needs {max_division_magic} wins to clinch division")
    
    # For division leaders, playoff clinch = division clinch
    if is_division_leader:
        if division_clinched:
            playoff_clinched = True
            logger.info(f"  ✓ {team_name} has clinched playoffs (via division)")
        elif not division_magic_numbers:
            # No achievable division magic numbers = can't clinch division = can lose division
            # But they're still in playoffs as long as they're division leader
            logger.info(f"  • {team_name} in playoffs as division leader (not clinched)")
    
    # Generate clinch scenarios
    clinch_scenarios = []
    
    if not playoff_clinched and playoff_magic_number and playoff_magic_number <= num_remaining * 2:
        # Generate specific scenarios
        if playoff_magic_number <= 2:
            clinch_scenarios.append("Win 2-0 in Week 12")
        elif playoff_magic_number <= 4:
            clinch_scenarios.append("Win 2-0 in Week 12 + 2-0 in Week 13")
            clinch_scenarios.append("Win 2-0 in Week 12 + 1-1 in Week 13 + 1-1 in Week 14")
        elif playoff_magic_number <= 6:
            clinch_scenarios.append("Win out (2-0, 2-0, 2-0)")
    
    return {
        'team_name': team_name,
        'current_record': {
            'wins': current_wins,
            'losses': current_losses
        },
        'current_seed': current_seed,
        'in_playoffs': is_in_playoffs,
        'remaining_games': num_remaining,
        'best_case_record': f"{max_possible_wins}-{current_losses}",
        'worst_case_record': f"{min_possible_wins}-{current_losses + num_remaining * 2}",
        'playoff_status': {
            'clinched': playoff_clinched,
            'eliminated': playoff_elimination,
            'magic_number': playoff_magic_number,
            'clinch_scenarios': clinch_scenarios
        },
        'division_status': {
            'clinched': division_clinched,
            'eliminated': division_eliminated,
            'magic_numbers': division_magic_numbers
        },
        'key_matchups': [
            {
                'week': game['week'],
                'opponent': game['opponent_name']
            }
            for game in remaining
        ]
    }


def main():
    """Main execution"""
    try:
        logger.info("Loading standings data...")
        standings = load_standings()
        
        # Collect all teams
        all_teams = []
        for div in standings['divisions']:
            all_teams.extend(div['teams'])
        
        logger.info(f"Calculating scenarios for {len(all_teams)} teams...")
        
        # Calculate current playoff seeding
        logger.info("\nCalculating current playoff seeding...")
        playoff_teams, seventh_place = get_current_playoff_seeding(all_teams, standings['divisions'])
        
        logger.info("Current Playoff Seeds:")
        for i, team in enumerate(playoff_teams, 1):
            seed_type = "Division Winner" if i <= 3 else "Wildcard"
            logger.info(f"  {i}. {team['team_name']} ({team['record']['wins']}-{team['record']['losses']}) - {seed_type}")
        
        if seventh_place:
            logger.info(f"  7. {seventh_place['team_name']} ({seventh_place['record']['wins']}-{seventh_place['record']['losses']}) - First Out")
        
        # Calculate scenarios for each team
        scenarios = []
        
        for div in standings['divisions']:
            division_name = div['division_name']
            division_teams = div['teams']
            
            logger.info(f"\nProcessing {division_name} Division...")
            
            for team in division_teams:
                team_scenarios = calculate_team_scenarios(team, all_teams, division_teams, playoff_teams, seventh_place)
                team_scenarios['division'] = division_name
                scenarios.append(team_scenarios)
        
        # Sort by current seed (playoff teams first, then by wins)
        scenarios.sort(key=lambda s: (not s['in_playoffs'], -s['current_record']['wins']))
        
        # Create output structure
        output = {
            'generated_at': '2025-11-18',  # Current date
            'current_week': 11,
            'weeks_remaining': 3,
            'playoff_spots': 6,
            'scenarios': scenarios,
            'summary': {
                'clinched_playoff': [s['team_name'] for s in scenarios if s['playoff_status']['clinched']],
                'clinched_division': [s['team_name'] for s in scenarios if s['division_status']['clinched']],
                'eliminated': [s['team_name'] for s in scenarios if s['playoff_status']['eliminated']],
                'in_contention': [s['team_name'] for s in scenarios 
                                 if not s['playoff_status']['clinched'] 
                                 and not s['playoff_status']['eliminated']]
            }
        }
        
        # Save to JSON
        output_file = Path(__file__).parent.parent / 'playoff_scenarios.json'
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"\n✓ Playoff scenarios saved to: {output_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("PLAYOFF SCENARIOS SUMMARY")
        print("="*80)
        
        print(f"\nClinched Playoffs ({len(output['summary']['clinched_playoff'])}):")
        for team in output['summary']['clinched_playoff']:
            print(f"  ✓ {team}")
        
        print(f"\nClinched Division ({len(output['summary']['clinched_division'])}):")
        for team in output['summary']['clinched_division']:
            print(f"  ✓ {team}")
        
        print(f"\nEliminated ({len(output['summary']['eliminated'])}):")
        for team in output['summary']['eliminated']:
            print(f"  ✗ {team}")
        
        print(f"\nIn Contention ({len(output['summary']['in_contention'])}):")
        for team in output['summary']['in_contention']:
            scenario = next(s for s in scenarios if s['team_name'] == team)
            magic = scenario['playoff_status']['magic_number']
            print(f"  • {team} (magic number: {magic})")
        
        print("\n" + "="*80)
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to calculate playoff scenarios: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
