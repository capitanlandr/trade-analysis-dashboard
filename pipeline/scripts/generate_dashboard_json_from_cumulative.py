#!/usr/bin/env python3
"""
Generate Dashboard JSON from Cumulative Files

This script replaces generate_dashboard_json.py to use cumulative multi-season files
as the source instead of CSV files. This implements Task 11 - Dashboard Data Synchronization
for the multi-season architecture.

MULTI-SEASON ARCHITECTURE:
==========================
This script reads from cumulative files (trades.json, cumulative_processed_waiver_transactions.json) that contain
ALL seasons' data with season tags, then generates dashboard JSON files that support
client-side season filtering.

Key Changes from Original:
- Reads from cumulative JSON files instead of CSV files
- Preserves season metadata in dashboard JSON
- Supports multi-season data structure
- Maintains backward compatibility with existing frontend
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import os

# Add pipeline utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get script directory and set up paths
SCRIPT_DIR = Path(__file__).parent
PIPELINE_DIR = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_DIR.parent

# Input paths - cumulative files (source of truth)
CUMULATIVE_TRADES = PIPELINE_DIR / 'trades.json'
CUMULATIVE_WAIVER_WIRE = PIPELINE_DIR / 'cumulative_processed_waiver_transactions.json'
TEAMS_CSV = PIPELINE_DIR / 'team_identity_mapping.csv'  # Still needed for team info
STANDINGS_JSON = PIPELINE_DIR / 'standings_data.json'
TRADES_ANALYSIS_CSV = PIPELINE_DIR / 'league_trades_analysis_pipeline.csv'  # For correct value_change calculations

# Output paths - dashboard JSON files
DASHBOARD_DIR = REPO_ROOT / 'dashboard/frontend/public'
OUTPUT_TRADES = DASHBOARD_DIR / 'api-trades.json'
OUTPUT_TEAMS = DASHBOARD_DIR / 'api-teams.json'
OUTPUT_STATS = DASHBOARD_DIR / 'api-stats-summary.json'


def load_cumulative_trades() -> Dict[str, Any]:
    """
    Load trade data from cumulative trades.json file.
    
    Returns:
        Dict containing trades and metadata from cumulative file
        
    Raises:
        FileNotFoundError: If cumulative trades file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    logger.info(f"Loading cumulative trades from {CUMULATIVE_TRADES}")
    
    if not CUMULATIVE_TRADES.exists():
        raise FileNotFoundError(f"Cumulative trades file not found: {CUMULATIVE_TRADES}")
    
    try:
        with open(CUMULATIVE_TRADES, 'r') as f:
            cumulative_data = json.load(f)
        
        trades = cumulative_data.get('trades', [])
        metadata = cumulative_data.get('metadata', {})
        
        logger.info(f"✓ Loaded {len(trades)} trades from cumulative file")
        logger.info(f"✓ Seasons included: {metadata.get('seasons_included', [])}")
        logger.info(f"✓ Total trades by season: {metadata.get('trades_by_season', {})}")
        
        return cumulative_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in cumulative trades file: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load cumulative trades: {e}")
        raise


def load_teams_data() -> List[Dict[str, Any]]:
    """
    Load team data from CSV file.
    
    Note: Team data is still loaded from CSV as it doesn't change frequently
    and doesn't need multi-season support.
    
    Returns:
        List of team dictionaries
    """
    import pandas as pd
    
    logger.info(f"Loading teams from {TEAMS_CSV}")
    
    if not TEAMS_CSV.exists():
        logger.warning(f"Teams CSV not found: {TEAMS_CSV}")
        return []
    
    try:
        df = pd.read_csv(TEAMS_CSV)
        logger.info(f"✓ Loaded {len(df)} teams")
        
        teams = []
        for _, row in df.iterrows():
            # Helper function to safely convert values
            def safe_int(value):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return 0
            
            def safe_str(value):
                return str(value) if pd.notna(value) else ""
            
            team = {
                "rosterId": safe_int(row['roster_id']),
                "teamName": safe_str(row['current_team_name']),
                "realName": safe_str(row['real_name']),
                "sleeperUsername": safe_str(row['sleeper_username']),
                "nickname": safe_str(row.get('nickname', '')),
                "tradeCount": 0,  # Will be calculated from cumulative data
                "winRate": 0,     # Will be calculated from cumulative data
                "avgMargin": 0,   # Will be calculated from cumulative data
                "totalValueGained": 0  # Will be calculated from cumulative data
            }
            teams.append(team)
        
        return teams
        
    except Exception as e:
        logger.error(f"Failed to load teams data: {e}")
        return []


