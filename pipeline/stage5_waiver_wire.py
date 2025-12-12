#!/usr/bin/env python3
"""
Stage 5: Waiver Wire Analysis Pipeline
Fetches and processes waiver wire and free agent transaction data from Sleeper API.
"""

import json
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path

from utils.api_client import fetch_with_retry
from utils.logging_config import setup_logging
from utils.backup import BackupManager
from utils.team_resolver import TeamResolver

# Setup logging
logger = setup_logging(__name__)

class WaiverWireProcessor:
    """Process waiver wire and free agent transactions."""
    
    def __init__(self, league_id: str):
        self.league_id = league_id
        self.team_resolver = TeamResolver()
        self.base_url = "https://api.sleeper.app/v1"
        
    def fetch_waiver_transactions(self) -> List[Dict[str, Any]]:
        """Fetch all waiver wire transactions for the season."""
        logger.info("Fetching waiver wire transactions...")
        
        all_transactions = []
        
        # Fetch transactions for each week (1-18 for regular season + playoffs)
        for week in range(1, 19):
            try:
                url = f"{self.base_url}/league/{self.league_id}/transactions/{week}"
                transactions = fetch_with_retry(url)
                if transactions:
                    # Filter for waiver transactions only
                    waiver_transactions = [t for t in transactions if t.get('type') == 'waiver']
                    all_transactions.extend(waiver_transactions)
                    logger.info(f"Week {week}: Found {len(waiver_transactions)} waiver transactions")
            except Exception as e:
                logger.warning(f"Failed to fetch waiver transactions for week {week}: {e}")
                
        logger.info(f"Total waiver transactions fetched: {len(all_transactions)}")
        return all_transactions
    
    def fetch_free_agent_transactions(self) -> List[Dict[str, Any]]:
        """Fetch all free agent transactions for the season."""
        logger.info("Fetching free agent transactions...")
        
        all_transactions = []
        
        # Fetch transactions for each week
        for week in range(1, 19):
            try:
                url = f"{self.base_url}/league/{self.league_id}/transactions/{week}"
                transactions = fetch_with_retry(url)
                if transactions:
                    # Filter for free agent transactions only
                    fa_transactions = [t for t in transactions if t.get('type') == 'free_agent']
                    all_transactions.extend(fa_transactions)
                    logger.info(f"Week {week}: Found {len(fa_transactions)} free agent transactions")
            except Exception as e:
                logger.warning(f"Failed to fetch free agent transactions for week {week}: {e}")
                
        logger.info(f"Total free agent transactions fetched: {len(all_transactions)}")
        return all_transactions
    
    def process_waiver_transactions(self, transactions: List[Dict[str, Any]]) -> pd.DataFrame:
        """Process waiver transactions into structured data."""
        logger.info("Processing waiver transactions...")
        
        processed_data = []
        
        for txn in transactions:
            try:
                # Extract basic transaction info
                base_data = {
                    'transaction_id': txn.get('transaction_id'),
                    'type': 'waiver',
                    'status': txn.get('status'),
                    'created': txn.get('created'),
                    'status_updated': txn.get('status_updated'),
                    'week': txn.get('leg', 1),
                    'creator': txn.get('creator'),
                    'roster_id': txn.get('roster_ids', [None])[0],
                }
                
                # Add waiver-specific data
                settings = txn.get('settings', {})
                base_data.update({
                    'waiver_bid': settings.get('waiver_bid', 0),
                    'sequence': settings.get('seq', 0),
                    'priority': settings.get('priority'),
                })
                
                # Add success/failure reason
                metadata = txn.get('metadata', {})
                base_data['notes'] = metadata.get('notes', '')
                
                # Process adds and drops
                adds = txn.get('adds', {})
                drops = txn.get('drops', {})
                
                # Create separate rows for each player transaction
                if adds:
                    for player_id, roster_id in adds.items():
                        row = base_data.copy()
                        row.update({
                            'action': 'add',
                            'player_id': player_id,
                            'target_roster_id': roster_id
                        })
                        processed_data.append(row)
                
                if drops:
                    for player_id, roster_id in drops.items():
                        row = base_data.copy()
                        row.update({
                            'action': 'drop',
                            'player_id': player_id,
                            'target_roster_id': roster_id
                        })
                        processed_data.append(row)
                
                # If no adds/drops, still record the transaction
                if not adds and not drops:
                    row = base_data.copy()
                    row.update({
                        'action': 'unknown',
                        'player_id': None,
                        'target_roster_id': None
                    })
                    processed_data.append(row)
                    
            except Exception as e:
                logger.warning(f"Failed to process waiver transaction {txn.get('transaction_id')}: {e}")
        
        df = pd.DataFrame(processed_data)
        
        if not df.empty:
            # Convert timestamps
            df['created_dt'] = pd.to_datetime(df['created'], unit='ms')
            df['status_updated_dt'] = pd.to_datetime(df['status_updated'], unit='ms')
            
            # Add team names
            df['team_name'] = df['roster_id'].apply(
                lambda x: self.team_resolver.get_current_team_name(x) if x else None
            )
        
        logger.info(f"Processed {len(df)} waiver transaction records")
        return df
    
    def process_free_agent_transactions(self, transactions: List[Dict[str, Any]]) -> pd.DataFrame:
        """Process free agent transactions into structured data."""
        logger.info("Processing free agent transactions...")
        
        processed_data = []
        
        for txn in transactions:
            try:
                # Extract basic transaction info
                base_data = {
                    'transaction_id': txn.get('transaction_id'),
                    'type': 'free_agent',
                    'status': txn.get('status'),
                    'created': txn.get('created'),
                    'status_updated': txn.get('status_updated'),
                    'week': txn.get('leg', 1),
                    'creator': txn.get('creator'),
                    'roster_id': txn.get('roster_ids', [None])[0],
                    'waiver_bid': 0,  # Free agents don't have bids
                    'sequence': None,
                    'priority': None,
                    'notes': 'Free agent transaction'
                }
                
                # Process adds and drops
                adds = txn.get('adds', {})
                drops = txn.get('drops', {})
                
                # Create separate rows for each player transaction
                if adds:
                    for player_id, roster_id in adds.items():
                        row = base_data.copy()
                        row.update({
                            'action': 'add',
                            'player_id': player_id,
                            'target_roster_id': roster_id
                        })
                        processed_data.append(row)
                
                if drops:
                    for player_id, roster_id in drops.items():
                        row = base_data.copy()
                        row.update({
                            'action': 'drop',
                            'player_id': player_id,
                            'target_roster_id': roster_id
                        })
                        processed_data.append(row)
                
                # If no adds/drops, still record the transaction
                if not adds and not drops:
                    row = base_data.copy()
                    row.update({
                        'action': 'unknown',
                        'player_id': None,
                        'target_roster_id': None
                    })
                    processed_data.append(row)
                    
            except Exception as e:
                logger.warning(f"Failed to process free agent transaction {txn.get('transaction_id')}: {e}")
        
        df = pd.DataFrame(processed_data)
        
        if not df.empty:
            # Convert timestamps
            df['created_dt'] = pd.to_datetime(df['created'], unit='ms')
            df['status_updated_dt'] = pd.to_datetime(df['status_updated'], unit='ms')
            
            # Add team names
            df['team_name'] = df['roster_id'].apply(
                lambda x: self.team_resolver.get_current_team_name(x) if x else None
            )
        
        logger.info(f"Processed {len(df)} free agent transaction records")
        return df
    
    def generate_waiver_analysis(self, waiver_df: pd.DataFrame, fa_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive waiver wire analysis."""
        logger.info("Generating waiver wire analysis...")
        
        analysis = {
            'summary': {
                'total_waiver_transactions': len(waiver_df),
                'total_free_agent_transactions': len(fa_df),
                'successful_waivers': len(waiver_df[waiver_df['status'] == 'complete']),
                'failed_waivers': len(waiver_df[waiver_df['status'] == 'failed']),
                'total_waiver_bids': waiver_df['waiver_bid'].sum(),
                'average_waiver_bid': waiver_df[waiver_df['waiver_bid'] > 0]['waiver_bid'].mean(),
            }
        }
        
        # Manager activity analysis
        if not waiver_df.empty:
            manager_stats = waiver_df.groupby(['roster_id', 'team_name']).agg({
                'transaction_id': 'nunique',
                'waiver_bid': ['sum', 'mean', 'max'],
                'status': lambda x: (x == 'complete').sum(),
            }).round(2)
            
            manager_stats.columns = ['total_claims', 'total_bid', 'avg_bid', 'max_bid', 'successful_claims']
            manager_stats['success_rate'] = (manager_stats['successful_claims'] / manager_stats['total_claims'] * 100).round(1)
            manager_stats = manager_stats.reset_index()
            
            analysis['manager_activity'] = manager_stats.to_dict('records')
        
        # Weekly activity
        combined_df = pd.concat([waiver_df, fa_df], ignore_index=True)
        if not combined_df.empty:
            weekly_activity = combined_df.groupby(['week', 'type']).size().unstack(fill_value=0)
            analysis['weekly_activity'] = weekly_activity.to_dict('index')
        
        # Most contested players (multiple waiver claims)
        if not waiver_df.empty:
            player_contests = waiver_df[waiver_df['action'] == 'add'].groupby('player_id').agg({
                'transaction_id': 'nunique',
                'waiver_bid': 'max',
                'status': lambda x: (x == 'complete').sum()
            })
            player_contests = player_contests[player_contests['transaction_id'] > 1].sort_values('transaction_id', ascending=False)
            analysis['contested_players'] = player_contests.head(20).to_dict('index')
        
        # Bidding patterns
        if not waiver_df.empty:
            bid_analysis = {
                'bid_distribution': waiver_df[waiver_df['waiver_bid'] > 0]['waiver_bid'].value_counts().to_dict(),
                'highest_bids': waiver_df.nlargest(10, 'waiver_bid')[['player_id', 'waiver_bid', 'team_name', 'status']].to_dict('records'),
                'zero_bid_success_rate': len(waiver_df[(waiver_df['waiver_bid'] == 0) & (waiver_df['status'] == 'complete')]) / len(waiver_df[waiver_df['waiver_bid'] == 0]) * 100 if len(waiver_df[waiver_df['waiver_bid'] == 0]) > 0 else 0
            }
            analysis['bidding_patterns'] = bid_analysis
        
        return analysis

def main():
    """Main execution function."""
    logger.info("Starting Stage 5: Waiver Wire Analysis")
    
    try:
        # Load configuration
        import yaml
        with open('config/default.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        league_id = config['league']['id']
        
        # Initialize processor
        processor = WaiverWireProcessor(league_id)
        
        # Create backups
        backup_manager = BackupManager()
        backup_files = [
            'waiver_transactions_raw.json',
            'free_agent_transactions_raw.json',
            'waiver_wire_analysis.csv',
            'waiver_wire_summary.json'
        ]
        
        for file in backup_files:
            if Path(file).exists():
                backup_manager.backup_file(file, 'stage5')
        
        # Fetch raw data
        waiver_transactions = processor.fetch_waiver_transactions()
        fa_transactions = processor.fetch_free_agent_transactions()
        
        # Save raw data
        with open('waiver_transactions_raw.json', 'w') as f:
            json.dump(waiver_transactions, f, indent=2)
        
        with open('free_agent_transactions_raw.json', 'w') as f:
            json.dump(fa_transactions, f, indent=2)
        
        # Process data
        waiver_df = processor.process_waiver_transactions(waiver_transactions)
        fa_df = processor.process_free_agent_transactions(fa_transactions)
        
        # Combine and save processed data
        combined_df = pd.concat([waiver_df, fa_df], ignore_index=True)
        combined_df.to_csv('waiver_wire_analysis.csv', index=False)
        
        # Generate analysis
        analysis = processor.generate_waiver_analysis(waiver_df, fa_df)
        
        # Save analysis
        with open('waiver_wire_summary.json', 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        logger.info("Stage 5 completed successfully")
        logger.info(f"Processed {len(waiver_transactions)} waiver transactions")
        logger.info(f"Processed {len(fa_transactions)} free agent transactions")
        logger.info(f"Generated analysis with {len(analysis)} sections")
        
    except Exception as e:
        logger.error(f"Stage 5 failed: {e}")
        raise

if __name__ == "__main__":
    main()