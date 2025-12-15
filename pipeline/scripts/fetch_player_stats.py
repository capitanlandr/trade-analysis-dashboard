#!/usr/bin/env python3
"""
Fetch weekly player stats from Sleeper API.
Used for calculating Waiver Wire Efficiency Score (WWES).
"""

import json
import sys
import os
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.api_client import fetch_with_retry
from utils.logging_config import setup_logging

logger = setup_logging("Fetch Player Stats")


def fetch_player_stats(season='2025', season_type='regular', max_week=14):
    """
    Fetch weekly player stats from Sleeper API.
    
    Note: Sleeper's /stats endpoint returns season totals, not weekly breakdowns.
    We need to fetch each week individually using the /stats/nfl/{season_type}/{season}/{week} endpoint.
    
    Args:
        season: Season year (default: '2025')
        season_type: Season type - 'regular' or 'post' (default: 'regular')
        max_week: Maximum week to fetch (default: 14)
    
    Returns:
        Dict mapping player_id -> {week -> stats}
    """
    logger.info(f"Fetching player stats for {season} {season_type} season (weeks 1-{max_week})...")
    
    player_weekly_stats = {}
    
    try:
        # Fetch stats for each week individually
        for week in range(1, max_week + 1):
            try:
                url = f"https://api.sleeper.app/v1/stats/nfl/{season_type}/{season}/{week}"
                logger.info(f"Fetching week {week} stats...")
                week_stats = fetch_with_retry(url)
                
                if not week_stats:
                    logger.warning(f"No stats data for week {week}")
                    continue
                
                # Process each player's stats for this week
                for player_id, stats in week_stats.items():
                    if player_id not in player_weekly_stats:
                        player_weekly_stats[player_id] = {}
                    
                    # Extract fantasy points (PPR scoring)
                    # Handle both dict and numeric stats formats
                    if isinstance(stats, dict):
                        fantasy_points = stats.get('pts_ppr', 0)
                        full_stats = stats
                    else:
                        # Stats is just a number (fantasy points)
                        fantasy_points = float(stats) if stats else 0
                        full_stats = {'pts_ppr': fantasy_points}
                    
                    player_weekly_stats[player_id][week] = {
                        'fantasy_points': fantasy_points,
                        'stats': full_stats
                    }
                
                logger.info(f"  ✓ Week {week}: {len(week_stats)} players")
                
            except Exception as e:
                logger.warning(f"Failed to fetch week {week} stats: {e}")
                continue
        
        logger.info(f"Successfully fetched stats for {len(player_weekly_stats)} players across weeks")
        
        # Save to file in pipeline directory
        output_file = Path(__file__).parent.parent / 'player_stats_weekly.json'
        with open(output_file, 'w') as f:
            json.dump(player_weekly_stats, f, indent=2)
        
        logger.info(f"Saved player stats to {output_file}")
        return player_weekly_stats
        
    except Exception as e:
        logger.error(f"Failed to fetch player stats: {e}", exc_info=True)
        # Don't raise - allow pipeline to continue without efficiency metrics
        return {}


if __name__ == "__main__":
    try:
        player_stats = fetch_player_stats()
        if player_stats:
            print(f"\n✅ Successfully fetched stats for {len(player_stats)} players")
        else:
            print("\n⚠️  No player stats retrieved - efficiency metrics will be skipped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error fetching player stats: {e}")
        sys.exit(1)