def load_asset_values() -> Dict[str, int]:
    """Load player values from asset_values_cache.csv."""
    asset_values_csv = PIPELINE_DIR / 'asset_values_cache.csv'
    
    try:
        if not asset_values_csv.exists():
            logger.warning("asset_values_cache.csv not found - using default values")
            return {}
        
        import pandas as pd
        df = pd.read_csv(asset_values_csv)
        
        # Create mapping from asset name to current value
        asset_values = {}
        for _, row in df.iterrows():
            asset_name = row['asset_name']
            value_current = row['value_current']
            value_at_trade = row.get('value_at_trade', value_current)
            metadata_str = str(row.get('metadata', ''))
            
            if pd.notna(asset_name):
                asset_data = {
                    'current': int(value_current) if pd.notna(value_current) else 0,
                    'at_trade': int(value_at_trade) if pd.notna(value_at_trade) else 0
                }
                
                # Parse metadata for pick position info
                if metadata_str and metadata_str != 'nan':
                    try:
                        import ast
                        metadata = ast.literal_eval(metadata_str)
                        if isinstance(metadata, dict) and 'pick_label' in metadata:
                            asset_data['pick_label'] = metadata['pick_label']
                    except:
                        pass
                
                asset_values[asset_name] = asset_data
        
        logger.info(f"✓ Loaded values for {len(asset_values)} assets")
        return asset_values
        
    except Exception as e:
        logger.warning(f"Failed to load asset values: {e}")
        return {}


def fetch_player_data() -> Dict[str, Dict[str, Any]]:
    """Fetch player data from Sleeper API for name resolution."""
    try:
        logger.info("Fetching player data from Sleeper API...")
        
        # Import here to avoid circular imports
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from utils.api_client import fetch_with_retry
        
        players_url = "https://api.sleeper.app/v1/players/nfl"
        players = fetch_with_retry(players_url, timeout=30)
        
        if players:
            logger.info(f"✓ Loaded {len(players)} players from Sleeper API")
            return players
        else:
            logger.warning("No player data received from API")
            return {}
    except Exception as e:
        logger.warning(f"Failed to fetch player data from API: {e}")
        return {}


def load_team_mappings() -> Dict[int, str]:
    """Load team mappings from team_identity_mapping.csv."""
    try:
        if not TEAMS_CSV.exists():
            logger.warning("team_identity_mapping.csv not found")
            return {}
        
        import pandas as pd
        df = pd.read_csv(TEAMS_CSV)
        
        # Create mapping from roster_id to sleeper_username
        team_mappings = {}
        for _, row in df.iterrows():
            roster_id = row.get('roster_id')
            username = row.get('sleeper_username', '')
            
            if pd.notna(roster_id) and pd.notna(username):
                team_mappings[int(roster_id)] = str(username)
        
        logger.info(f"✓ Loaded mappings for {len(team_mappings)} teams")
        return team_mappings
        
    except Exception as e:
        logger.warning(f"Failed to load team mappings: {e}")
        return {}


def load_trade_value_changes() -> Dict[str, Dict[str, float]]:
    """
    Load pre-calculated value changes from league_trades_analysis_pipeline.csv.
    
    This CSV contains the correct value_change calculations from Stage 4 that properly
    handle draft pick valuations and other edge cases.
    
    Returns:
        Dict mapping transaction_id to value change data
    """
    try:
        if not TRADES_ANALYSIS_CSV.exists():
            logger.warning(f"Trades analysis CSV not found: {TRADES_ANALYSIS_CSV}")
            return {}
        
        import pandas as pd
        df = pd.read_csv(TRADES_ANALYSIS_CSV)
        
        # Create lookup by transaction_id
        value_changes = {}
        for _, row in df.iterrows():
            transaction_id = str(row.get('transaction_id', ''))
            if transaction_id:
                value_changes[transaction_id] = {
                    'team_a': row.get('team_a', ''),
                    'team_b': row.get('team_b', ''),
                    'team_a_value_change': float(row.get('team_a_value_change', 0)),
                    'team_b_value_change': float(row.get('team_b_value_change', 0)),
                    'team_a_value_then': float(row.get('team_a_value_then', 0)),
                    'team_a_value_now': float(row.get('team_a_value_now', 0)),
                    'team_b_value_then': float(row.get('team_b_value_then', 0)),
                    'team_b_value_now': float(row.get('team_b_value_now', 0)),
                    'margin_at_trade': float(row.get('margin_at_trade', 0)),
                    'margin_current': float(row.get('margin_current', 0)),
                    'winner_at_trade': str(row.get('winner_at_trade', '')),
                    'winner_current': str(row.get('winner_current', '')),
                    'swing_winner': str(row.get('swing_winner', '')),
                    'swing_margin': float(row.get('swing_margin', 0))
                }
        
        logger.info(f"✓ Loaded value changes for {len(value_changes)} trades from CSV")
        return value_changes
        
    except Exception as e:
        logger.warning(f"Failed to load trade value changes: {e}")
        return {}


