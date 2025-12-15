#!/usr/bin/env python3
"""
Fetch weekly lineup data from Sleeper API.
Used to determine player usage for Waiver Hit Rate calculations.
"""

import json
import sys
import os
from pathlib import Path
import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.api_client import fetch_with_retry
from utils.logging_config import setup_logging

logger = setup_logging(__name__)

def load_config():
    """Load configuration from default.yaml."""
    config_path = Path(__file__).parent.parent / 'config' / 'default.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def fetch_weekly_lineups(league_id, start_week=1, end_week=15):
    """
    Fetch lineup data for all weeks to determine player usage.
    
    Args:
        league_id: Sleeper league ID
        start_week: First week to fetch (default: 1)
        end_week: Last week to fetch (default: 15)
    
    Returns:
        Dict: {roster_id: {week: {starters: [player_ids], points: float}}}
    """
    lineup_data = {}
    
    logger.info(f"Fetching lineup data for weeks {start_week}-{end_week}...")
    
    for week in range(start_week, end_week + 1):
        try:
            url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
            logger.info(f"Fetching week {week} matchups...")
            matchups = fetch_with_retry(url)
            
            if not matchups:
                logger.warning(f"No matchup data for week {week}")
                continue
            
            for matchup in matchups:
                roster_id = matchup.get('roster_id')
                if not roster_id:
                    continue
                
                starters = matchup.get('starters', [])
                points = matchup.get('points', 0.0)
                
                if roster_id not in lineup_data:
                    lineup_data[roster_id] = {}
                
                lineup_data[roster_id][week] = {
                    'starters': [str(p) for p in starters if p],  # Convert to strings, filter None
                    'points': float(points) if points else 0.0
                }
            
            logger.info(f"✓ Processed week {week} - {len(matchups)} rosters")
        
        except Exception as e:
            logger.error(f"Failed to fetch week {week} lineups: {e}")
            # Continue to next week even if one fails
    
    logger.info(f"Fetched lineup data for {len(lineup_data)} rosters across {end_week - start_week + 1} weeks")
    return lineup_data

def main():
    """Main execution function."""
    try:
        # Load configuration
        config = load_config()
        league_id = config['league']['id']
        
        logger.info(f"Starting lineup data fetch for league {league_id}")
        
        # Fetch lineup data for weeks 1-15
        lineup_data = fetch_weekly_lineups(league_id, start_week=1, end_week=15)
        
        if not lineup_data:
            logger.error("No lineup data fetched")
            return
        
        # Save to file
        output_file = Path(__file__).parent.parent / 'lineup_data_weekly.json'
        with open(output_file, 'w') as f:
            json.dump(lineup_data, f, indent=2)
        
        logger.info(f"✓ Saved lineup data to {output_file}")
        
        # Print summary statistics
        total_weeks = sum(len(weeks) for weeks in lineup_data.values())
        avg_weeks_per_roster = total_weeks / len(lineup_data) if lineup_data else 0
        
        logger.info(f"Summary:")
        logger.info(f"  - Total rosters: {len(lineup_data)}")
        logger.info(f"  - Total week entries: {total_weeks}")
        logger.info(f"  - Average weeks per roster: {avg_weeks_per_roster:.1f}")
        
    except Exception as e:
        logger.error(f"Failed to fetch lineup data: {e}")
        raise

if __name__ == "__main__":
    main()