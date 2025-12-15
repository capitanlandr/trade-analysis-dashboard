#!/usr/bin/env python3
"""
Generate waiver wire dashboard JSON files for the frontend.
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_config import setup_logging
from utils.team_resolver import TeamResolver
from utils.api_client import fetch_with_retry

logger = setup_logging(__name__)

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

def calculate_efficiency_metrics(df, player_stats):
    """
    Calculate Waiver Wire Efficiency Score (WWES) for each manager.
    
    Args:
        df: DataFrame with waiver wire transactions
        player_stats: Dict mapping player_id -> {week -> {fantasy_points, stats}}
    
    Returns:
        Dict with manager_metrics and league_stats
    """
    if not player_stats:
        logger.warning("No player stats available - skipping efficiency calculation")
        return None
    
    efficiency_data = []
    
    for roster_id in df['roster_id'].unique():
        manager_txns = df[df['roster_id'] == roster_id]
        team_name = manager_txns['team_name'].iloc[0] if not manager_txns.empty else f"Team {roster_id}"
        
        # Filter to successful adds only
        adds = manager_txns[
            (manager_txns['action'] == 'add') &
            (manager_txns['status'] == 'complete')
        ]
        
        total_points = 0
        for _, add in adds.iterrows():
            player_id = str(add['player_id'])
            acq_week = int(add['week']) if pd.notna(add['week']) else 1
            
            # Sum points scored AFTER acquisition
            if player_id in player_stats:
                for week, stats in player_stats[player_id].items():
                    if int(week) > acq_week:
                        total_points += stats.get('fantasy_points', 0)
        
        # Calculate WWES components
        faab_spent = adds[adds['type'] == 'waiver']['waiver_bid'].sum()
        faab_spent = int(faab_spent) if pd.notna(faab_spent) else 0
        fa_count = len(adds[adds['type'] == 'free_agent'])
        
        # WWES = Total Points / (FAAB Spent + Free Agent Count)
        denominator = faab_spent + fa_count
        raw_wwes = total_points / denominator if denominator > 0 else 0
        
        efficiency_data.append({
            'roster_id': int(roster_id),
            'team_name': team_name,
            'total_points_from_adds': round(total_points, 2),
            'faab_spent': faab_spent,
            'free_agent_count': fa_count,
            'raw_wwes': round(raw_wwes, 2)
        })
    
    # Calculate league stats for normalization
    wwes_values = [m['raw_wwes'] for m in efficiency_data if m['raw_wwes'] > 0]
    
    if not wwes_values:
        logger.warning("No valid WWES scores - all managers have 0")
        return None
    
    mean_wwes = sum(wwes_values) / len(wwes_values) if wwes_values else 0
    
    # Calculate std dev
    if len(wwes_values) > 1:
        variance = sum((x - mean_wwes) ** 2 for x in wwes_values) / len(wwes_values)
        std_dev = variance ** 0.5
    else:
        std_dev = 1
    
    # Add normalized scores and percentiles
    for metric in efficiency_data:
        if std_dev > 0 and metric['raw_wwes'] > 0:
            metric['normalized_wwes'] = round(
                (metric['raw_wwes'] - mean_wwes) / std_dev, 2
            )
        else:
            metric['normalized_wwes'] = 0
        
        # Calculate percentile
        rank = sum(1 for m in efficiency_data if m['raw_wwes'] < metric['raw_wwes'])
        metric['league_percentile'] = round((rank / len(efficiency_data)) * 100, 1) if efficiency_data else 50
    
    return {
        'manager_metrics': efficiency_data,
        'league_stats': {
            'mean_wwes': round(mean_wwes, 2),
            'std_dev_wwes': round(std_dev, 2),
            'median_wwes': round(sorted(wwes_values)[len(wwes_values)//2], 2) if wwes_values else 0
        }
    }

def generate_waiver_wire_dashboard_data():
    """Generate dashboard JSON files for waiver wire analysis."""
    logger.info("Generating waiver wire dashboard data...")
    
    try:
        # Load processed data
        if not Path('waiver_wire_analysis.csv').exists():
            logger.error("waiver_wire_analysis.csv not found. Run stage5_waiver_wire.py first.")
            return
        
        df = pd.read_csv('waiver_wire_analysis.csv')
        
        # Load analysis summary
        analysis_summary = {}
        if Path('waiver_wire_summary.json').exists():
            with open('waiver_wire_summary.json', 'r') as f:
                analysis_summary = json.load(f)
        
        # Load player data for name resolution
        players = load_player_data()
        team_resolver = TeamResolver()
        
        # Helper function to get player name
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
        
        # Generate manager activity summary
        manager_activity = []
        if 'manager_activity' in analysis_summary:
            for manager in analysis_summary['manager_activity']:
                manager_activity.append({
                    'roster_id': manager.get('roster_id'),
                    'team_name': manager.get('team_name', f"Team {manager.get('roster_id')}"),
                    'total_claims': manager.get('total_claims', 0),
                    'successful_claims': manager.get('successful_claims', 0),
                    'success_rate': manager.get('success_rate', 0),
                    'total_bid': manager.get('total_bid', 0),
                    'avg_bid': manager.get('avg_bid', 0),
                    'max_bid': manager.get('max_bid', 0)
                })
        
        # Generate all transactions for the table
        all_transactions = []
        if not df.empty:
            # Get all transactions, sorted by date (most recent first)
            df['created_dt'] = pd.to_datetime(df['created_dt'])
            df_sorted = df.sort_values('created_dt', ascending=False)
            
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
                
                transaction = {
                    'transaction_id': row['transaction_id'],
                    'type': row['type'],
                    'action': row['action'],
                    'status': row['status'],
                    'team_name': row['team_name'] or f"Team {row['roster_id']}",
                    'roster_id': int(row['roster_id']) if pd.notna(row['roster_id']) else None,
                    'player_name': get_player_name(row['player_id']),
                    'player_id': str(row['player_id']) if pd.notna(row['player_id']) else None,
                    'waiver_bid': int(row['waiver_bid']) if pd.notna(row['waiver_bid']) else 0,
                    'week': int(row['week']) if pd.notna(row['week']) else 1,
                    'created_date': row['created_dt'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['created_dt']) and hasattr(row['created_dt'], 'strftime') else str(row['created_dt']) if pd.notna(row['created_dt']) else None,
                    'status_updated_date': row['status_updated_dt'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['status_updated_dt']) and hasattr(row['status_updated_dt'], 'strftime') else str(row['status_updated_dt']) if pd.notna(row['status_updated_dt']) else None,
                    'notes': str(row['notes']) if pd.notna(row['notes']) else '',
                    'sequence': sequence_val,
                    'priority': priority_val
                }
                all_transactions.append(transaction)
        
        # Also keep recent activity for backward compatibility
        recent_activity = all_transactions[:50] if all_transactions else []
        
        # Calculate churn metrics
        churn_metrics = calculate_churn_metrics(df, current_week=15, roster_size=25)
        logger.info(f"Calculated churn metrics for {len(churn_metrics)} managers")
        
        # Load player stats and calculate efficiency metrics
        efficiency_metrics = None
        player_stats_file = Path('player_stats_weekly.json')
        if player_stats_file.exists():
            try:
                logger.info("Loading player stats for efficiency calculation...")
                with open(player_stats_file, 'r') as f:
                    player_stats = json.load(f)
                
                efficiency_metrics = calculate_efficiency_metrics(df, player_stats)
                if efficiency_metrics:
                    logger.info(f"Calculated efficiency metrics for {len(efficiency_metrics['manager_metrics'])} managers")
                else:
                    logger.warning("Efficiency metrics calculation returned None")
            except Exception as e:
                logger.warning(f"Failed to calculate efficiency metrics: {e}")
        else:
            logger.info("player_stats_weekly.json not found - skipping efficiency metrics")
        
        # Generate weekly activity chart data
        weekly_activity = []
        if 'weekly_activity' in analysis_summary:
            for week, activity_data in analysis_summary['weekly_activity'].items():
                weekly_activity.append({
                    'week': int(week),
                    'waiver_transactions': activity_data.get('waiver', 0),
                    'free_agent_transactions': activity_data.get('free_agent', 0),
                    'total_transactions': activity_data.get('waiver', 0) + activity_data.get('free_agent', 0)
                })
            
            # Sort by week
            weekly_activity.sort(key=lambda x: x['week'])
        
        # Generate contested players data
        contested_players = []
        if 'contested_players' in analysis_summary:
            for player_id, contest_data in analysis_summary['contested_players'].items():
                contested_players.append({
                    'player_id': player_id,
                    'player_name': get_player_name(player_id),
                    'total_claims': contest_data.get('transaction_id', 0),
                    'successful_claims': contest_data.get('status', 0),
                    'highest_bid': contest_data.get('waiver_bid', 0)
                })
        
        # Generate bidding patterns
        bidding_patterns = analysis_summary.get('bidding_patterns', {})
        
        # Prepare highest bids with player names
        highest_bids = []
        if 'highest_bids' in bidding_patterns:
            for bid in bidding_patterns['highest_bids']:
                highest_bids.append({
                    'player_id': bid.get('player_id'),
                    'player_name': get_player_name(bid.get('player_id')),
                    'waiver_bid': bid.get('waiver_bid', 0),
                    'team_name': bid.get('team_name', 'Unknown Team'),
                    'status': bid.get('status', 'unknown')
                })
        
        # Create main dashboard data
        dashboard_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_waiver_transactions': analysis_summary.get('summary', {}).get('total_waiver_transactions', 0),
                'total_free_agent_transactions': analysis_summary.get('summary', {}).get('total_free_agent_transactions', 0),
                'successful_waivers': analysis_summary.get('summary', {}).get('successful_waivers', 0),
                'failed_waivers': analysis_summary.get('summary', {}).get('failed_waivers', 0),
                'success_rate': round(
                    (analysis_summary.get('summary', {}).get('successful_waivers', 0) /
                     max(analysis_summary.get('summary', {}).get('total_waiver_transactions', 1), 1)) * 100, 1
                ),
                'total_waiver_bids': analysis_summary.get('summary', {}).get('total_waiver_bids', 0),
                'average_waiver_bid': round(analysis_summary.get('summary', {}).get('average_waiver_bid', 0), 1)
            },
            'manager_activity': manager_activity,
            'churn_metrics': churn_metrics,
            'efficiency_metrics': efficiency_metrics,
            'all_transactions': all_transactions,
            'recent_activity': recent_activity,
            'weekly_activity': weekly_activity,
            'contested_players': contested_players,
            'bidding_patterns': {
                'distribution': bidding_patterns.get('bid_distribution', {}),
                'highest_bids': highest_bids,
                'zero_bid_success_rate': round(bidding_patterns.get('zero_bid_success_rate', 0), 1)
            }
        }
        
        # Save dashboard data
        output_files = [
            '../dashboard/frontend/public/api-waiver-wire.json',  # Correct path relative to pipeline dir
            'api-waiver-wire.json'  # Also save in pipeline dir for reference
        ]
        
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
        
        # Clean NaN values before serializing
        cleaned_data = clean_nan(dashboard_data)
        
        for output_file in output_files:
            # Create directory if it doesn't exist
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(cleaned_data, f, indent=2)
            
            logger.info(f"Generated {output_file}")
        
        # Generate summary stats for quick access
        summary_stats = {
            'total_managers': len(manager_activity),
            'most_active_manager': max(manager_activity, key=lambda x: x['total_claims'])['team_name'] if manager_activity else 'N/A',
            'highest_success_rate': max(manager_activity, key=lambda x: x['success_rate'])['team_name'] if manager_activity else 'N/A',
            'biggest_spender': max(manager_activity, key=lambda x: x['total_bid'])['team_name'] if manager_activity else 'N/A',
            'most_contested_player': contested_players[0]['player_name'] if contested_players else 'N/A',
            'busiest_week': max(weekly_activity, key=lambda x: x['total_transactions'])['week'] if weekly_activity else 'N/A'
        }
        
        with open('waiver_wire_stats.json', 'w') as f:
            json.dump(summary_stats, f, indent=2)
        
        logger.info("Waiver wire dashboard data generation completed successfully")
        logger.info(f"Generated data for {len(manager_activity)} managers")
        logger.info(f"Processed {len(recent_activity)} recent transactions")
        logger.info(f"Identified {len(contested_players)} contested players")
        
    except Exception as e:
        logger.error(f"Failed to generate waiver wire dashboard data: {e}")
        raise

if __name__ == "__main__":
    generate_waiver_wire_dashboard_data()