def process_raw_trade_to_dashboard_format(raw_trade: Dict[str, Any], players: Dict, asset_values: Dict, team_mappings: Dict, csv_value_changes: Dict) -> Dict[str, Any]:
    """
    Process a raw Sleeper API trade into dashboard format.
    
    This function uses pre-calculated value changes from the CSV (Stage 4 output)
    to ensure correct handling of draft picks and other edge cases.
    
    Args:
        raw_trade: Raw trade record from cumulative file (Sleeper API format)
        players: Player data from Sleeper API
        asset_values: Asset values from cache
        team_mappings: Roster ID to username mappings
        csv_value_changes: Pre-calculated value changes from CSV
        
    Returns:
        Trade record in dashboard format
    """
    from datetime import datetime
    
    # Helper functions
    def safe_float(value):
        try:
            return float(value) if value is not None else 0
        except (ValueError, TypeError):
            return 0
    
    def get_player_name(player_id):
        if not player_id:
            return 'Unknown Player'
        
        player_info = players.get(str(player_id), {})
        if isinstance(player_info, dict):
            first_name = player_info.get('first_name', '')
            last_name = player_info.get('last_name', '')
            if first_name and last_name:
                return f"{first_name} {last_name}"
            elif first_name or last_name:
                return first_name or last_name
        
        return f"Player {player_id}"
    
    def get_asset_value(asset_name, value_type='current'):
        if not asset_name or asset_name == 'Unknown Player':
            return 0
        
        asset_data = asset_values.get(asset_name, {})
        return asset_data.get(value_type, 0)
    
    def get_asset_pick_label(asset_name):
        """Get pick position label if available."""
        if not asset_name:
            return None
        asset_data = asset_values.get(asset_name, {})
        return asset_data.get('pick_label')
    
    def format_draft_pick(pick):
        season = pick.get('season', 'Unknown')
        round_num = pick.get('round', 'Unknown')
        return f"{season} Round {round_num}"
    
    # Extract basic trade info
    transaction_id = str(raw_trade.get('transaction_id', ''))
    created_timestamp = raw_trade.get('created', 0)
    trade_date = datetime.fromtimestamp(created_timestamp / 1000).strftime('%Y-%m-%d') if created_timestamp else ''
    season = raw_trade.get('season', '')
    roster_ids = raw_trade.get('roster_ids', [])
    
    # CHECK CSV FOR PRE-CALCULATED VALUES (correct draft pick handling)
    csv_data = csv_value_changes.get(transaction_id)
    if csv_data:
        # Use pre-calculated values from CSV (Stage 4 output with correct logic)
        use_csv_values = True
    else:
        # Fallback to calculating from assets (may be less accurate for draft picks)
        use_csv_values = False
    
    # Only process 2-team trades for now (multi-team trades need special handling)
    if len(roster_ids) != 2:
        logger.debug(f"Skipping multi-team trade {transaction_id} with {len(roster_ids)} teams")
        return None
    
    roster_a, roster_b = roster_ids[0], roster_ids[1]
    team_a = team_mappings.get(roster_a, f"Team {roster_a}")
    team_b = team_mappings.get(roster_b, f"Team {roster_b}")
    
    # Process player adds/drops
    adds = raw_trade.get('adds', {}) or {}
    drops = raw_trade.get('drops', {}) or {}
    
    # Determine what each team received
    team_a_assets = []
    team_a_value_then = 0
    team_a_value_now = 0
    
    team_b_assets = []
    team_b_value_then = 0
    team_b_value_now = 0
    
    # Process player adds (what each team received)
    for player_id, to_roster in adds.items():
        player_name = get_player_name(player_id)
        value_then = get_asset_value(player_name, 'at_trade')
        value_now = get_asset_value(player_name, 'current')
        
        asset_info = {
            'name': player_name,
            'type': 'player',
            'value_then': value_then,
            'value_now': value_now
        }
        
        if to_roster == roster_a:
            team_a_assets.append(asset_info)
            team_a_value_then += value_then
            team_a_value_now += value_now
        elif to_roster == roster_b:
            team_b_assets.append(asset_info)
            team_b_value_then += value_then
            team_b_value_now += value_now
    
    # Process draft picks
    draft_picks = raw_trade.get('draft_picks', [])
    for pick in draft_picks:
        pick_name = format_draft_pick(pick)
        value_then = get_asset_value(pick_name, 'at_trade')
        value_now = get_asset_value(pick_name, 'current')
        pick_label = get_asset_pick_label(pick_name)
        
        asset_info = {
            'name': pick_name,
            'type': 'draft_pick',
            'value_then': value_then,
            'value_now': value_now
        }
        
        # Add pick position if available (for 2026 picks with finalized draft order)
        if pick_label:
            asset_info['pick_label'] = pick_label
        
        owner_id = pick.get('owner_id')
        if owner_id == roster_a:
            team_a_assets.append(asset_info)
            team_a_value_then += value_then
            team_a_value_now += value_now
        elif owner_id == roster_b:
            team_b_assets.append(asset_info)
            team_b_value_then += value_then
            team_b_value_now += value_now
    
    # Process FAAB transfers
    waiver_budget = raw_trade.get('waiver_budget', [])
    for faab_transfer in waiver_budget:
        amount = faab_transfer.get('amount', 0)
        receiver = faab_transfer.get('receiver')
        
        faab_name = f"${amount} FAAB"
        # FAAB typically has minimal fantasy value, use amount as rough value
        value_then = amount
        value_now = amount
        
        asset_info = {
            'name': faab_name,
            'type': 'faab',
            'value_then': value_then,
            'value_now': value_now
        }
        
        if receiver == roster_a:
            team_a_assets.append(asset_info)
            team_a_value_then += value_then
            team_a_value_now += value_now
        elif receiver == roster_b:
            team_b_assets.append(asset_info)
            team_b_value_then += value_then
            team_b_value_now += value_now
    
    # Calculate trade outcomes
    winner_at_trade = team_a if team_a_value_then > team_b_value_then else team_b
    winner_current = team_a if team_a_value_now > team_b_value_now else team_b
    
    margin_at_trade = abs(team_a_value_then - team_b_value_then)
    margin_current = abs(team_a_value_now - team_b_value_now)
    
    # Calculate swing
    if team_a_value_then > team_b_value_then:
        margin_swing = (team_a_value_now - team_b_value_now) - (team_a_value_then - team_b_value_then)
    else:
        margin_swing = (team_b_value_now - team_a_value_now) - (team_b_value_then - team_a_value_then)
    
    swing_winner = winner_current if margin_swing != 0 else 'Tie'
    swing_margin = abs(margin_swing)
    
    # Create dashboard format
    # Use CSV values if available (correct draft pick handling), otherwise use calculated values
    if use_csv_values and csv_data:
        # Check if team names match (could be in either order)
        teams_match_forward = (csv_data['team_a'] == team_a and csv_data['team_b'] == team_b)
        teams_match_reversed = (csv_data['team_a'] == team_b and csv_data['team_b'] == team_a)
        
        if teams_match_forward:
            # Teams match in same order
            pass
        elif teams_match_reversed:
            # Teams are reversed - swap the CSV values
            csv_data = {
                'team_a': csv_data['team_b'],
                'team_b': csv_data['team_a'],
                'team_a_value_then': csv_data['team_b_value_then'],
                'team_a_value_now': csv_data['team_b_value_now'],
                'team_a_value_change': csv_data['team_b_value_change'],
                'team_b_value_then': csv_data['team_a_value_then'],
                'team_b_value_now': csv_data['team_a_value_now'],
                'team_b_value_change': csv_data['team_a_value_change'],
                'winner_at_trade': csv_data['winner_at_trade'],
                'winner_current': csv_data['winner_current'],
                'margin_at_trade': -csv_data['margin_at_trade'],  # Reverse margin
                'margin_current': -csv_data['margin_current'],  # Reverse margin
                'swing_winner': csv_data['swing_winner'],
                'swing_margin': csv_data['swing_margin']
            }
        else:
            # Team names don't match - use calculated values
            logger.warning(f"Team name mismatch for trade {transaction_id}: "
                         f"CSV has ({csv_data['team_a']}, {csv_data['team_b']}), "
                         f"but trade has ({team_a}, {team_b})")
            use_csv_values = False
    
    if use_csv_values and csv_data:
        dashboard_trade = {
            "tradeId": transaction_id,
            "transactionId": transaction_id,
            "tradeDate": trade_date,
            "season": season,
            "teamA": team_a,
            "teamAReceived": [asset['name'] for asset in team_a_assets],
            "teamAAssets": team_a_assets,
            "teamAValueThen": csv_data['team_a_value_then'],
            "teamAValueNow": csv_data['team_a_value_now'],
            "teamAValueChange": csv_data['team_a_value_change'],
            "teamB": team_b,
            "teamBReceived": [asset['name'] for asset in team_b_assets],
            "teamBAssets": team_b_assets,
            "teamBValueThen": csv_data['team_b_value_then'],
            "teamBValueNow": csv_data['team_b_value_now'],
            "teamBValueChange": csv_data['team_b_value_change'],
            "winnerAtTrade": csv_data['winner_at_trade'],
            "winnerCurrent": csv_data['winner_current'],
            "marginAtTrade": csv_data['margin_at_trade'],
            "marginCurrent": csv_data['margin_current'],
            "swingWinner": csv_data['swing_winner'],
            "swingMargin": csv_data['swing_margin']
        }
    else:
        # Fallback: calculate from assets (less accurate for draft picks)
        dashboard_trade = {
            "tradeId": transaction_id,
            "transactionId": transaction_id,
            "tradeDate": trade_date,
            "season": season,
            "teamA": team_a,
            "teamAReceived": [asset['name'] for asset in team_a_assets],
            "teamAAssets": team_a_assets,
            "teamAValueThen": team_a_value_then,
            "teamAValueNow": team_a_value_now,
            "teamAValueChange": team_a_value_now - team_a_value_then,
            "teamB": team_b,
            "teamBReceived": [asset['name'] for asset in team_b_assets],
            "teamBAssets": team_b_assets,
            "teamBValueThen": team_b_value_then,
            "teamBValueNow": team_b_value_now,
            "teamBValueChange": team_b_value_now - team_b_value_then,
            "winnerAtTrade": winner_at_trade,
            "winnerCurrent": winner_current,
            "marginAtTrade": margin_at_trade,
            "marginCurrent": margin_current,
            "swingWinner": swing_winner,
            "swingMargin": swing_margin
        }
    
    return dashboard_trade


