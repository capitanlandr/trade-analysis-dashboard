#!/usr/bin/env python3
"""
STAGE 1: Fetch All Trades from Sleeper API
Retrieves complete trade data and saves to trades_raw.json

IMPROVEMENTS:
- Structured logging with JSON output
- Retry logic with exponential backoff
- Configuration management (no hardcoded values)
- Pre/post validation (fail-fast)
- Automatic backups with retention
- Metrics collection
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Set, Optional
import sys

# Pipeline utilities
from config import get_config
from constants import OutputFiles
from utils.logging_config import setup_logging
from utils.api_client import fetch_with_retry, APIError
from utils.validators import StageValidator, ValidationError
from utils.backup import BackupManager
from utils.metrics import LocalMetrics
from utils.team_resolver import sync_team_identities, TeamIdentityError

# Initialize
logger = setup_logging('Stage 1: Fetch Trades')
config = get_config()
metrics = LocalMetrics()


def fetch_all_trades(incremental: bool = True) -> str:
    """
    Fetch trade transactions from Sleeper API.
    
    Args:
        incremental: If True, only fetch new trades. If False, fetch all trades.
        
    Returns:
        Path to output file
        
    Raises:
        APIError: If API calls fail after retries
        ValidationError: If output validation fails
    """
    start_time = time.time()
    
    try:
        # Validate prerequisites
        StageValidator.validate_stage1_prerequisites(config.league_id)
        
        mode = "INCREMENTAL (append new trades only)" if incremental else "FULL REFRESH (fetch all trades)"
        logger.info(f"Mode: {mode}")
        logger.info(f"League ID: {config.league_id}")
        
        # Load existing data if incremental
        existing_data = None
        existing_trade_ids: Set[str] = set()
        
        if incremental:
            try:
                with open(OutputFiles.TRADES_RAW.value, 'r') as f:
                    existing_data = json.load(f)
                    existing_trade_ids = {t['transaction_id'] for t in existing_data.get('trades', [])}
                    logger.info(f"✓ Loaded {len(existing_trade_ids)} existing trades from cache")
            except FileNotFoundError:
                logger.warning("No existing cache found, performing full fetch")
                incremental = False
        
        # Get league info
        logger.info("Fetching league info...")
        league_url = f"{config.sleeper_api.base_url}/league/{config.league_id}"
        
        try:
            league = fetch_with_retry(league_url, timeout=config.sleeper_api.timeout)
            metrics.record('api.sleeper.league_info.success', 1)
        except APIError as e:
            logger.error(f"Failed to fetch league info: {e}")
            metrics.record('api.sleeper.league_info.error', 1)
            raise
        
        season = league.get('season')
        league_name = league.get('name')
        current_week = league.get('settings', {}).get('leg', 1)
        
        logger.info(f"✓ League: {league_name}")
        logger.info(f"✓ Season: {season}")
        logger.info(f"✓ Current week: {current_week}")
        
        # Get users
        logger.info("Fetching users...")
        users_url = f"{config.sleeper_api.base_url}/league/{config.league_id}/users"
        
        try:
            users = fetch_with_retry(users_url, timeout=config.sleeper_api.timeout)
            logger.info(f"✓ {len(users)} users")
            metrics.record('count.users', len(users))
        except APIError as e:
            logger.error(f"Failed to fetch users: {e}")
            raise
        
        # Get rosters
        logger.info("Fetching rosters...")
        rosters_url = f"{config.sleeper_api.base_url}/league/{config.league_id}/rosters"
        
        try:
            rosters = fetch_with_retry(rosters_url, timeout=config.sleeper_api.timeout)
            logger.info(f"✓ {len(rosters)} rosters")
            metrics.record('count.rosters', len(rosters))
        except APIError as e:
            logger.error(f"Failed to fetch rosters: {e}")
            raise
        
        # Sync team identities (keep mapping current)
        try:
            logger.info("Syncing team identities...")
            updates = sync_team_identities(rosters, users, OutputFiles.TEAM_IDENTITY_MAPPING.value)
            if updates > 0:
                logger.info(f"✓ Updated {updates} team name(s)")
                metrics.record('count.team_name_updates', updates)
            else:
                logger.info(f"✓ Team names current (no changes)")
        except TeamIdentityError as e:
            # Log warning but don't fail - team identity is not critical for stage 1
            logger.warning(f"Team identity sync failed (non-critical): {e}")
            metrics.record('warning.team_identity_sync_failed', 1)
        
        # Scan all weeks for trades
        logger.info(f"Scanning weeks 1-{current_week + 5} for trades...")
        all_trades: List[Dict] = []
        api_calls = 0
        successful_weeks = 0
        
        for week in range(1, current_week + 6):
            url = f"{config.sleeper_api.base_url}/league/{config.league_id}/transactions/{week}"
            api_calls += 1
            
            try:
                response = fetch_with_retry(url, timeout=config.sleeper_api.timeout)
                
                if response:  # API returns None for 404
                    transactions = response
                    trades = [t for t in transactions if t.get('type') == 'trade']
                    
                    if trades:
                        all_trades.extend(trades)
                        successful_weeks += 1
                        logger.info(f"  Week {week}: {len(trades)} trade(s)")
                
            except APIError as e:
                # Log but continue - weeks may not exist yet
                logger.debug(f"Week {week} not available (expected): {e}")
                continue
        
        logger.info(f"✓ Total trades fetched from API: {len(all_trades)}")
        metrics.record('count.api_calls', api_calls)
        metrics.record('count.successful_weeks', successful_weeks)
        metrics.record('count.trades_fetched', len(all_trades))
        
        # Filter to new trades only if incremental
        if incremental and existing_trade_ids:
            new_trades = [t for t in all_trades if t['transaction_id'] not in existing_trade_ids]
            logger.info(f"✓ New trades not in cache: {len(new_trades)}")
            metrics.record('count.new_trades', len(new_trades))
            
            if existing_data and new_trades:
                # Append new trades to existing
                all_trades = existing_data['trades'] + new_trades
                logger.info(f"✓ Total trades after merge: {len(all_trades)}")
            elif existing_data:
                # No new trades
                all_trades = existing_data['trades']
                logger.info(f"✓ No new trades, using existing {len(all_trades)} trades")
        
        # Sort by date (most recent first)
        all_trades.sort(key=lambda t: t.get('created', 0), reverse=True)
        
        # Create comprehensive output
        output = {
            'metadata': {
                'league_id': config.league_id,
                'league_name': league_name,
                'season': season,
                'current_week': current_week,
                'fetch_timestamp': datetime.now().isoformat(),
                'total_trades': len(all_trades),
                'incremental_mode': incremental
            },
            'users': users,
            'rosters': rosters,
            'trades': all_trades
        }
        
        # Save to file
        output_file = OutputFiles.TRADES_RAW.value
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"✓ Saved {len(all_trades)} trades to: {output_file}")
        logger.info(f"✓ Includes full metadata: users, rosters, league info")
        
        # Create backup
        backup_mgr = BackupManager(
            backup_dir=str(config.storage.backup_dir),
            retention_days=config.storage.retention_days
        )
        backup_mgr.backup_file(output_file, 'stage1')
        backup_mgr.cleanup_old_backups()
        
        # Validate output
        StageValidator.validate_stage1_output(output_file)
        
        # Display summary stats
        if all_trades:
            earliest = datetime.fromtimestamp(min(t['created'] for t in all_trades)/1000)
            latest = datetime.fromtimestamp(max(t['created'] for t in all_trades)/1000)
            
            logger.info(f"📊 TRADE SUMMARY:")
            logger.info(f"  Date range: {earliest.strftime('%Y-%m-%d')} to {latest.strftime('%Y-%m-%d')}")
            
            # Count statuses
            statuses = {}
            for t in all_trades:
                status = t.get('status', 'unknown')
                statuses[status] = statuses.get(status, 0) + 1
            
            logger.info(f"  Statuses: {dict(statuses)}")
            metrics.record('count.trades_by_status', statuses)
            
            # Count 2-team vs multi-team
            two_team = len([t for t in all_trades if len(t.get('roster_ids', [])) == 2])
            multi_team = len([t for t in all_trades if len(t.get('roster_ids', [])) > 2])
            
            logger.info(f"  2-team trades: {two_team}")
            logger.info(f"  Multi-team trades: {multi_team}")
            metrics.record('count.two_team_trades', two_team)
            metrics.record('count.multi_team_trades', multi_team)
        
        # Record success metrics
        duration = time.time() - start_time
        metrics.record_duration('stage1', duration)
        metrics.record_success('stage1')
        metrics.record('count.total_trades', len(all_trades))
        
        logger.info("="*80)
        logger.info("✓ STAGE 1 COMPLETE")
        logger.info(f"✓ Duration: {duration:.2f}s")
        logger.info("="*80)
        
        # Save metrics
        metrics.save()
        
        return output_file
        
    except (APIError, ValidationError) as e:
        duration = time.time() - start_time
        metrics.record_duration('stage1', duration)
        metrics.record_failure('stage1', str(e))
        metrics.save()
        logger.error(f"Stage 1 failed after {duration:.2f}s: {e}")
        raise
    except Exception as e:
        duration = time.time() - start_time
        metrics.record_duration('stage1', duration)
        metrics.record_failure('stage1', str(e))
        metrics.save()
        logger.error(f"Stage 1 unexpected error after {duration:.2f}s", exc_info=True)
        raise


if __name__ == "__main__":
    # Check for --full flag
    full_refresh = '--full' in sys.argv
    
    try:
        output_file = fetch_all_trades(incremental=not full_refresh)
        logger.info(f"✓ Output ready: {output_file}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Stage 1 failed: {e}")
        sys.exit(1)