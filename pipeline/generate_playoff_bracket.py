#!/usr/bin/env python3
"""
Generate Current Playoff Bracket from Sleeper League Data

Applies custom league playoff rules:
- 6 teams make playoffs
- Seeds 1-3: Division winners (by tiebreakers)
- Seeds 4-6: Best remaining records (by tiebreakers)
- Tiebreakers: W/L record → H2H record → Division record → Points For → Points Against

Usage:
    python generate_playoff_bracket.py
"""

import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import sys

from config import get_config
from utils.logging_config import setup_logging
from utils.api_client import fetch_with_retry, APIError

logger = setup_logging('Playoff Bracket Generator')
config = get_config()


@dataclass
class TeamRecord:
    """Team's season record and stats"""
    roster_id: int
    owner_id: str
    team_name: str
    division: int
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float
    h2h_wins: Dict[int, int] = field(default_factory=dict)  # opponent_roster_id -> wins
    division_wins: int = 0
    division_losses: int = 0
    
    @property
    def win_pct(self) -> float:
        """Calculate win percentage"""
        total = self.wins + self.losses + self.ties
        if total == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / total
    
    def get_h2h_record(self, opponent_roster_id: int) -> Tuple[int, int]:
        """Get head-to-head record against specific opponent"""
        wins = self.h2h_wins.get(opponent_roster_id, 0)
        # Assume symmetric - if we have 2 wins, they have 0
        return (wins, 0)  # Simplified - full implementation would track losses too


def fetch_league_data() -> Dict:
    """Fetch all necessary league data from Sleeper API"""
    league_id = config.league_id
    base_url = config.sleeper_api.base_url
    timeout = config.sleeper_api.timeout
    
    logger.info(f"Fetching league data for: {league_id}")
    
    # Get league info
    league = fetch_with_retry(f"{base_url}/league/{league_id}", timeout=timeout)
    season = league.get('season')
    league_name = league.get('name')
    
    logger.info(f"League: {league_name} ({season})")
    
    # Get users
    users = fetch_with_retry(f"{base_url}/league/{league_id}/users", timeout=timeout)
    user_map = {u['user_id']: u for u in users}
    
    # Get rosters
    rosters = fetch_with_retry(f"{base_url}/league/{league_id}/rosters", timeout=timeout)
    
    # Get matchups for all weeks to calculate records
    current_week = league.get('settings', {}).get('leg', 1)
    
    return {
        'league': league,
        'users': user_map,
        'rosters': rosters,
        'current_week': current_week,
        'season': season,
        'league_name': league_name
    }


def get_team_name(roster: Dict, user_map: Dict) -> str:
    """Get team name from roster"""
    owner_id = roster.get('owner_id')
    if not owner_id:
        return f"Team {roster['roster_id']}"
    
    user = user_map.get(owner_id, {})
    
    # Try team_name first, then display_name, then username
    return (
        user.get('metadata', {}).get('team_name') or
        user.get('display_name') or
        user.get('username') or
        f"Team {roster['roster_id']}"
    )


