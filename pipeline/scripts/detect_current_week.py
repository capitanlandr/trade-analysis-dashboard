"""
Week Detection Script with Roster Validation
Centralized week detection to avoid timing issues during Tuesday waivers.

This script determines the current completed week by:
1. Fetching Sleeper's 'leg' field (upcoming week)
2. Validating completion using roster records: (wins + losses + ties) / 2
3. Writing the validated week to config/current_week.json

The validation ensures we don't advance to a new week until all games
are completed and records are finalized, even if Sleeper has moved to
the next leg during Tuesday waivers.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import fetch_with_retry, APIError
from utils.logging_config import setup_logging
from config import get_config

# League configuration from centralized config
config = get_config()
LEAGUE_ID = config.league_id
SLEEPER_API_BASE = config.sleeper_api.base_url

# Setup logging
logger = setup_logging(__name__)


def fetch_league_info() -> Dict[str, Any]:
    """
    Fetch league information from Sleeper API.
    
    Returns:
        League info dict containing settings and leg
        
    Raises:
        APIError: If API call fails
    """
    url = f"{SLEEPER_API_BASE}/league/{LEAGUE_ID}"
    logger.info(f"Fetching league info from Sleeper API...")
    
    try:
        response = fetch_with_retry(url, timeout=10)
        if not response or 'settings' not in response:
            raise APIError("Invalid league response structure")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch league info: {e}")
        raise


def fetch_rosters() -> list:
    """
    Fetch all rosters from Sleeper API.
    
    Returns:
        List of roster dicts with settings and records
        
    Raises:
        APIError: If API call fails
    """
    url = f"{SLEEPER_API_BASE}/league/{LEAGUE_ID}/rosters"
    logger.info(f"Fetching rosters from Sleeper API...")
    
    try:
        response = fetch_with_retry(url, timeout=10)
        if not response or not isinstance(response, list):
            raise APIError("Invalid rosters response structure")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch rosters: {e}")
        raise


def validate_week_completion(rosters: list, sleeper_leg: int) -> int:
    """
    Validate week completion using roster records.
    
    For a dual-game-per-week league format, the formula is:
        weeks_completed = (wins + losses + ties) / 2
    
    If all teams have completed games matching Sleeper's leg, that week
    is finalized. Otherwise, we use the previous week.
    
    Args:
        rosters: List of roster dicts from Sleeper API
        sleeper_leg: Sleeper's 'leg' field (upcoming week)
        
    Returns:
        Validated current week number (1-14)
    """
    if not rosters:
        logger.warning("No rosters found, using Sleeper leg - 1")
        return max(1, sleeper_leg - 1)
    
    # Calculate weeks completed for each roster
    weeks_completed_list = []
    for roster in rosters:
        settings = roster.get('settings', {})
        wins = settings.get('wins', 0)
        losses = settings.get('losses', 0)
        ties = settings.get('ties', 0)
        
        # Dual-game-per-week format: divide total games by 2
        total_games = wins + losses + ties
        weeks_completed = total_games / 2
        weeks_completed_list.append(weeks_completed)
        
        logger.debug(
            f"Roster {roster.get('roster_id')}: "
            f"{wins}W-{losses}L-{ties}T = {total_games} games = {weeks_completed} weeks"
        )
    
    # Check if all teams have same weeks completed
    if len(set(weeks_completed_list)) == 1:
        validated_week = int(weeks_completed_list[0])
        logger.info(f"All teams completed {validated_week} weeks")
        
        # Compare with Sleeper's leg
        if validated_week == sleeper_leg:
            logger.info(
                f"Week {validated_week} MATCHES Sleeper leg {sleeper_leg} - "
                f"week is finalized"
            )
            return validated_week
        elif validated_week == sleeper_leg - 1:
            logger.info(
                f"Week {validated_week} is one behind Sleeper leg {sleeper_leg} - "
                f"games complete but waivers not processed"
            )
            return validated_week
        else:
            logger.warning(
                f"Unexpected mismatch: completed {validated_week} vs leg {sleeper_leg}"
            )
            # Use the completed week from records as source of truth
            return validated_week
    else:
        # Teams have different completion counts (shouldn't happen but handle it)
        min_weeks = int(min(weeks_completed_list))
        max_weeks = int(max(weeks_completed_list))
        logger.warning(
            f"Teams have inconsistent completion: {min_weeks} to {max_weeks} weeks"
        )
        # Use minimum as the safely completed week
        return min_weeks


def write_week_config(current_week: int) -> None:
    """
    Write current week to config file.
    
    Creates config directory if it doesn't exist and writes JSON config
    that other scripts will read.
    
    Args:
        current_week: Validated current week number
    """
    config_dir = Path(__file__).parent.parent / "config"
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "current_week.json"
    config_data = {
        "current_week": current_week,
        "last_updated": "Generated by detect_current_week.py"
    }
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        logger.info(f"✓ Week config written to {config_file}")
        logger.info(f"✓ Current week: {current_week}")
    except Exception as e:
        logger.error(f"Failed to write config file: {e}")
        raise


def detect_current_week() -> int:
    """
    Main detection logic.
    
    Orchestrates the week detection process:
    1. Fetch league info and rosters
    2. Extract Sleeper's leg
    3. Validate using roster records
    4. Write to config file
    
    Returns:
        Validated current week number
        
    Raises:
        APIError: If API calls fail
        Exception: If validation or file writing fails
    """
    logger.info("=" * 60)
    logger.info("Starting Week Detection")
    logger.info("=" * 60)
    
    # Fetch data from Sleeper
    league_info = fetch_league_info()
    rosters = fetch_rosters()
    
    # Get Sleeper's leg (upcoming week)
    sleeper_leg = league_info.get('settings', {}).get('leg', 1)
    logger.info(f"Sleeper leg (upcoming week): {sleeper_leg}")
    
    # Validate using roster records
    current_week = validate_week_completion(rosters, sleeper_leg)
    
    # Write to config
    write_week_config(current_week)
    
    logger.info("=" * 60)
    logger.info(f"Week Detection Complete: Week {current_week}")
    logger.info("=" * 60)
    
    return current_week


if __name__ == "__main__":
    try:
        week = detect_current_week()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Week detection failed: {e}")
        sys.exit(1)