def calculate_team_stats_from_processed_trades(teams: List[Dict], processed_trades: List[Dict]) -> List[Dict]:
    """
    Calculate team statistics from processed trade data.
    
    Args:
        teams: List of team dictionaries
        processed_trades: List of processed trades in dashboard format
        
    Returns:
        List of teams with calculated statistics
    """
    logger.info("Calculating team statistics from processed trades...")
    
    # Create lookup by sleeper username (which matches trades)
    team_stats = {}
    username_to_team = {}
    
    for team in teams:
        username = team['sleeperUsername']
        team_stats[username] = {
            'tradeCount': 0,
            'wins': 0,
            'totalMargin': 0,
            'totalValueGained': 0
        }
        username_to_team[username] = team
    
    # Calculate stats from processed trades
    for trade in processed_trades:
        if not trade:  # Skip None trades (multi-team trades)
            continue
            
        team_a = trade.get('teamA', '')
        team_b = trade.get('teamB', '')
        
        if team_a in team_stats:
            stats = team_stats[team_a]
            stats['tradeCount'] += 1
            stats['totalMargin'] += abs(trade.get('marginCurrent', 0))
            stats['totalValueGained'] += trade.get('teamAValueChange', 0)
            if trade.get('winnerCurrent') == team_a:
                stats['wins'] += 1
        
        if team_b in team_stats:
            stats = team_stats[team_b]
            stats['tradeCount'] += 1
            stats['totalMargin'] += abs(trade.get('marginCurrent', 0))
            stats['totalValueGained'] += trade.get('teamBValueChange', 0)
            if trade.get('winnerCurrent') == team_b:
                stats['wins'] += 1
    
    # Apply stats to teams
    for team in teams:
        username = team['sleeperUsername']
        if username in team_stats:
            stats = team_stats[username]
            team['tradeCount'] = stats['tradeCount']
            team['winRate'] = (stats['wins'] / stats['tradeCount'] * 100) if stats['tradeCount'] > 0 else 0
            team['avgMargin'] = (stats['totalMargin'] / stats['tradeCount']) if stats['tradeCount'] > 0 else 0
            team['totalValueGained'] = stats['totalValueGained']
    
    return teams


