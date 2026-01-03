#!/usr/bin/env python3
"""
Generate Dashboard JSON from Cumulative Files (Simplified Version)

This script replaces generate_dashboard_json.py to use cumulative multi-season files
as the source instead of CSV files. This implements Task 11 - Dashboard Data Synchronization
for the multi-season architecture.

This is a simplified version that processes raw Sleeper API data from cumulative files
into dashboard JSON format without complex dependencies.
"""

import json
import pandas as pd
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import os

# Get script directory and set up paths
SCRIPT_DIR = Path(__file__).parent
PIPELINE_DIR = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_DIR.parent

# Input paths - cumulative files (source of truth)
CUMULATIVE_TRADES = PIPELINE_DIR / 'trades.json'
TEAMS_CSV = PIPELINE_DIR / 'team_identity_mapping.csv'
ASSET_VALUES_CSV = PIPELINE_DIR / 'asset_values_cache.csv'

# Output paths - dashboard JSON files
DASHBOARD_DIR = REPO_ROOT / 'dashboard/frontend/public'
OUTPUT_TRADES = DASHBOARD_DIR / 'api-trades.json'
OUTPUT_TEAMS = DASHBOARD_DIR / 'api-teams.json'
OUTPUT_STATS = DASHBOARD_DIR / 'api-stats-summary.json'


def load_cumulative_trades() -> Dict[str, Any]:
    """Load trade data from cumulative trades.json file."""
    print(f"Loading cumulative trades from {CUMULATIVE_TRADES}")
    
    if not CUMULATIVE_TRADES.exists():
        raise FileNotFoundError(f"Cumulative trades file not found: {CUMULATIVE_TRADES}")
    
    with open(CUMULATIVE_TRADES, 'r') as f:
        cumulative_data = json.load(f)
    
    trades = cumulative_data.get('trades', [])
    metadata = cumulative_data.get('metadata', {})
    
    print(f"✓ Loaded {len(trades)} trades from cumulative file")
    print(f"✓ Seasons included: {metadata.get('seasons_included', [])}")
    
    return cumulative_data


def load_team_mappings() -> Dict[int, str]:
    """Load team mappings from team_identity_mapping.csv."""
    if not TEAMS_CSV.exists():
        print("Warning: team_identity_mapping.csv not found")
        return {}
    
    df = pd.read_csv(TEAMS_CSV)
    
    # Create mapping from roster_id to sleeper_username
    team_mappings = {}
    for _, row in df.iterrows():
        roster_id = row.get('roster_id')
        username = row.get('sleeper_username', '')
        
        if pd.notna(roster_id) and pd.notna(username):
            team_mappings[int(roster_id)] = str(username)
    
    print(f"✓ Loaded mappings for {len(team_mappings)} teams")
    return team_mappings


def load_asset_values() -> Dict[str, Dict[str, int]]:
    """Load asset values from asset_values_cache.csv."""
    if not ASSET_VALUES_CSV.exists():
        print("Warning: asset_values_cache.csv not found - using default values")
        return {}
    
    df = pd.read_csv(ASSET_VALUES_CSV)
    
    # Create mapping from asset name to values
    asset_values = {}
    for _, row in df.iterrows():
        asset_name = row['asset_name']
        value_current = row['value_current']
        value_at_trade = row.get('value_at_trade', value_current)
        
        if pd.notna(asset_name):
            asset_values[asset_name] = {
                'current': int(value_current) if pd.notna(value_current) else 0,
                'at_trade': int(value_at_trade) if pd.notna(value_at_trade) else 0
            }
    
    print(f"✓ Loaded values for {len(asset_values)} assets")
    return asset_values


def fetch_player_data() -> Dict[str, Dict[str, Any]]:
    """Fetch player data from Sleeper API."""
    try:
        print("Fetching player data from Sleeper API...")
        response = requests.get("https://api.sleeper.app/v1/players/nfl", timeout=30)
        response.raise_for_status()
        players = response.json()
        
        print(f"✓ Loaded {len(players)} players from Sleeper API")
        return players
    except Exception as e:
        print(f"Warning: Failed to fetch player data: {e}")
        return {}


def get_player_name(player_id: str, players: Dict) -> str:
    """Get player name from player ID."""
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


def get_asset_value(asset_name: str, asset_values: Dict, value_type: str = 'current') -> int:
    """Get asset value by name and type."""
    if not asset_name or asset_name == 'Unknown Player':
        return 0
    
    asset_data = asset_values.get(asset_name, {})
    return asset_data.get(value_type, 0)


def format_draft_pick(pick: Dict) -> str:
    """Format draft pick as readable string."""
    season = pick.get('season', 'Unknown')
    round_num = pick.get('round', 'Unknown')
    return f"{season} Round {round_num}"