def calculate_team_records(league_data: Dict) -> List[TeamRecord]:
    """Calculate complete records for all teams"""
    rosters = league_data['rosters']
    user_map = league_data['users']
    league_id = config.league_id
    current_week = league_data['current_week']
    
    # Initialize team records
    teams = []
    for roster in rosters:
        team = TeamRecord(
            roster_id=roster['roster_id'],
            owner_id=roster.get('owner_id', ''),
            team_name=get_team_name(roster, user_map),
            division=roster.get('settings', {}).get('division', 0),
            wins=roster.get('settings', {}).get('wins', 0),
            losses=roster.get('settings', {}).get('losses', 0),
            ties=roster.get('settings', {}).get('ties', 0),
            points_for=roster.get('settings', {}).get('fpts', 0) + roster.get('settings', {}).get('fpts_decimal', 0) / 100,
            points_against=roster.get('settings', {}).get('fpts_against', 0) + roster.get('settings', {}).get('fpts_against_decimal', 0) / 100
        )
        teams.append(team)
    
    logger.info(f"Loaded {len(teams)} teams")
    
    # Calculate H2H and division records by fetching matchups
    logger.info(f"Calculating H2H records from weeks 1-{current_week}...")
    
    for week in range(1, current_week + 1):
        try:
            matchups = fetch_with_retry(
                f"{config.sleeper_api.base_url}/league/{league_id}/matchups/{week}",
                timeout=config.sleeper_api.timeout
            )
            
            if not matchups:
                continue
            
            # Group by matchup_id
            matchup_groups = defaultdict(list)
            for m in matchups:
                matchup_groups[m['matchup_id']].append(m)
            
            # Process each matchup
            for matchup_id, participants in matchup_groups.items():
                if len(participants) != 2:
                    continue  # Skip if not a 2-team matchup
                
                team1, team2 = participants
                roster1_id = team1['roster_id']
                roster2_id = team2['roster_id']
                
                points1 = team1.get('points', 0)
                points2 = team2.get('points', 0)
                
                # Find team objects
                team1_obj = next((t for t in teams if t.roster_id == roster1_id), None)
                team2_obj = next((t for t in teams if t.roster_id == roster2_id), None)
                
                if not team1_obj or not team2_obj:
                    continue
                
                # Record H2H result
                if points1 > points2:
                    team1_obj.h2h_wins[roster2_id] = team1_obj.h2h_wins.get(roster2_id, 0) + 1
                elif points2 > points1:
                    team2_obj.h2h_wins[roster1_id] = team2_obj.h2h_wins.get(roster1_id, 0) + 1
                
                # Record division games
                if team1_obj.division == team2_obj.division and team1_obj.division > 0:
                    if points1 > points2:
                        team1_obj.division_wins += 1
                        team2_obj.division_losses += 1
                    elif points2 > points1:
                        team2_obj.division_wins += 1
                        team1_obj.division_losses += 1
        
        except APIError as e:
            logger.warning(f"Could not fetch week {week} matchups: {e}")
            continue
    
    return teams


def compare_teams(team1: TeamRecord, team2: TeamRecord) -> int:
    """
    Compare two teams using tiebreaker rules.
    Returns: -1 if team1 better, 1 if team2 better, 0 if tied
    
    Tiebreakers:
    1. Win/Loss record
    2. Head-to-head record
    3. Division record
    4. Points for
    5. Points against (lower is better)
    """
    # 1. Win/Loss record
    if team1.wins != team2.wins:
        return -1 if team1.wins > team2.wins else 1
    
    # 2. Head-to-head record
    h2h_wins_1 = team1.h2h_wins.get(team2.roster_id, 0)
    h2h_wins_2 = team2.h2h_wins.get(team1.roster_id, 0)
    if h2h_wins_1 != h2h_wins_2:
        return -1 if h2h_wins_1 > h2h_wins_2 else 1
    
    # 3. Division record
    if team1.division_wins != team2.division_wins:
        return -1 if team1.division_wins > team2.division_wins else 1
    
    # 4. Points for
    if abs(team1.points_for - team2.points_for) > 0.01:
        return -1 if team1.points_for > team2.points_for else 1
    
    # 5. Points against (lower is better)
    if abs(team1.points_against - team2.points_against) > 0.01:
        return -1 if team1.points_against < team2.points_against else 1
    
    return 0


