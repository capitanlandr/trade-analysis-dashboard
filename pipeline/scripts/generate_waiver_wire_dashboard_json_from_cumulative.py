#!/usr/bin/env python3
"""
Generate Waiver Wire Dashboard JSON from Cumulative Files

This script replaces generate_waiver_wire_dashboard_json.py to use cumulative multi-season files
as the source instead of CSV files. This implements Task 11 - Dashboard Data Synchronization
for the multi-season architecture.

MULTI-SEASON ARCHITECTURE:
==========================
This script reads from cumulative waiver-wire.json that contains ALL seasons' waiver data
with season tags, then generates dashboard JSON files that support client-side season filtering.

Key Changes from Original:
- Reads from cumulative waiver-wire.json instead of waiver_wire_analysis.csv
- Preserves season metadata in dashboard JSON
- Supports multi-season data structure
- Maintains backward compatibility with existing frontend
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Any
import sys
import os

# Add pipeline utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.logging_config import get_logger
from utils.team_resolver import TeamResolver
from utils.api_client import fetch_with_retry

# Initialize logger
logger = get_logger(__name__)

# Get script directory and set up paths
SCRIPT_DIR = Path(__file__).parent
PIPELINE_DIR = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_DIR.parent

# Input paths - cumulative files (source of truth)
CUMULATIVE_WAIVER_WIRE = PIPELINE_DIR / 'waiver-wire.json'
ASSET_VALUES_CSV = PIPELINE_DIR / 'asset_values_cache.csv'  # Still needed for player values

# Output paths - dashboard JSON files
DASHBOARD_DIR = REPO_ROOT / 'dashboard/frontend/public'
OUTPUT_WAIVER_WIRE = DASHBOARD_DIR / 'api-waiver-wire.json'

# Optional data files for enhanced metrics
PLAYER_STATS_FILE = PIPELINE_DIR / 'player_stats_weekly.json'
LINEUP_DATA_FILE = PIPELINE_DIR / 'lineup_data_weekly.json'


def load_cumulative_waiver_wire() -> Dict[str, Any]:
    """
    Load waiver wire data from cumulative waiver-wire.json file.
    
    Returns:
        Dict containing waiver transactions and metadata from cumulative file
        
    Raises:
        FileNotFoundError: If cumulative waiver wire file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    logger.info(f"Loading cumulative waiver wire data from {CUMULATIVE_WAIVER_WIRE}")
    
    if not CUMULATIVE_WAIVER_WIRE.exists():
        raise FileNotFoundError(f"Cumulative waiver wire file not found: {CUMULATIVE_WAIVER_WIRE}")
    
    try:
        with open(CUMULATIVE_WAIVER_WIRE, 'r') as f:
            cumulative_data = json.load(f)
        
        # Handle different key names in cumulative file
        transactions = cumulative_data.get('transactions', [])
        if not transactions:
            # Try alternative key name used in waiver-wire.json
            transactions = cumulative_data.get('waiver-wire', [])
        
        metadata = cumulative_data.get('metadata', {})
        
        logger.info(f"✓ Loaded {len(transactions)} waiver transactions from cumulative file")
        logger.info(f"✓ Seasons included: {metadata.get('seasons_included', [])}")
        
        # Normalize the data structure
        normalized_data = {
            'transactions': transactions,
            'metadata': metadata
        }
        
        return normalized_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in cumulative waiver wire file: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load cumulative waiver wire data: {e}")
        raise


