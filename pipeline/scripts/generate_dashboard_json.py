#!/usr/bin/env python3
"""
Generate Static JSON Files for Dashboard

Converts the CSV pipeline outputs to JSON files that the static dashboard can use.
This bridges the gap between our Python pipeline and the static React frontend.
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

# Get script directory and set up paths
SCRIPT_DIR = Path(__file__).parent
PIPELINE_DIR = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_DIR.parent

# File paths (relative to pipeline directory)
TRADES_CSV = PIPELINE_DIR / 'league_trades_analysis_pipeline.csv'
TEAMS_CSV = PIPELINE_DIR / 'team_identity_mapping.csv'
MULTITEAM_JSON = PIPELINE_DIR / '3team_trades_analysis.json'
ASSET_VALUES_CSV = PIPELINE_DIR / 'asset_values_cache.csv'
STANDINGS_JSON = PIPELINE_DIR / 'standings_data.json'

# Output paths (go up to repo root, then into dashboard)
DASHBOARD_DIR = REPO_ROOT / 'dashboard/frontend/public'
OUTPUT_TRADES = DASHBOARD_DIR / 'api-trades.json'
OUTPUT_TEAMS = DASHBOARD_DIR / 'api-teams.json'
OUTPUT_STATS = DASHBOARD_DIR / 'api-stats-summary.json'
OUTPUT_STANDINGS = DASHBOARD_DIR / 'api-standings.json'


def load_asset_values() -> pd.DataFrame:
    """Load asset values cache."""
    logger.info(f"Loading asset values from {ASSET_VALUES_CSV}")
    df = pd.read_csv(ASSET_VALUES_CSV)
    logger.info(f"✓ Loaded {len(df)} asset valuations")
    return df


def load_trades_data() -> List[Dict[str, Any]]:
    """Load and convert trades CSV to JSON format with individual asset values."""
    logger.info(f"Loading trades from {TRADES_CSV}")
    
    trades_df = pd.read_csv(TRADES_CSV)
    asset_values_df = load_asset_values()
    
    logger.info(f"✓ Loaded {len(trades_df)} trades")
    
    trades = []
    for _, row in trades_df.iterrows():
        # Helper function to safely convert to float, replacing NaN with 0
        def safe_float(value):
            try:
                result = float(value)
                return 0 if pd.isna(result) else result
            except (ValueError, TypeError):
                return 0
        
        # Convert pipe-separated strings to arrays with values
        def parse_assets_with_values(asset_string, transaction_id, receiving_team):
            if pd.isna(asset_string) or str(asset_string).strip() == '':
                return []
            
            asset_names = [asset.strip() for asset in str(asset_string).split('|') if asset.strip()]
            assets_with_values = []
            
            for asset_name in asset_names:
                # Look up asset value from asset_values_cache
                # Note: asset_values_cache uses 'trade_id' column
                asset_row = asset_values_df[
                    (asset_values_df['trade_id'].astype(str) == str(transaction_id)) &
                    (asset_values_df['asset_name'] == asset_name) &
                    (asset_values_df['receiving_team'] == receiving_team)
                ]
                
                if not asset_row.empty:
                    assets_with_values.append({
                        "name": asset_name,
                        "valueThen": safe_float(asset_row.iloc[0]['value_at_trade']),
                        "valueNow": safe_float(asset_row.iloc[0]['value_current'])
                    })
                else:
                    # Debug: try without receiving_team filter
                    debug_row = asset_values_df[
                        (asset_values_df['trade_id'].astype(str) == str(transaction_id)) &
                        (asset_values_df['asset_name'] == asset_name)
                    ]
                    
                    if not debug_row.empty:
                        logger.warning(f"Found asset '{asset_name}' but receiving_team mismatch. Expected: '{receiving_team}', Found: '{debug_row.iloc[0]['receiving_team']}'")
                        # Use it anyway
                        assets_with_values.append({
                            "name": asset_name,
                            "valueThen": safe_float(debug_row.iloc[0]['value_at_trade']),
                            "valueNow": safe_float(debug_row.iloc[0]['value_current'])
                        })
                    else:
                        logger.warning(f"Asset not found: trade_id={transaction_id}, asset={asset_name}, team={receiving_team}")
                        assets_with_values.append({
                            "name": asset_name,
                            "valueThen": 0,
                            "valueNow": 0
                        })
            
            return assets_with_values
        
        transaction_id = str(row['transaction_id'])
        team_a = str(row['team_a'])
        team_b = str(row['team_b'])
        
        trade = {
            "tradeId": transaction_id,
            "transactionId": transaction_id,
            "tradeDate": str(row['trade_date']),
            "teamA": team_a,
            "teamAReceived": [a['name'] for a in parse_assets_with_values(row['team_a_received'], transaction_id, team_a)],
            "teamAAssets": parse_assets_with_values(row['team_a_received'], transaction_id, team_a),
            "teamAValueThen": safe_float(row['team_a_value_then']),
            "teamAValueNow": safe_float(row['team_a_value_now']),
            "teamAValueChange": safe_float(row['team_a_value_change']),
            "teamB": team_b,
            "teamBReceived": [a['name'] for a in parse_assets_with_values(row['team_b_received'], transaction_id, team_b)],
            "teamBAssets": parse_assets_with_values(row['team_b_received'], transaction_id, team_b),
            "teamBValueThen": safe_float(row['team_b_value_then']),
            "teamBValueNow": safe_float(row['team_b_value_now']),
            "teamBValueChange": safe_float(row['team_b_value_change']),
            "winnerAtTrade": str(row['winner_at_trade']),
            "winnerCurrent": str(row['winner_current']),
            "marginAtTrade": safe_float(row['margin_at_trade']),
            "marginCurrent": safe_float(row['margin_current']),
            "swingWinner": str(row['swing_winner']),
            "swingMargin": safe_float(row['swing_margin'])
        }
        trades.append(trade)
    
    return trades


def load_teams_data() -> List[Dict[str, Any]]:
    """Load and convert teams CSV to JSON format."""
    logger.info(f"Loading teams from {TEAMS_CSV}")
    
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
            "tradeCount": 0,  # Will be calculated
            "winRate": 0,     # Will be calculated
            "avgMargin": 0,   # Will be calculated
            "totalValueGained": 0  # Will be calculated
        }
        teams.append(team)
    
    return teams


def calculate_team_stats(teams: List[Dict], trades: List[Dict]) -> List[Dict]:
    """Calculate team statistics from trades."""
    logger.info("Calculating team statistics...")
    
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
    
    # Calculate stats from trades
    for trade in trades:
        team_a = trade['teamA']  # This is sleeper username
        team_b = trade['teamB']  # This is sleeper username
        
        if team_a in team_stats:
            stats = team_stats[team_a]
            stats['tradeCount'] += 1
            stats['totalMargin'] += abs(trade['marginCurrent'])
            stats['totalValueGained'] += trade['teamAValueChange']
            if trade['winnerCurrent'] == team_a:
                stats['wins'] += 1
        
        if team_b in team_stats:
            stats = team_stats[team_b]
            stats['tradeCount'] += 1
            stats['totalMargin'] += abs(trade['marginCurrent'])
            stats['totalValueGained'] += trade['teamBValueChange']
            if trade['winnerCurrent'] == team_b:
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


def calculate_league_stats(trades: List[Dict], teams: List[Dict]) -> Dict[str, Any]:
    """Calculate league-wide statistics."""
    logger.info("Calculating league statistics...")
    
    if not trades:
        return {
            "totalTrades": 0,
            "totalTradeValue": 0,
            "avgTradeMargin": 0,
            "mostActiveTrader": "",
            "biggestWinner": "",
            "blockbusterCount": 0,
            "dateRange": {"earliest": "", "latest": ""}
        }
    
    total_trade_value = sum(trade['teamAValueNow'] + trade['teamBValueNow'] for trade in trades)
    avg_trade_margin = sum(abs(trade['marginCurrent']) for trade in trades) / len(trades)
    
    # Find most active trader
    most_active = max(teams, key=lambda t: t['tradeCount'])
    
    # Find biggest winner
    biggest_winner = max(teams, key=lambda t: t['totalValueGained'])
    
    # Count blockbuster trades (>5000 total value)
    blockbuster_count = sum(1 for trade in trades if (trade['teamAValueNow'] + trade['teamBValueNow']) > 5000)
    
    # Date range
    trade_dates = [trade['tradeDate'] for trade in trades]
    trade_dates.sort()
    
    return {
        "totalTrades": len(trades),
        "totalTradeValue": total_trade_value,
        "avgTradeMargin": avg_trade_margin,
        "mostActiveTrader": most_active['realName'],
        "biggestWinner": biggest_winner['realName'],
        "blockbusterCount": blockbuster_count,
        "dateRange": {
            "earliest": trade_dates[0] if trade_dates else "",
            "latest": trade_dates[-1] if trade_dates else ""
        }
    }


def generate_json_files():
    """Generate all JSON files for the dashboard."""
    logger.info("="*80)
    logger.info("GENERATING DASHBOARD JSON FILES")
    logger.info("="*80)
    
    # Ensure output directory exists
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load data
    trades = load_trades_data()
    teams = load_teams_data()
    
    # Calculate team stats
    teams_with_stats = calculate_team_stats(teams, trades)
    
    # Calculate league stats
    league_stats = calculate_league_stats(trades, teams_with_stats)
    
    # Generate trades JSON
    trades_response = {
        "success": True,
        "data": {
            "trades": trades,
            "metadata": {
                "lastUpdated": datetime.now().isoformat(),
                "totalTrades": len(trades),
                "dateRange": league_stats["dateRange"]
            }
        }
    }
    
    with open(OUTPUT_TRADES, 'w') as f:
        json.dump(trades_response, f, indent=2)
    logger.info(f"✓ Generated {OUTPUT_TRADES} ({len(trades)} trades)")
    
    # Generate teams JSON
    teams_response = {
        "success": True,
        "data": {
            "teams": teams_with_stats,
            "summary": {
                "totalTeams": len(teams_with_stats),
                "totalTrades": len(trades)
            }
        }
    }
    
    with open(OUTPUT_TEAMS, 'w') as f:
        json.dump(teams_response, f, indent=2)
    logger.info(f"✓ Generated {OUTPUT_TEAMS} ({len(teams_with_stats)} teams)")
    
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
            "tradesByMonth": {},  # Could be calculated if needed
            "valueDistribution": {},  # Could be calculated if needed
            "swingAnalysis": {},  # Could be calculated if needed
            "recentActivity": trades[-10:] if trades else []  # Last 10 trades
        }
    }
    
    # Use ensure_ascii=False and handle NaN values properly
    with open(OUTPUT_STATS, 'w') as f:
        json.dump(stats_response, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"✓ Generated {OUTPUT_STATS}")
    
    # Generate standings JSON (if available)
    if STANDINGS_JSON.exists():
        logger.info(f"Loading standings from {STANDINGS_JSON}")
        with open(STANDINGS_JSON, 'r') as f:
            standings_data = json.load(f)
        
        with open(OUTPUT_STANDINGS, 'w') as f:
            json.dump(standings_data, f, indent=2)
        logger.info(f"✓ Generated {OUTPUT_STANDINGS}")
    else:
        logger.warning(f"Standings data not found at {STANDINGS_JSON}")
        logger.warning("Run 'python scripts/fetch_standings.py' to generate standings data")
    
    # Generate playoff scenarios JSON (if available)
    PLAYOFF_SCENARIOS_JSON = PIPELINE_DIR / 'playoff_scenarios_simulated.json'
    OUTPUT_PLAYOFF_SCENARIOS = DASHBOARD_DIR / 'api-playoff-scenarios.json'
    
    if PLAYOFF_SCENARIOS_JSON.exists():
        logger.info(f"Loading playoff scenarios from {PLAYOFF_SCENARIOS_JSON}")
        with open(PLAYOFF_SCENARIOS_JSON, 'r') as f:
            playoff_data = json.load(f)
        
        with open(OUTPUT_PLAYOFF_SCENARIOS, 'w') as f:
            json.dump(playoff_data, f, indent=2)
        logger.info(f"✓ Generated {OUTPUT_PLAYOFF_SCENARIOS}")
    else:
        logger.warning(f"Playoff scenarios not found at {PLAYOFF_SCENARIOS_JSON}")
        logger.warning("Run 'python scripts/simulate_playoff_scenarios.py' to generate playoff scenarios")
    
    logger.info("="*80)
    logger.info("✅ JSON GENERATION COMPLETE")
    logger.info(f"   Dashboard files updated with {len(trades)} trades")
    logger.info("="*80)


if __name__ == "__main__":
    try:
        generate_json_files()
        print("\n🎉 Dashboard JSON files generated successfully!")
        print("   Run the dashboard update script to deploy these changes.")
    except Exception as e:
        logger.error(f"Failed to generate JSON files: {e}")
        print(f"\n❌ Error: {e}")
        exit(1)