def calculate_league_stats_from_processed_trades(processed_trades: List[Dict], teams: List[Dict]) -> Dict[str, Any]:
    """
    Calculate league-wide statistics from processed trade data.
    
    Args:
        processed_trades: List of processed trades in dashboard format
        teams: List of teams with calculated stats
        
    Returns:
        Dictionary of league statistics
    """
    logger.info("Calculating league statistics from processed trades...")
    
    # Filter out None trades (multi-team trades)
    valid_trades = [t for t in processed_trades if t is not None]
    
    if not valid_trades:
        return {
            "totalTrades": 0,
            "totalTradeValue": 0,
            "avgTradeMargin": 0,
            "mostActiveTrader": "",
            "biggestWinner": "",
            "blockbusterCount": 0,
            "dateRange": {"earliest": "", "latest": ""}
        }
    
    total_trade_value = sum(
        (trade.get('teamAValueNow', 0) + trade.get('teamBValueNow', 0)) 
        for trade in valid_trades
    )
    avg_trade_margin = sum(abs(trade.get('marginCurrent', 0)) for trade in valid_trades) / len(valid_trades)
    
    # Find most active trader
    most_active = max(teams, key=lambda t: t['tradeCount']) if teams else None
    
    # Find biggest winner
    biggest_winner = max(teams, key=lambda t: t['totalValueGained']) if teams else None
    
    # Count blockbuster trades (>5000 total value)
    blockbuster_count = sum(
        1 for trade in valid_trades 
        if (trade.get('teamAValueNow', 0) + trade.get('teamBValueNow', 0)) > 5000
    )
    
    # Date range
    trade_dates = [trade.get('tradeDate', '') for trade in valid_trades if trade.get('tradeDate')]
    trade_dates.sort()
    
    return {
        "totalTrades": len(valid_trades),
        "totalTradeValue": total_trade_value,
        "avgTradeMargin": avg_trade_margin,
        "mostActiveTrader": most_active['realName'] if most_active else "",
        "biggestWinner": biggest_winner['realName'] if biggest_winner else "",
        "blockbusterCount": blockbuster_count,
        "dateRange": {
            "earliest": trade_dates[0] if trade_dates else "",
            "latest": trade_dates[-1] if trade_dates else ""
        }
    }