def process_raw_waiver_transactions_to_dataframe(cumulative_data: Dict[str, Any], team_mappings: Dict[int, str]) -> pd.DataFrame:
    """
    Process raw waiver wire transactions from cumulative data into DataFrame format.
    
    This function transforms raw Sleeper API waiver transactions into the processed
    format expected by the dashboard generation functions.
    
    Args:
        cumulative_data: Cumulative waiver wire data with raw transactions
        team_mappings: Roster ID to username mappings
        
    Returns:
        DataFrame with processed waiver wire transactions
    """
    transactions = cumulative_data.get('transactions', [])
    
    if not transactions:
        logger.warning("No transactions found in cumulative data")
        return pd.DataFrame()
    
    processed_transactions = []
    
    for raw_txn in transactions:
        # Extract basic transaction info
        transaction_id = raw_txn.get('transaction_id', '')
        txn_type = raw_txn.get('type', 'free_agent')
        status = raw_txn.get('status', 'complete')
        created_timestamp = raw_txn.get('created', 0)
        status_updated_timestamp = raw_txn.get('status_updated', 0)
        leg = raw_txn.get('leg', 1)  # Week number
        season = raw_txn.get('season', 'unknown')
        
        # Convert timestamps to datetime
        from datetime import datetime
        created_dt = datetime.fromtimestamp(created_timestamp / 1000) if created_timestamp else None
        status_updated_dt = datetime.fromtimestamp(status_updated_timestamp / 1000) if status_updated_timestamp else None
        
        # Process waiver settings for bid amount and priority
        waiver_bid = 0
        priority = None
        sequence = None
        
        settings = raw_txn.get('settings', {})
        if settings:
            waiver_bid = settings.get('waiver_bid', 0)
            priority = settings.get('priority')
            sequence = settings.get('seq')
        
        # Process adds and drops (handle None values)
        adds = raw_txn.get('adds') or {}
        drops = raw_txn.get('drops') or {}
        
        # Get roster IDs involved
        roster_ids = raw_txn.get('roster_ids', [])
        
        # Process each add as a separate transaction record
        for player_id, to_roster in adds.items():
            team_name = team_mappings.get(to_roster, f"Team {to_roster}")
            
            processed_transactions.append({
                'transaction_id': str(transaction_id),
                'type': txn_type,
                'action': 'add',
                'status': status,
                'roster_id': to_roster,
                'team_name': team_name,
                'player_id': str(player_id),
                'waiver_bid': waiver_bid,
                'week': leg,
                'created_dt': created_dt,
                'status_updated_dt': status_updated_dt,
                'notes': '',  # Raw API doesn't include notes
                'sequence': sequence,
                'priority': priority,
                'season': season
            })
        
        # Process each drop as a separate transaction record
        for player_id, from_roster in drops.items():
            team_name = team_mappings.get(from_roster, f"Team {from_roster}")
            
            processed_transactions.append({
                'transaction_id': str(transaction_id),
                'type': txn_type,
                'action': 'drop',
                'status': status,
                'roster_id': from_roster,
                'team_name': team_name,
                'player_id': str(player_id),
                'waiver_bid': 0,  # Drops don't have bids
                'week': leg,
                'created_dt': created_dt,
                'status_updated_dt': status_updated_dt,
                'notes': '',
                'sequence': sequence,
                'priority': priority,
                'season': season
            })
    
    # Convert to DataFrame
    df = pd.DataFrame(processed_transactions)
    
    if df.empty:
        return df
    
    # Ensure proper data types
    df['roster_id'] = pd.to_numeric(df['roster_id'], errors='coerce').fillna(0).astype(int)
    df['waiver_bid'] = pd.to_numeric(df['waiver_bid'], errors='coerce').fillna(0)
    df['week'] = pd.to_numeric(df['week'], errors='coerce').fillna(1).astype(int)
    
    # Handle sequence and priority - convert None to -1 for consistency
    df['sequence'] = df['sequence'].fillna(-1).astype(int)
    df['priority'] = df['priority'].fillna(-1).astype(int)
    
    logger.info(f"✓ Processed {len(df)} transaction records from {len(transactions)} raw transactions")
    return df


def load_team_mappings() -> Dict[int, str]:
    """Load team mappings from team_identity_mapping.csv."""
    teams_csv = PIPELINE_DIR / 'team_identity_mapping.csv'
    
    try:
        if not teams_csv.exists():
            logger.warning("team_identity_mapping.csv not found")
            return {}
        
        import pandas as pd
        df = pd.read_csv(teams_csv)
        
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


def load_asset_values() -> Dict[str, int]:
    """Load player values from asset_values_cache.csv."""
    try:
        if not ASSET_VALUES_CSV.exists():
            logger.warning("asset_values_cache.csv not found - player values will not be available")
            return {}
        
        df = pd.read_csv(ASSET_VALUES_CSV)
        
        # Filter to only player assets (not picks or FAAB)
        player_df = df[df['asset_type'] == 'player'].copy()
        
        if player_df.empty:
            logger.warning("No player data found in asset_values_cache.csv")
            return {}
        
        # Create mapping from player name to current value
        player_values = {}
        for _, row in player_df.iterrows():
            player_name = row['asset_name']
            value = row['value_current']
            
            if pd.notna(player_name) and pd.notna(value):
                player_values[player_name] = int(value)
        
        logger.info(f"✓ Loaded values for {len(player_values)} players from asset_values_cache.csv")
        return player_values
        
    except Exception as e:
        logger.warning(f"Failed to load asset values: {e}")
        return {}