def generate_playoff_bracket(teams: List[TeamRecord]) -> Tuple[Dict, Dict]:
    """
    Generate playoff and consolation brackets based on league rules.
    
    Playoff Rules:
    - 6 teams make playoffs
    - Seeds 1-3: Division winners
    - Seeds 4-6: Best remaining records
    - Tiebreakers applied throughout
    
    Consolation Rules:
    - Remaining teams (7+)
    - Seeded purely by record (no division winners)
    - Same tiebreakers applied
    
    Returns:
        Tuple of (playoff_bracket, consolation_bracket)
    """
    logger.info("Generating playoff bracket...")
    
    # Group teams by division
    divisions = defaultdict(list)
    for team in teams:
        divisions[team.division].append(team)
    
    logger.info(f"Found {len(divisions)} divisions")
    
    # Get division winners (seeds 1-3)
    division_winners = []
    for div_id, div_teams in sorted(divisions.items()):
        if not div_teams:
            continue
        
        # Sort by tiebreakers
        div_teams_sorted = sorted(div_teams, key=lambda t: (
            -t.wins,
            -sum(t.h2h_wins.values()),
            -t.division_wins,
            -t.points_for,
            t.points_against
        ))
        
        winner = div_teams_sorted[0]
        division_winners.append(winner)
        logger.info(f"Division {div_id} winner: {winner.team_name} ({winner.wins}-{winner.losses})")
    
    # Sort division winners by tiebreakers for seeds 1-3
    from functools import cmp_to_key
    division_winners.sort(key=cmp_to_key(compare_teams))
    
    # Get remaining teams (non-division winners)
    division_winner_ids = {t.roster_id for t in division_winners}
    remaining_teams = [t for t in teams if t.roster_id not in division_winner_ids]
    
    # Sort remaining teams by tiebreakers
    remaining_teams.sort(key=cmp_to_key(compare_teams))
    
    # Take top 3 remaining teams for seeds 4-6
    wild_cards = remaining_teams[:3]
    
    # Combine for final playoff bracket
    playoff_teams = division_winners + wild_cards
    
    # Consolation bracket: remaining teams after top 6
    consolation_teams = remaining_teams[3:]  # Teams 7+
    
    # Create playoff bracket structure
    playoff_bracket = {
        'seeds': [],
        'matchups': {
            'wild_card': [],
            'semifinals': [],
            'championship': None
        }
    }
    
    # Assign playoff seeds
    for i, team in enumerate(playoff_teams, 1):
        seed_info = {
            'seed': i,
            'roster_id': team.roster_id,
            'team_name': team.team_name,
            'division': team.division,
            'record': f"{team.wins}-{team.losses}-{team.ties}" if team.ties > 0 else f"{team.wins}-{team.losses}",
            'points_for': round(team.points_for, 2),
            'points_against': round(team.points_against, 2),
            'type': 'Division Winner' if i <= 3 else 'Wild Card'
        }
        playoff_bracket['seeds'].append(seed_info)
    
    # Standard 6-team bracket: 1 & 2 get byes, 3v6 and 4v5 in wild card
    if len(playoff_teams) >= 6:
        playoff_bracket['matchups']['wild_card'] = [
            {'home': playoff_teams[2], 'away': playoff_teams[5]},  # 3 vs 6
            {'home': playoff_teams[3], 'away': playoff_teams[4]}   # 4 vs 5
        ]
        
        playoff_bracket['byes'] = [
            {'seed': 1, 'team': playoff_teams[0].team_name},
            {'seed': 2, 'team': playoff_teams[1].team_name}
        ]
    
    # Create consolation bracket structure
    consolation_bracket = {
        'seeds': [],
        'matchups': {
            'first_round': [],
            'semifinals': [],
            'championship': None
        }
    }
    
    # Assign consolation seeds (starting at 7)
    logger.info(f"Generating consolation bracket with {len(consolation_teams)} teams...")
    for i, team in enumerate(consolation_teams, 7):
        seed_info = {
            'seed': i,
            'roster_id': team.roster_id,
            'team_name': team.team_name,
            'division': team.division,
            'record': f"{team.wins}-{team.losses}-{team.ties}" if team.ties > 0 else f"{team.wins}-{team.losses}",
            'points_for': round(team.points_for, 2),
            'points_against': round(team.points_against, 2)
        }
        consolation_bracket['seeds'].append(seed_info)
    
    # Create consolation matchups based on number of teams
    if len(consolation_teams) >= 6:
        # 6-team consolation: 7&8 get byes, 9v12 and 10v11
        consolation_bracket['matchups']['first_round'] = [
            {'home': consolation_teams[2], 'away': consolation_teams[5]},  # 9 vs 12
            {'home': consolation_teams[3], 'away': consolation_teams[4]}   # 10 vs 11
        ]
        consolation_bracket['byes'] = [
            {'seed': 7, 'team': consolation_teams[0].team_name},
            {'seed': 8, 'team': consolation_teams[1].team_name}
        ]
    elif len(consolation_teams) == 4:
        # 4-team consolation: straight semifinals
        consolation_bracket['matchups']['first_round'] = [
            {'home': consolation_teams[0], 'away': consolation_teams[3]},  # 7 vs 10
            {'home': consolation_teams[1], 'away': consolation_teams[2]}   # 8 vs 9
        ]
    elif len(consolation_teams) == 2:
        # 2-team consolation: just a championship
        consolation_bracket['matchups']['first_round'] = [
            {'home': consolation_teams[0], 'away': consolation_teams[1]}   # 7 vs 8
        ]
    
    return playoff_bracket, consolation_bracket