def generate_dashboard_json_from_cumulative():
    """
    Generate dashboard JSON files from cumulative multi-season data.
    
    This is the main function that implements Task 11 - Dashboard Data Synchronization.
    It reads from cumulative files and generates dashboard JSON with multi-season support.
    """
    logger.info("="*80)
    logger.info("GENERATING DASHBOARD JSON FROM CUMULATIVE FILES")
    logger.info("="*80)
    
    # Ensure output directory exists
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load cumulative trade data (raw Sleeper API format)
        cumulative_data = load_cumulative_trades()
        raw_trades = cumulative_data.get('trades', [])
        cumulative_metadata = cumulative_data.get('metadata', {})
        
        logger.info(f"Processing {len(raw_trades)} raw trades from cumulative file...")
        
        # Load supporting data needed for processing
        players = fetch_player_data()
        asset_values = load_asset_values()
        team_mappings = load_team_mappings()
        teams = load_teams_data()
        csv_value_changes = load_trade_value_changes()  # Load pre-calculated values from CSV
        
        # Process raw trades into dashboard format
        dashboard_trades = []
        processed_count = 0
        skipped_count = 0
        csv_used_count = 0
        calculated_count = 0
        
        for raw_trade in raw_trades:
            processed_trade = process_raw_trade_to_dashboard_format(
                raw_trade, players, asset_values, team_mappings, csv_value_changes
            )
            
            if processed_trade:
                dashboard_trades.append(processed_trade)
                processed_count += 1
                
                # Track if CSV values were used
                transaction_id = str(raw_trade.get('transaction_id', ''))
                if transaction_id in csv_value_changes:
                    csv_used_count += 1
                else:
                    calculated_count += 1
            else:
                skipped_count += 1
        
        logger.info(f"✓ Processed {processed_count} trades to dashboard format")
        logger.info(f"✓ Used CSV values for {csv_used_count} trades")
        logger.info(f"✓ Calculated values for {calculated_count} trades")
        if skipped_count > 0:
            logger.info(f"✓ Skipped {skipped_count} multi-team trades (not yet supported)")
        
        # Calculate team stats from processed trades
        teams_with_stats = calculate_team_stats_from_processed_trades(teams, dashboard_trades)
        
        # Calculate league stats from processed trades
        league_stats = calculate_league_stats_from_processed_trades(dashboard_trades, teams_with_stats)
        
        # Generate trades JSON with multi-season metadata
        trades_response = {
            "success": True,
            "data": {
                "trades": dashboard_trades,
                "metadata": {
                    "lastUpdated": datetime.now().isoformat(),
                    "totalTrades": len(dashboard_trades),
                    "dateRange": league_stats["dateRange"],
                    # Multi-season metadata from cumulative file
                    "seasonsIncluded": cumulative_metadata.get('seasons_included', []),
                    "tradesBySeason": cumulative_metadata.get('trades_by_season', {}),
                    "seasonInfo": cumulative_metadata.get('season_info', {}),
                    "schemaVersion": cumulative_metadata.get('schema_version', '2.0.0'),
                    "source": "cumulative_files",  # Indicate this came from cumulative data
                    "processingInfo": {
                        "rawTradesProcessed": len(raw_trades),
                        "dashboardTradesGenerated": len(dashboard_trades),
                        "multiTeamTradesSkipped": skipped_count
                    }
                }
            }
        }
        
        with open(OUTPUT_TRADES, 'w') as f:
            json.dump(trades_response, f, indent=2)
        logger.info(f"✓ Generated {OUTPUT_TRADES} ({len(dashboard_trades)} trades)")
        
        # Generate teams JSON
        teams_response = {
            "success": True,
            "data": {
                "teams": teams_with_stats,
                "summary": {
                    "totalTeams": len(teams_with_stats),
                    "totalTrades": len(dashboard_trades),
                    "seasonsIncluded": cumulative_metadata.get('seasons_included', [])
                }
            }
        }
        
        with open(OUTPUT_TEAMS, 'w') as f:
            json.dump(teams_response, f, indent=2)
        logger.info(f"✓ Generated {OUTPUT_TEAMS} ({len(teams_with_stats)} teams)")
        
        # Generate stats summary JSON with multi-season support
        stats_response = {
            "success": True,
            "data": {
                "overview": league_stats,
                "teamRankings": {
                    "byValueGained": sorted(teams_with_stats, key=lambda t: t['totalValueGained'], reverse=True)[:10],
                    "byWinRate": sorted([t for t in teams_with_stats if t['tradeCount'] > 0], key=lambda t: t['winRate'], reverse=True)[:10],
                    "byTradeCount": sorted(teams_with_stats, key=lambda t: t['tradeCount'], reverse=True)[:10]
                },
                "multiSeasonData": {
                    "seasonsIncluded": cumulative_metadata.get('seasons_included', []),
                    "tradesBySeason": cumulative_metadata.get('trades_by_season', {}),
                    "seasonInfo": cumulative_metadata.get('season_info', {})
                },
                "recentActivity": dashboard_trades[-10:] if dashboard_trades else []  # Last 10 trades
            }
        }
        
        with open(OUTPUT_STATS, 'w') as f:
            json.dump(stats_response, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"✓ Generated {OUTPUT_STATS}")
        
        logger.info("="*80)
        logger.info("✅ DASHBOARD JSON GENERATION FROM CUMULATIVE FILES COMPLETE")
        logger.info(f"   Generated dashboard files with {len(dashboard_trades)} processed trades")
        logger.info(f"   Seasons included: {cumulative_metadata.get('seasons_included', [])}")
        logger.info(f"   Source: Cumulative multi-season files (raw API data processed)")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"Failed to generate dashboard JSON from cumulative files: {e}")
        raise


if __name__ == "__main__":
    try:
        generate_dashboard_json_from_cumulative()
        print("\n🎉 Dashboard JSON files generated successfully from cumulative data!")
        print("   Multi-season support enabled with season filtering metadata.")
    except Exception as e:
        logger.error(f"Failed to generate JSON files: {e}")
        print(f"\n❌ Error: {e}")
        exit(1)