def load_player_data() -> Dict[str, Dict[str, Any]]:
    """Fetch player data from Sleeper API for name resolution."""
    try:
        logger.info("Fetching player data from Sleeper API...")
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


def calculate_churn_metrics(df, current_week=15, roster_size=25):
    """Calculate roster churn index for each manager."""
    churn_data = []
    
    for roster_id in df['roster_id'].unique():
        manager_txns = df[df['roster_id'] == roster_id]
        team_name = manager_txns['team_name'].iloc[0] if not manager_txns.empty else f"Team {roster_id}"
        
        # Count adds and drops
        adds = len(manager_txns[manager_txns['action'] == 'add'])
        drops = len(manager_txns[manager_txns['action'] == 'drop'])
        
        # Calculate overall churn
        weeks_elapsed = current_week - 1
        overall_churn = ((adds + drops) / (weeks_elapsed * roster_size)) * 100 if weeks_elapsed > 0 else 0
        
        # Categorize management style
        if overall_churn > 20:
            style = 'extreme'
        elif overall_churn > 10:
            style = 'active'
        elif overall_churn > 5:
            style = 'moderate'
        else:
            style = 'passive'
        
        churn_data.append({
            'roster_id': int(roster_id),
            'team_name': team_name,
            'total_adds': adds,
            'total_drops': drops,
            'overall_churn_rate': round(overall_churn, 2),
            'management_style': style
        })
    
    return churn_data


