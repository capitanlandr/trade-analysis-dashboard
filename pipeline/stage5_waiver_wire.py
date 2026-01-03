#!/usr/bin/env python3
"""
Stage 5: Waiver Wire Analysis Pipeline (Multi-Season Architecture)
Fetches and processes waiver wire and free agent transaction data with incremental support

MULTI-SEASON FEATURES:
- Incremental fetching based on last_fetch_timestamp for active seasons
- Season configuration integration for active vs static season handling
- Cumulative file management with atomic operations and deduplication
- Enhanced API error handling with exponential backoff for rate limits
- Season tagging for all new transactions
"""

import json
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path

from utils.api_client import fetch_with_retry, RateLimitError, APIError
from utils.logging_config import setup_logging
from utils.backup import BackupManager
from utils.team_resolver import TeamResolver
from utils.season_config import get_season_config, validate_season_operation
from utils.cumulative_file_manager import CumulativeFileManager, CumulativeFileError

# Setup logging
logger = setup_logging(__name__)

class WaiverWireProcessor:
    """Process waiver wire and free agent transactions with multi-season support."""
    
    def __init__(self, league_id: str, season_name: str = None):
        self.league_id = league_id
        self.season_name = season_name
        self.team_resolver = TeamResolver()
        self.base_url = "https://api.sleeper.app/v1"
        
    def fetch_waiver_transactions(self, incremental: bool = True, 
                                last_fetch_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch waiver wire transactions with incremental support.
        
        Args:
            incremental: If True, only fetch transactions newer than last_fetch_timestamp
            last_fetch_timestamp: ISO timestamp of last fetch (for incremental mode)
            
        Returns:
            List of waiver transactions
            
        Raises:
            RateLimitError: If rate limits are exceeded
            APIError: If API calls fail after retries
        """
        logger.info("Fetching waiver wire transactions...")
        
        # Convert last_fetch_timestamp to milliseconds for comparison
        last_fetch_ms = None
        if incremental and last_fetch_timestamp:
            try:
                dt = datetime.fromisoformat(last_fetch_timestamp.replace('Z', '+00:00'))
                last_fetch_ms = int(dt.timestamp() * 1000)
                logger.info(f"Incremental fetch since: {dt} ({last_fetch_ms}ms)")
            except ValueError as e:
                logger.warning(f"Invalid last_fetch_timestamp format, performing full fetch: {e}")
                incremental = False
        
        all_transactions = []
        rate_limited_weeks = 0
        
        # Fetch transactions for each week (1-18 for regular season + playoffs)
        for week in range(1, 19):
            try:
                url = f"{self.base_url}/league/{self.league_id}/transactions/{week}"
                transactions = fetch_with_retry(url)
                
                if transactions:
                    # Filter for waiver transactions only
                    waiver_transactions = [t for t in transactions if t.get('type') == 'waiver']
                    
                    # Add league_id to each transaction (required by cumulative file manager)
                    for txn in waiver_transactions:
                        txn['league_id'] = self.league_id
                    
                    # Filter by timestamp if incremental
                    if incremental and last_fetch_ms:
                        new_transactions = []
                        for txn in waiver_transactions:
                            txn_created = txn.get('created', 0)
                            if txn_created > last_fetch_ms:
                                new_transactions.append(txn)
                        waiver_transactions = new_transactions
                        
                        if waiver_transactions:
                            logger.info(f"Week {week}: Found {len(waiver_transactions)} new waiver transactions since last fetch")
                    elif waiver_transactions:
                        logger.info(f"Week {week}: Found {len(waiver_transactions)} waiver transactions")
                    
                    all_transactions.extend(waiver_transactions)
                    
            except RateLimitError as e:
                logger.warning(f"Rate limited on waiver transactions for week {week}: {e}")
                rate_limited_weeks += 1
                raise  # Re-raise to trigger retry logic
            except Exception as e:
                logger.warning(f"Failed to fetch waiver transactions for week {week}: {e}")
                
        fetch_mode = "incremental" if incremental and last_fetch_ms else "full"
        logger.info(f"Total waiver transactions fetched ({fetch_mode}): {len(all_transactions)}")
        
        if rate_limited_weeks > 0:
            logger.warning(f"Rate limited on {rate_limited_weeks} weeks during waiver fetch")
        
        return all_transactions
    
    def fetch_free_agent_transactions(self, incremental: bool = True,
                                    last_fetch_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch free agent transactions with incremental support.
        
        Args:
            incremental: If True, only fetch transactions newer than last_fetch_timestamp
            last_fetch_timestamp: ISO timestamp of last fetch (for incremental mode)
            
        Returns:
            List of free agent transactions
            
        Raises:
            RateLimitError: If rate limits are exceeded
            APIError: If API calls fail after retries
        """
        logger.info("Fetching free agent transactions...")
        
        # Convert last_fetch_timestamp to milliseconds for comparison
        last_fetch_ms = None
        if incremental and last_fetch_timestamp:
            try:
                dt = datetime.fromisoformat(last_fetch_timestamp.replace('Z', '+00:00'))
                last_fetch_ms = int(dt.timestamp() * 1000)
                logger.info(f"Incremental fetch since: {dt} ({last_fetch_ms}ms)")
            except ValueError as e:
                logger.warning(f"Invalid last_fetch_timestamp format, performing full fetch: {e}")
                incremental = False
        
        all_transactions = []
        rate_limited_weeks = 0
        
        # Fetch transactions for each week
        for week in range(1, 19):
            try:
                url = f"{self.base_url}/league/{self.league_id}/transactions/{week}"
                transactions = fetch_with_retry(url)
                
                if transactions:
                    # Filter for free agent transactions only
                    fa_transactions = [t for t in transactions if t.get('type') == 'free_agent']
                    
                    # Add league_id to each transaction (required by cumulative file manager)
                    for txn in fa_transactions:
                        txn['league_id'] = self.league_id
                    
                    # Filter by timestamp if incremental
                    if incremental and last_fetch_ms:
                        new_transactions = []
                        for txn in fa_transactions:
                            txn_created = txn.get('created', 0)
                            if txn_created > last_fetch_ms:
                                new_transactions.append(txn)
                        fa_transactions = new_transactions
                        
                        if fa_transactions:
                            logger.info(f"Week {week}: Found {len(fa_transactions)} new free agent transactions since last fetch")
                    elif fa_transactions:
                        logger.info(f"Week {week}: Found {len(fa_transactions)} free agent transactions")
                    
                    all_transactions.extend(fa_transactions)
                    
            except RateLimitError as e:
                logger.warning(f"Rate limited on free agent transactions for week {week}: {e}")
                rate_limited_weeks += 1
                raise  # Re-raise to trigger retry logic
            except Exception as e:
                logger.warning(f"Failed to fetch free agent transactions for week {week}: {e}")
                
        fetch_mode = "incremental" if incremental and last_fetch_ms else "full"
        logger.info(f"Total free agent transactions fetched ({fetch_mode}): {len(all_transactions)}")
        
        if rate_limited_weeks > 0:
            logger.warning(f"Rate limited on {rate_limited_weeks} weeks during free agent fetch")
        
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
                    'sequence': -1,  # Use -1 to indicate no sequence (will be converted to None in JSON)
                    'priority': -1,  # Use -1 to indicate no priority (will be converted to None in JSON)
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


def process_waiver_wire_multi_season(force_full_refresh: bool = False) -> str:
    """
    Process waiver wire data for all active seasons using multi-season architecture.
    
    Args:
        force_full_refresh: If True, perform full refresh for all active seasons
        
    Returns:
        Path to cumulative waiver wire file
        
    Raises:
        APIError: If API calls fail after retries
        CumulativeFileError: If cumulative file operations fail
    """
    logger.info("Starting Stage 5: Waiver Wire Analysis (Multi-Season)")
    
    try:
        # Load season configuration
        season_config = get_season_config()
        active_seasons = season_config.get_active_seasons()
        
        if not active_seasons:
            logger.warning("No active seasons configured, nothing to fetch")
            return ""
        
        logger.info(f"Processing {len(active_seasons)} active seasons: {active_seasons}")
        
        # Initialize cumulative file manager
        cumulative_manager = CumulativeFileManager()
        cumulative_file = "waiver-wire.json"  # Cumulative waiver wire file
        
        # Initialize cumulative file if it doesn't exist
        if not cumulative_manager.initialize_cumulative_file(cumulative_file, "waiver-wire"):
            raise CumulativeFileError(f"Failed to initialize cumulative file: {cumulative_file}")
        
        total_new_transactions = 0
        total_duplicates = 0
        processed_seasons = []
        
        # Process each active season
        for season_name in active_seasons:
            try:
                logger.info(f"Processing waiver wire for season: {season_name}")
                
                # Validate season operation is allowed
                validate_season_operation(season_name, "fetch")
                
                # Get season info
                season_info = season_config.get_season_info(season_name)
                if not season_info:
                    logger.error(f"Season info not found: {season_name}")
                    continue
                
                league_id = season_info.league_id
                last_fetch = season_info.last_incremental_fetch
                
                # Determine if incremental fetch is possible
                incremental = not force_full_refresh and last_fetch is not None
                
                # Initialize processor for this season
                processor = WaiverWireProcessor(league_id, season_name)
                
                # Fetch waiver transactions
                waiver_transactions = processor.fetch_waiver_transactions(
                    incremental=incremental,
                    last_fetch_timestamp=last_fetch
                )
                
                # Fetch free agent transactions
                fa_transactions = processor.fetch_free_agent_transactions(
                    incremental=incremental,
                    last_fetch_timestamp=last_fetch
                )
                
                # Combine all transactions
                all_transactions = waiver_transactions + fa_transactions
                
                # Append to cumulative file if we have new transactions
                if all_transactions:
                    result = cumulative_manager.append_to_cumulative_file(
                        file_path=cumulative_file,
                        new_records=all_transactions,
                        season=season_name
                    )
                    
                    total_new_transactions += result['records_added']
                    total_duplicates += result['duplicates_skipped']
                    
                    logger.info(f"✓ {season_name}: {result['records_added']} new transactions, "
                               f"{result['duplicates_skipped']} duplicates")
                    
                    # Find the most recent transaction timestamp from newly added transactions
                    # This ensures incremental fetch uses the actual data timestamp, not script execution time
                    most_recent_txn_ms = max(txn.get('created', 0) for txn in all_transactions)
                    most_recent_dt = datetime.fromtimestamp(most_recent_txn_ms / 1000, tz=timezone.utc)
                    current_timestamp = most_recent_dt.isoformat()
                    
                    # Update last fetch timestamp in season config ONLY when we have new data
                    season_config.update_last_fetch_timestamp(season_name, current_timestamp)
                    logger.info(f"Updated last_fetch to most recent transaction: {current_timestamp}")
                else:
                    logger.info(f"✓ {season_name}: No new transactions, keeping existing last_fetch timestamp")
                    # Don't update timestamp - this prevents gaps when one stage has no data
                
                processed_seasons.append(season_name)
                
                # Save raw data for this season (for backward compatibility)
                season_waiver_file = f'waiver_transactions_raw_{season_name}.json'
                season_fa_file = f'free_agent_transactions_raw_{season_name}.json'
                
                with open(season_waiver_file, 'w') as f:
                    json.dump(waiver_transactions, f, indent=2)
                
                with open(season_fa_file, 'w') as f:
                    json.dump(fa_transactions, f, indent=2)
                
            except Exception as e:
                logger.error(f"Failed to process waiver wire for season {season_name}: {e}")
                # Continue with other seasons
                continue
        
        # Save updated season configuration
        season_config.save()
        
        # Create legacy output files for backward compatibility
        if processed_seasons:
            # Load cumulative data for processing
            try:
                with open(cumulative_file, 'r') as f:
                    cumulative_data = json.load(f)
                    all_waiver_transactions = cumulative_data.get('waiver-wire', [])
                
                # Separate waiver and free agent transactions
                waiver_only = [t for t in all_waiver_transactions if t.get('type') == 'waiver']
                fa_only = [t for t in all_waiver_transactions if t.get('type') == 'free_agent']
                
                # Save legacy format files
                with open('waiver_transactions_raw.json', 'w') as f:
                    json.dump(waiver_only, f, indent=2)
                
                with open('free_agent_transactions_raw.json', 'w') as f:
                    json.dump(fa_only, f, indent=2)
                
                # Process data for analysis (using first season's processor for compatibility)
                if processed_seasons:
                    first_season = processed_seasons[0]
                    season_info = season_config.get_season_info(first_season)
                    processor = WaiverWireProcessor(season_info.league_id, first_season)
                    
                    waiver_df = processor.process_waiver_transactions(waiver_only)
                    fa_df = processor.process_free_agent_transactions(fa_only)
                    
                    # Combine and save processed data
                    combined_df = pd.concat([waiver_df, fa_df], ignore_index=True)
                    combined_df.to_csv('waiver_wire_analysis.csv', index=False)
                    
                    # Generate analysis
                    analysis = processor.generate_waiver_analysis(waiver_df, fa_df)
                    
                    # Add multi-season metadata
                    analysis['multi_season_metadata'] = {
                        'processed_seasons': processed_seasons,
                        'total_new_transactions': total_new_transactions,
                        'total_duplicates': total_duplicates,
                        'fetch_mode': 'incremental' if not force_full_refresh else 'full'
                    }
                    
                    # Save analysis
                    with open('waiver_wire_summary.json', 'w') as f:
                        json.dump(analysis, f, indent=2, default=str)
                
            except Exception as e:
                logger.warning(f"Could not create legacy output files: {e}")
        
        # Create backup
        backup_manager = BackupManager()
        backup_manager.backup_file(cumulative_file, 'stage5_multi_season')
        
        # Display summary stats
        logger.info(f"📊 MULTI-SEASON WAIVER WIRE SUMMARY:")
        logger.info(f"  Processed seasons: {processed_seasons}")
        logger.info(f"  Total new transactions: {total_new_transactions}")
        logger.info(f"  Duplicates skipped: {total_duplicates}")
        
        logger.info("✓ Stage 5 Multi-Season completed successfully")
        
        return cumulative_file
        
    except Exception as e:
        logger.error(f"Stage 5 multi-season failed: {e}")
        raise


def main():
    """Main execution function with multi-season support."""
    import sys
    
    # Check for --full flag
    full_refresh = '--full' in sys.argv
    
    try:
        output_file = process_waiver_wire_multi_season(force_full_refresh=full_refresh)
        logger.info(f"✓ Output ready: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"❌ Stage 5 failed: {e}")
        raise


if __name__ == "__main__":
    main()