def format_bracket_output(playoff_bracket: Dict, consolation_bracket: Dict, league_data: Dict) -> str:
    """Format both brackets as readable text"""
    output = []
    output.append("=" * 80)
    output.append(f"PLAYOFF & CONSOLATION BRACKETS - {league_data['league_name']} ({league_data['season']})")
    output.append(f"As of Week {league_data['current_week']}")
    output.append("=" * 80)
    output.append("")
    
    # PLAYOFF BRACKET
    output.append("PLAYOFF SEEDS:")
    output.append("-" * 80)
    for seed in playoff_bracket['seeds']:
        output.append(
            f"  {seed['seed']}. {seed['team_name']:<30} "
            f"{seed['record']:<10} "
            f"PF: {seed['points_for']:<8.2f} "
            f"PA: {seed['points_against']:<8.2f} "
            f"({seed['type']})"
        )
    
    output.append("")
    output.append("PLAYOFF BRACKET:")
    output.append("-" * 80)
    
    if 'byes' in playoff_bracket:
        output.append("FIRST ROUND BYES:")
        for bye in playoff_bracket['byes']:
            output.append(f"  Seed {bye['seed']}: {bye['team']}")
        output.append("")
    
    if playoff_bracket['matchups']['wild_card']:
        output.append("WILD CARD ROUND:")
        for i, matchup in enumerate(playoff_bracket['matchups']['wild_card'], 1):
            home = matchup['home']
            away = matchup['away']
            home_seed = next(s['seed'] for s in playoff_bracket['seeds'] if s['roster_id'] == home.roster_id)
            away_seed = next(s['seed'] for s in playoff_bracket['seeds'] if s['roster_id'] == away.roster_id)
            
            output.append(f"  Matchup {i}:")
            output.append(f"    ({home_seed}) {home.team_name} vs ({away_seed}) {away.team_name}")
        output.append("")
    
    output.append("=" * 80)
    output.append("")
    
    # CONSOLATION BRACKET
    if consolation_bracket['seeds']:
        output.append("CONSOLATION SEEDS:")
        output.append("-" * 80)
        for seed in consolation_bracket['seeds']:
            output.append(
                f"  {seed['seed']}. {seed['team_name']:<30} "
                f"{seed['record']:<10} "
                f"PF: {seed['points_for']:<8.2f} "
                f"PA: {seed['points_against']:<8.2f}"
            )
        
        output.append("")
        output.append("CONSOLATION BRACKET:")
        output.append("-" * 80)
        
        if 'byes' in consolation_bracket:
            output.append("FIRST ROUND BYES:")
            for bye in consolation_bracket['byes']:
                output.append(f"  Seed {bye['seed']}: {bye['team']}")
            output.append("")
        
        if consolation_bracket['matchups']['first_round']:
            output.append("FIRST ROUND:")
            for i, matchup in enumerate(consolation_bracket['matchups']['first_round'], 1):
                home = matchup['home']
                away = matchup['away']
                home_seed = next(s['seed'] for s in consolation_bracket['seeds'] if s['roster_id'] == home.roster_id)
                away_seed = next(s['seed'] for s in consolation_bracket['seeds'] if s['roster_id'] == away.roster_id)
                
                output.append(f"  Matchup {i}:")
                output.append(f"    ({home_seed}) {home.team_name} vs ({away_seed}) {away.team_name}")
            output.append("")
        
        output.append("=" * 80)
    else:
        output.append("NO CONSOLATION BRACKET (insufficient teams)")
        output.append("=" * 80)
    
    return "\n".join(output)


def main():
    """Main execution"""
    try:
        # Fetch league data
        league_data = fetch_league_data()
        
        # Calculate team records
        teams = calculate_team_records(league_data)
        
        # Generate brackets
        playoff_bracket, consolation_bracket = generate_playoff_bracket(teams)
        
        # Format and display
        output = format_bracket_output(playoff_bracket, consolation_bracket, league_data)
        print(output)
        
        # Save to JSON
        output_file = 'playoff_bracket.json'
        with open(output_file, 'w') as f:
            json.dump({
                'league_name': league_data['league_name'],
                'season': league_data['season'],
                'current_week': league_data['current_week'],
                'playoff_bracket': playoff_bracket,
                'consolation_bracket': consolation_bracket
            }, f, indent=2, default=str)
        
        logger.info(f"✓ Brackets saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate brackets: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