def generate_manager_activity_from_cumulative(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Generate manager activity summary from cumulative waiver wire data.
    
    Args:
        df: DataFrame with waiver wire transactions
        
    Returns:
        List of manager activity dictionaries
    """
    manager_activity = []
    
    for roster_id in df['roster_id'].unique():
        manager_txns = df[df['roster_id'] == roster_id]
        team_name = manager_txns['team_name'].iloc[0] if not manager_txns.empty else f"Team {roster_id}"
        
        # Calculate waiver-specific metrics
        waiver_txns = manager_txns[manager_txns['type'] == 'waiver']
        
        total_claims = len(waiver_txns)
        successful_claims = len(waiver_txns[waiver_txns['status'] == 'complete'])
        success_rate = (successful_claims / total_claims * 100) if total_claims > 0 else 0
        
        # Calculate bidding metrics
        total_bid = waiver_txns['waiver_bid'].sum()
        avg_bid = waiver_txns['waiver_bid'].mean() if len(waiver_txns) > 0 else 0
        max_bid = waiver_txns['waiver_bid'].max() if len(waiver_txns) > 0 else 0
        
        manager_activity.append({
            'roster_id': int(roster_id),
            'team_name': team_name,
            'total_claims': total_claims,
            'successful_claims': successful_claims,
            'success_rate': round(success_rate, 1),
            'total_bid': int(total_bid) if pd.notna(total_bid) else 0,
            'avg_bid': round(avg_bid, 1) if pd.notna(avg_bid) else 0,
            'max_bid': int(max_bid) if pd.notna(max_bid) else 0
        })
    
    return manager_activity


def generate_all_transactions_from_cumulative(df: pd.DataFrame, players: Dict, player_values: Dict) -> List[Dict[str, Any]]:
    """
    Generate all transactions list from cumulative data.
    
    Args:
        df: DataFrame with waiver wire transactions
        players: Player data from Sleeper API
        player_values: Player values from asset cache
        
    Returns:
        List of transaction dictionaries
    """
    def get_player_name(player_id):
        if not player_id or player_id == 'None':
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
    
    def get_player_value(player_name):
        if not player_name or player_name == 'Unknown Player':
            return None
        
        # Direct lookup by name
        value = player_values.get(player_name)
        if value is not None:
            return value
        
        # Try case-insensitive match as fallback
        player_name_lower = player_name.lower()
        for name, val in player_values.items():
            if name.lower() == player_name_lower:
                return val
        
        return None
    
    all_transactions = []
    
    # Sort by date (most recent first)
    df_sorted = df.sort_values('created_dt', ascending=False, na_position='last')
    
    for _, row in df_sorted.iterrows():
        # Handle sequence and priority - convert -1 to None
        sequence_val = None
        if pd.notna(row['sequence']):
            seq = int(row['sequence'])
            sequence_val = None if seq == -1 else seq
        
        priority_val = None
        if pd.notna(row['priority']):
            pri = int(row['priority'])
            priority_val = None if pri == -1 else pri
        
        player_name = get_player_name(row['player_id'])
        player_value = get_player_value(player_name)
        
        # Map season to year
        season_str = str(row.get('season', 'unknown'))
        year_map = {
            'season_2': 2025,
            'season_3': 2026
        }
        year = year_map.get(season_str, None)
        
        transaction = {
            'transaction_id': str(row['transaction_id']),
            'type': str(row['type']),
            'action': str(row['action']),
            'status': str(row['status']),
            'team_name': str(row['team_name']) or f"Team {row['roster_id']}",
            'roster_id': int(row['roster_id']) if pd.notna(row['roster_id']) else None,
            'player_name': player_name,
            'player_id': str(row['player_id']) if pd.notna(row['player_id']) else None,
            'player_value': player_value,
            'waiver_bid': int(row['waiver_bid']) if pd.notna(row['waiver_bid']) else 0,
            'week': int(row['week']) if pd.notna(row['week']) else 1,
            'created_date': row['created_dt'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['created_dt']) and hasattr(row['created_dt'], 'strftime') else str(row['created_dt']) if pd.notna(row['created_dt']) else None,
            'status_updated_date': row['status_updated_dt'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['status_updated_dt']) and hasattr(row['status_updated_dt'], 'strftime') else str(row['status_updated_dt']) if pd.notna(row['status_updated_dt']) else None,
            'notes': str(row['notes']) if pd.notna(row['notes']) else '',
            'sequence': sequence_val,
            'priority': priority_val,
            'season': season_str,  # Include season tag
            'year': year  # Add year field for display
        }
        all_transactions.append(transaction)
    
    return all_transactions


def generate_weekly_activity_from_cumulative(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Generate weekly activity chart data from cumulative data.
    
    Args:
        df: DataFrame with waiver wire transactions
        
    Returns:
        List of weekly activity dictionaries
    """
    weekly_activity = []
    
    # Group by week and type
    for week in sorted(df['week'].unique()):
        week_data = df[df['week'] == week]
        
        waiver_count = len(week_data[week_data['type'] == 'waiver'])
        free_agent_count = len(week_data[week_data['type'] == 'free_agent'])
        
        weekly_activity.append({
            'week': int(week),
            'waiver_transactions': waiver_count,
            'free_agent_transactions': free_agent_count,
            'total_transactions': waiver_count + free_agent_count
        })
    
    return weekly_activity


def generate_contested_players_from_cumulative(df: pd.DataFrame, players: Dict) -> List[Dict[str, Any]]:
    """
    Generate contested players data from cumulative data.
    
    Args:
        df: DataFrame with waiver wire transactions
        players: Player data from Sleeper API
        
    Returns:
        List of contested player dictionaries
    """
    def get_player_name(player_id):
        if not player_id or player_id == 'None':
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
    
    contested_players = []
    
    # Group by player_id and count claims
    player_claims = df.groupby('player_id').agg({
        'transaction_id': 'count',
        'status': lambda x: sum(x == 'complete'),
        'waiver_bid': 'max'
    }).reset_index()
    
    # Filter to players with multiple claims (contested)
    contested = player_claims[player_claims['transaction_id'] > 1]
    
    for _, row in contested.iterrows():
        contested_players.append({
            'player_id': str(row['player_id']),
            'player_name': get_player_name(row['player_id']),
            'total_claims': int(row['transaction_id']),
            'successful_claims': int(row['status']),
            'highest_bid': int(row['waiver_bid']) if pd.notna(row['waiver_bid']) else 0
        })
    
    # Sort by total claims (most contested first)
    contested_players.sort(key=lambda x: x['total_claims'], reverse=True)
    
    return contested_players


def generate_bidding_patterns_from_cumulative(df: pd.DataFrame, players: Dict) -> Dict[str, Any]:
    """
    Generate bidding patterns data from cumulative data.
    
    Args:
        df: DataFrame with waiver wire transactions
        players: Player data from Sleeper API
        
    Returns:
        Dictionary with bidding patterns data
    """
    def get_player_name(player_id):
        if not player_id or player_id == 'None':
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
    
    waiver_txns = df[df['type'] == 'waiver']
    
    # Bid distribution
    bid_ranges = {
        '0': 0,
        '1-5': 0,
        '6-10': 0,
        '11-20': 0,
        '21-50': 0,
        '51+': 0
    }
    
    for bid in waiver_txns['waiver_bid']:
        if pd.isna(bid) or bid == 0:
            bid_ranges['0'] += 1
        elif bid <= 5:
            bid_ranges['1-5'] += 1
        elif bid <= 10:
            bid_ranges['6-10'] += 1
        elif bid <= 20:
            bid_ranges['11-20'] += 1
        elif bid <= 50:
            bid_ranges['21-50'] += 1
        else:
            bid_ranges['51+'] += 1
    
    # Highest bids
    highest_bids = []
    top_bids = waiver_txns.nlargest(10, 'waiver_bid')
    
    for _, row in top_bids.iterrows():
        highest_bids.append({
            'player_id': str(row['player_id']),
            'player_name': get_player_name(row['player_id']),
            'waiver_bid': int(row['waiver_bid']) if pd.notna(row['waiver_bid']) else 0,
            'team_name': str(row['team_name']) or 'Unknown Team',
            'status': str(row['status'])
        })
    
    # Zero bid success rate
    zero_bids = waiver_txns[waiver_txns['waiver_bid'] == 0]
    zero_bid_success_rate = (len(zero_bids[zero_bids['status'] == 'complete']) / len(zero_bids) * 100) if len(zero_bids) > 0 else 0
    
    return {
        'distribution': bid_ranges,
        'highest_bids': highest_bids,
        'zero_bid_success_rate': round(zero_bid_success_rate, 1)
    }


def generate_waiver_wire_dashboard_data_from_cumulative():
    """
    Generate waiver wire dashboard JSON from cumulative multi-season data.
    
    This is the main function that implements Task 11 - Dashboard Data Synchronization
    for waiver wire data. It reads from cumulative files and generates dashboard JSON
    with multi-season support.
    """
    logger.info("="*80)
    logger.info("GENERATING WAIVER WIRE DASHBOARD JSON FROM CUMULATIVE FILES")
    logger.info("="*80)
    
    try:
        # Load cumulative waiver wire data (raw Sleeper API format)
        cumulative_data = load_cumulative_waiver_wire()
        cumulative_metadata = cumulative_data.get('metadata', {})
        
        # Load team mappings for processing raw data
        team_mappings = load_team_mappings()
        
        # Process raw transactions into DataFrame format
        df = process_raw_waiver_transactions_to_dataframe(cumulative_data, team_mappings)
        
        if df.empty:
            logger.warning("No waiver wire data found - generating empty dashboard")
            # Generate empty dashboard structure
            dashboard_data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_waiver_transactions': 0,
                    'total_free_agent_transactions': 0,
                    'successful_waivers': 0,
                    'failed_waivers': 0,
                    'success_rate': 0,
                    'total_waiver_bids': 0,
                    'average_waiver_bid': 0,
                    'seasonsIncluded': cumulative_metadata.get('seasons_included', []),
                    'transactionsBySeason': cumulative_metadata.get('transactions_by_season', {}),
                    'source': 'cumulative_files'
                },
                'manager_activity': [],
                'churn_metrics': [],
                'all_transactions': [],
                'recent_activity': [],
                'weekly_activity': [],
                'contested_players': [],
                'bidding_patterns': {
                    'distribution': {},
                    'highest_bids': [],
                    'zero_bid_success_rate': 0
                }
            }
        else:
            # Load additional data for enhanced processing
            player_values = load_asset_values()
            players = load_player_data()
            
            logger.info(f"Processing {len(df)} waiver wire transaction records...")
            
            # Generate manager activity
            manager_activity = generate_manager_activity_from_cumulative(df)
            logger.info(f"✓ Generated activity data for {len(manager_activity)} managers")
            
            # Calculate churn metrics
            churn_metrics = calculate_churn_metrics(df, current_week=15, roster_size=25)
            logger.info(f"✓ Calculated churn metrics for {len(churn_metrics)} managers")
            
            # Generate all transactions
            all_transactions = generate_all_transactions_from_cumulative(df, players, player_values)
            recent_activity = all_transactions[:50] if all_transactions else []
            logger.info(f"✓ Generated {len(all_transactions)} transaction records")
            
            # Generate weekly activity
            weekly_activity = generate_weekly_activity_from_cumulative(df)
            logger.info(f"✓ Generated weekly activity for {len(weekly_activity)} weeks")
            
            # Generate contested players
            contested_players = generate_contested_players_from_cumulative(df, players)
            logger.info(f"✓ Identified {len(contested_players)} contested players")
            
            # Generate bidding patterns
            bidding_patterns = generate_bidding_patterns_from_cumulative(df, players)
            logger.info(f"✓ Generated bidding patterns with {len(bidding_patterns['highest_bids'])} top bids")
            
            # Calculate summary statistics
            total_waiver_txns = len(df[df['type'] == 'waiver'])
            total_fa_txns = len(df[df['type'] == 'free_agent'])
            successful_waivers = len(df[(df['type'] == 'waiver') & (df['status'] == 'complete')])
            failed_waivers = total_waiver_txns - successful_waivers
            success_rate = (successful_waivers / total_waiver_txns * 100) if total_waiver_txns > 0 else 0
            total_waiver_bids = df[df['type'] == 'waiver']['waiver_bid'].sum()
            avg_waiver_bid = df[df['type'] == 'waiver']['waiver_bid'].mean()
            
            # Create main dashboard data with multi-season metadata
            dashboard_data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_waiver_transactions': total_waiver_txns,
                    'total_free_agent_transactions': total_fa_txns,
                    'successful_waivers': successful_waivers,
                    'failed_waivers': failed_waivers,
                    'success_rate': round(success_rate, 1),
                    'total_waiver_bids': int(total_waiver_bids) if pd.notna(total_waiver_bids) else 0,
                    'average_waiver_bid': round(avg_waiver_bid, 1) if pd.notna(avg_waiver_bid) else 0,
                    # Multi-season metadata from cumulative file
                    'seasonsIncluded': cumulative_metadata.get('seasons_included', []),
                    'transactionsBySeason': cumulative_metadata.get('transactions_by_season', {}),
                    'seasonInfo': cumulative_metadata.get('season_info', {}),
                    'schemaVersion': cumulative_metadata.get('schema_version', '2.0.0'),
                    'source': 'cumulative_files',  # Indicate this came from cumulative data
                    'processingInfo': {
                        'rawTransactionsProcessed': len(cumulative_data.get('transactions', [])),
                        'processedRecordsGenerated': len(df)
                    }
                },
                'manager_activity': manager_activity,
                'churn_metrics': churn_metrics,
                'efficiency_metrics': None,  # Would need player stats for this
                'hit_rate_metrics': None,    # Would need lineup data for this
                'timing_metrics': None,      # Would need both for this
                'all_transactions': all_transactions,
                'recent_activity': recent_activity,
                'weekly_activity': weekly_activity,
                'contested_players': contested_players,
                'bidding_patterns': bidding_patterns
            }
        
        # Ensure output directory exists
        DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Clean NaN values before serializing
        def clean_nan(obj):
            """Recursively replace NaN with None in nested structures."""
            import math
            if isinstance(obj, dict):
                return {k: clean_nan(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nan(item) for item in obj]
            elif isinstance(obj, float) and math.isnan(obj):
                return None
            else:
                return obj
        
        cleaned_data = clean_nan(dashboard_data)
        
        # Save dashboard data
        with open(OUTPUT_WAIVER_WIRE, 'w') as f:
            json.dump(cleaned_data, f, indent=2)
        
        logger.info(f"✓ Generated {OUTPUT_WAIVER_WIRE}")
        
        logger.info("="*80)
        logger.info("✅ WAIVER WIRE DASHBOARD JSON GENERATION FROM CUMULATIVE FILES COMPLETE")
        logger.info(f"   Generated dashboard with {len(dashboard_data.get('all_transactions', []))} transactions")
        logger.info(f"   Seasons included: {cumulative_metadata.get('seasons_included', [])}")
        logger.info(f"   Source: Cumulative multi-season files (raw API data processed)")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"Failed to generate waiver wire dashboard JSON from cumulative files: {e}")
        raise


if __name__ == "__main__":
    try:
        generate_waiver_wire_dashboard_data_from_cumulative()
        print("\n🎉 Waiver wire dashboard JSON generated successfully from cumulative data!")
        print("   Multi-season support enabled with season filtering metadata.")
    except Exception as e:
        logger.error(f"Failed to generate waiver wire JSON: {e}")
        print(f"\n❌ Error: {e}")
        exit(1)