def process_raw_trade_to_dashboard_format(raw_trade: Dict, players: Dict, asset_values: Dict, team_mappings: Dict) -> Optional[Dict]:
    """Process a raw Sleeper API trade into dashboard format."""
    
    # Extract basic trade info
    transaction_id = str(raw_trade.get('transaction_id', ''))
    created_timestamp = raw_trade.get('created', 0)
    trade_date = datetime.fromtimestamp(created_timestamp / 1000).strftime('%Y-%m-%d') if created_timestamp else ''
    season = raw_trade.get('season', '')
    roster_ids = raw_trade.get('roster_ids', [])
    
    # Only process 2-team trades for now
    if len(roster_ids) != 2:
        return None
    
    roster_a, roster_b = roster_ids[0], roster_ids[1]
    team_a = team_mappings.get(roster_a, f"Team {roster_a}")
    team_b = team_mappings.get(roster_b, f"Team {roster_b}")
    
    # Process assets (handle None values)
    adds = raw_trade.get('adds') or {}
    draft_picks = raw_trade.get('draft_picks') or []
    waiver_budget = raw_trade.get('waiver_budget') or []
    
    # Initialize team assets and values
    team_a_assets = []
    team_a_value_then = 0
    team_a_value_now = 0
    
    team_b_assets = []
    team_b_value_then = 0
    team_b_value_now = 0
    
    # Process player adds
    for player_id, to_roster in adds.items():
        player_name = get_player_name(player_id, players)
        value_then = get_asset_value(player_name, asset_values, 'at_trade')
        value_now = get_asset_value(player_name, asset_values, 'current')
        
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
    for pick in draft_picks:
        pick_name = format_draft_pick(pick)
        value_then = get_asset_value(pick_name, asset_values, 'at_trade')
        value_now = get_asset_value(pick_name, asset_values, 'current')
        
        asset_info = {
            'name': pick_name,
            'type': 'draft_pick',
            'value_then': value_then,
            'value_now': value_now
        }
        
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
    for faab_transfer in waiver_budget:
        amount = faab_transfer.get('amount', 0)
        receiver = faab_transfer.get('receiver')
        
        faab_name = f"${amount} FAAB"
        # FAAB has minimal fantasy value, use amount as rough value
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
    return {
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


def load_teams_data() -> List[Dict[str, Any]]:
    """Load team data from CSV file."""
    if not TEAMS_CSV.exists():
        print("Warning: Teams CSV not found")
        return []
    
    df = pd.read_csv(TEAMS_CSV)
    
    teams = []
    for _, row in df.iterrows():
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
            "tradeCount": 0,
            "winRate": 0,
            "avgMargin": 0,
            "totalValueGained": 0
        }
        teams.append(team)
    
    return teams


def calculate_team_stats(teams: List[Dict], processed_trades: List[Dict]) -> List[Dict]:
    """Calculate team statistics from processed trades."""
    print("Calculating team statistics...")
    
    # Create lookup by sleeper username
    team_stats = {}
    for team in teams:
        username = team['sleeperUsername']
        team_stats[username] = {
            'tradeCount': 0,
            'wins': 0,
            'totalMargin': 0,
            'totalValueGained': 0
        }
    
    # Calculate stats from processed trades
    for trade in processed_trades:
        if not trade:  # Skip None trades
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


def calculate_league_stats(processed_trades: List[Dict], teams: List[Dict]) -> Dict[str, Any]:
    """Calculate league-wide statistics."""
    print("Calculating league statistics...")
    
    # Filter out None trades
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


def main():
    """Generate dashboard JSON files from cumulative data."""
    print("="*80)
    print("GENERATING DASHBOARD JSON FROM CUMULATIVE FILES")
    print("="*80)
    
    # Ensure output directory exists
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load cumulative trade data (raw Sleeper API format)
        cumulative_data = load_cumulative_trades()
        raw_trades = cumulative_data.get('trades', [])
        cumulative_metadata = cumulative_data.get('metadata', {})
        
        print(f"Processing {len(raw_trades)} raw trades from cumulative file...")
        
        # Load supporting data
        players = fetch_player_data()
        asset_values = load_asset_values()
        team_mappings = load_team_mappings()
        teams = load_teams_data()
        
        # Process raw trades into dashboard format
        dashboard_trades = []
        processed_count = 0
        skipped_count = 0
        
        for raw_trade in raw_trades:
            processed_trade = process_raw_trade_to_dashboard_format(
                raw_trade, players, asset_values, team_mappings
            )
            
            if processed_trade:
                dashboard_trades.append(processed_trade)
                processed_count += 1
            else:
                skipped_count += 1
        
        print(f"✓ Processed {processed_count} trades to dashboard format")
        if skipped_count > 0:
            print(f"✓ Skipped {skipped_count} multi-team trades (not yet supported)")
        
        # Calculate team stats
        teams_with_stats = calculate_team_stats(teams, dashboard_trades)
        
        # Calculate league stats
        league_stats = calculate_league_stats(dashboard_trades, teams_with_stats)
        
        # Generate trades JSON
        trades_response = {
            "success": True,
            "data": {
                "trades": dashboard_trades,
                "metadata": {
                    "lastUpdated": datetime.now().isoformat(),
                    "totalTrades": len(dashboard_trades),
                    "dateRange": league_stats["dateRange"],
                    "seasonsIncluded": cumulative_metadata.get('seasons_included', []),
                    "tradesBySeason": cumulative_metadata.get('trades_by_season', {}),
                    "seasonInfo": cumulative_metadata.get('season_info', {}),
                    "schemaVersion": cumulative_metadata.get('schema_version', '2.0.0'),
                    "source": "cumulative_files",
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
        print(f"✓ Generated {OUTPUT_TRADES} ({len(dashboard_trades)} trades)")
        
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
        print(f"✓ Generated {OUTPUT_TEAMS} ({len(teams_with_stats)} teams)")
        
        # Generate stats summary JSON
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
                "recentActivity": dashboard_trades[-10:] if dashboard_trades else []
            }
        }
        
        with open(OUTPUT_STATS, 'w') as f:
            json.dump(stats_response, f, indent=2)
        print(f"✓ Generated {OUTPUT_STATS}")
        
        print("="*80)
        print("✅ DASHBOARD JSON GENERATION FROM CUMULATIVE FILES COMPLETE")
        print(f"   Generated dashboard files with {len(dashboard_trades)} processed trades")
        print(f"   Seasons included: {cumulative_metadata.get('seasons_included', [])}")
        print(f"   Source: Cumulative multi-season files (raw API data processed)")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Failed to generate dashboard JSON: {e}")
        raise


if __name__ == "__main__":
    main()