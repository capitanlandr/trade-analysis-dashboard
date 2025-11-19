#!/usr/bin/env python3
"""
Fetch Standings Data from Sleeper API
Generates standings data including division rankings, records, and schedules
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import requests
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logging_config import setup_logging

# Constants
LEAGUE_ID = "1180814327660371968"
CURRENT_SEASON = 2025
REGULAR_SEASON_WEEKS = 14  # Weeks 1-14 are regular season

# Setup logging
logger = setup_logging("fetch_standings")


def load_config() -> Dict:
    """Load configuration from YAML"""
    config_path = Path(__file__).parent.parent / "config" / "default.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def fetch_league_info() -> Dict:
    """Fetch league information including divisions"""
    logger.info(f"Fetching league info for {LEAGUE_ID}")
    url = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}"
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    league_data = response.json()
    logger.info(f"✓ League: {league_data.get('name')}")
    return league_data


def fetch_rosters() -> List[Dict]:
    """Fetch all team rosters"""
    logger.info("Fetching rosters...")
    url = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters"
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    rosters = response.json()
    logger.info(f"✓ Loaded {len(rosters)} rosters")
    return rosters


def fetch_users() -> Dict[str, Dict]:
    """Fetch league users and create user_id to user mapping"""
    logger.info("Fetching users...")
    url = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users"
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    users = response.json()
    user_map = {user['user_id']: user for user in users}
    logger.info(f"✓ Loaded {len(users)} users")
    return user_map


def fetch_matchups_for_week(week: int) -> List[Dict]:
    """Fetch matchups for a specific week"""
    url = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{week}"
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    return response.json()


def calculate_median_score(matchups: List[Dict]) -> float:
    """Calculate median score for a week"""
    scores = [m['points'] for m in matchups if m.get('points') is not None]
    scores.sort()
    
    n = len(scores)
    if n == 0:
        return 0.0
    if n % 2 == 0:
        return (scores[n//2 - 1] + scores[n//2]) / 2
    return scores[n//2]


def get_opponent_roster_id(matchup: Dict, matchups: List[Dict]) -> Optional[int]:
    """Find opponent's roster_id from same matchup_id"""
    matchup_id = matchup.get('matchup_id')
    roster_id = matchup.get('roster_id')
    
    if not matchup_id:
        return None
    
    for m in matchups:
        if m.get('matchup_id') == matchup_id and m.get('roster_id') != roster_id:
            return m.get('roster_id')
    
    return None


def build_schedule_data(rosters: List[Dict], current_week: int) -> Dict[int, List[Dict]]:
    """Build complete schedule data for all teams"""
    logger.info(f"Building schedule data for weeks 1-{REGULAR_SEASON_WEEKS}")
    
    # Initialize schedule for each roster
    schedules = {roster['roster_id']: [] for roster in rosters}
    
    # Fetch matchups for each week
    for week in range(1, REGULAR_SEASON_WEEKS + 1):
        logger.info(f"  Processing week {week}...")
        
        try:
            matchups = fetch_matchups_for_week(week)
            median_score = calculate_median_score(matchups)
            
            # Create matchup lookup
            matchup_lookup = {m['roster_id']: m for m in matchups}
            
            for matchup in matchups:
                roster_id = matchup['roster_id']
                opponent_id = get_opponent_roster_id(matchup, matchups)
                
                points_for = matchup.get('points', 0)
                points_against = matchup_lookup.get(opponent_id, {}).get('points', 0) if opponent_id else 0
                
                # Determine result
                if week <= current_week:
                    if points_for > points_against:
                        result = 'W'
                    elif points_for < points_against:
                        result = 'L'
                    else:
                        result = 'T'
                else:
                    result = 'UPCOMING'
                
                schedules[roster_id].append({
                    'week': week,
                    'opponent_id': opponent_id,
                    'points_for': points_for,
                    'points_against': points_against,
                    'result': result,
                    'beat_median': points_for > median_score if week <= current_week else None,
                    'median_score': median_score
                })
        
        except Exception as e:
            logger.warning(f"  Failed to fetch week {week}: {e}")
            # Add placeholder for future weeks
            for roster_id in schedules:
                schedules[roster_id].append({
                    'week': week,
                    'opponent_id': None,
                    'points_for': 0,
                    'points_against': 0,
                    'result': 'UPCOMING',
                    'beat_median': None,
                    'median_score': 0
                })
    
    logger.info(f"✓ Schedule data built for {len(schedules)} teams")
    return schedules


def calculate_records(schedules: Dict[int, List[Dict]], rosters: List[Dict]) -> Dict[int, Dict]:
    """Calculate all record types for each team"""
    logger.info("Calculating records...")
    
    records = {}
    
    # Create division lookup
    division_lookup = {r['roster_id']: r.get('settings', {}).get('division', 0) for r in rosters}
    
    for roster_id, schedule in schedules.items():
        wins = losses = ties = 0
        median_wins = median_losses = 0
        division_wins = division_losses = division_ties = 0
        points_for = points_against = 0
        
        for game in schedule:
            if game['result'] == 'UPCOMING':
                continue
            
            # Overall record
            if game['result'] == 'W':
                wins += 1
            elif game['result'] == 'L':
                losses += 1
            else:
                ties += 1
            
            # Median record
            if game['beat_median'] is True:
                median_wins += 1
            elif game['beat_median'] is False:
                median_losses += 1
            
            # Division record
            opponent_id = game['opponent_id']
            if opponent_id and division_lookup.get(roster_id) == division_lookup.get(opponent_id):
                if game['result'] == 'W':
                    division_wins += 1
                elif game['result'] == 'L':
                    division_losses += 1
                else:
                    division_ties += 1
            
            # Points
            points_for += game['points_for']
            points_against += game['points_against']
        
        # Combined record = H2H wins + Median wins
        combined_wins = wins + median_wins
        combined_losses = losses + median_losses
        
        records[roster_id] = {
            'record': {'wins': combined_wins, 'losses': combined_losses, 'ties': ties},
            'matchup_record': {'wins': wins, 'losses': losses, 'ties': ties},
            'median_record': {'wins': median_wins, 'losses': median_losses},
            'division_record': {'wins': division_wins, 'losses': division_losses, 'ties': division_ties},
            'points_for': round(points_for, 2),
            'points_against': round(points_against, 2)
        }
    
    logger.info(f"✓ Records calculated for {len(records)} teams")
    return records


def load_team_identity_mapping() -> Dict[int, Dict]:
    """Load team identity mapping for display names"""
    mapping_path = Path(__file__).parent.parent / "team_identity_mapping.csv"
    
    if not mapping_path.exists():
        logger.warning("team_identity_mapping.csv not found, using Sleeper names")
        return {}
    
    import pandas as pd
    df = pd.read_csv(mapping_path)
    
    # Create roster_id to team info mapping
    mapping = {}
    for _, row in df.iterrows():
        mapping[row['roster_id']] = {
            'team_name': row['current_team_name'],
            'real_name': row['real_name']
        }
    
    logger.info(f"✓ Loaded team identity mapping for {len(mapping)} teams")
    return mapping


def organize_by_division(rosters: List[Dict], records: Dict, schedules: Dict, 
                        user_map: Dict, team_mapping: Dict, league_info: Dict) -> List[Dict]:
    """Organize teams by division and calculate rankings"""
    logger.info("Organizing teams by division...")
    
    # Get division names from league metadata
    metadata = league_info.get('metadata', {})
    division_names = {
        1: metadata.get('division_1', 'Division 1'),
        2: metadata.get('division_2', 'Division 2'),
        3: metadata.get('division_3', 'Division 3')
    }
    
    # Group rosters by division
    divisions = {}
    for roster in rosters:
        division_id = roster.get('settings', {}).get('division', 0)
        if division_id not in divisions:
            divisions[division_id] = []
        divisions[division_id].append(roster)
    
    # Build division data
    division_data = []
    for division_id in sorted(divisions.keys()):
        division_rosters = divisions[division_id]
        
        # Sort by wins, then points for
        division_rosters.sort(
            key=lambda r: (
                -records[r['roster_id']]['record']['wins'],
                -records[r['roster_id']]['points_for']
            )
        )
        
        teams = []
        for rank, roster in enumerate(division_rosters, 1):
            roster_id = roster['roster_id']
            owner_id = roster.get('owner_id')
            user = user_map.get(owner_id, {})
            
            # Get team names from mapping or fallback to Sleeper
            team_info = team_mapping.get(roster_id, {})
            team_name = team_info.get('team_name') or user.get('display_name', f'Team {roster_id}')
            owner_name = team_info.get('real_name') or user.get('display_name', 'Unknown')
            
            # Add opponent names to schedule
            schedule_with_names = []
            for game in schedules[roster_id]:
                opponent_id = game['opponent_id']
                opponent_info = team_mapping.get(opponent_id, {}) if opponent_id else {}
                opponent_name = opponent_info.get('team_name', f'Team {opponent_id}') if opponent_id else 'BYE'
                
                schedule_with_names.append({
                    **game,
                    'opponent_name': opponent_name
                })
            
            teams.append({
                'roster_id': roster_id,
                'team_name': team_name,
                'owner_name': owner_name,
                'rank': rank,
                **records[roster_id],
                'schedule': schedule_with_names
            })
        
        division_data.append({
            'division_id': division_id,
            'division_name': division_names.get(division_id, f'Division {division_id}'),
            'teams': teams
        })
    
    logger.info(f"✓ Organized {len(division_data)} divisions")
    return division_data


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("FETCHING STANDINGS DATA")
    logger.info("=" * 80)
    
    try:
        # Fetch data from Sleeper
        league_info = fetch_league_info()
        rosters = fetch_rosters()
        user_map = fetch_users()
        
        # Determine current week (simplified - could be enhanced)
        current_week = league_info.get('settings', {}).get('leg', 1)
        logger.info(f"Current week: {current_week}")
        
        # Build schedule and calculate records
        schedules = build_schedule_data(rosters, current_week)
        records = calculate_records(schedules, rosters)
        
        # Load team identity mapping
        team_mapping = load_team_identity_mapping()
        
        # Organize by division
        divisions = organize_by_division(rosters, records, schedules, user_map, team_mapping, league_info)
        
        # Build output
        output = {
            'divisions': divisions,
            'metadata': {
                'current_week': current_week,
                'total_weeks': REGULAR_SEASON_WEEKS,
                'last_updated': datetime.now().isoformat(),
                'season': CURRENT_SEASON
            }
        }
        
        # Write output
        output_path = Path(__file__).parent.parent / "standings_data.json"
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info("=" * 80)
        logger.info(f"✅ STANDINGS DATA GENERATED")
        logger.info(f"   Output: {output_path}")
        logger.info(f"   Divisions: {len(divisions)}")
        logger.info(f"   Teams: {sum(len(d['teams']) for d in divisions)}")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"❌ Failed to generate standings data: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
