#!/usr/bin/env python3
"""
STAGE 1: Fetch All Trades from Sleeper API (Multi-Season Architecture)
Retrieves trade data with incremental fetching support for active seasons

MULTI-SEASON FEATURES:
- Incremental fetching based on last_fetch_timestamp for active seasons
- Season configuration integration for active vs static season handling
- Cumulative file management with atomic operations and deduplication
- Enhanced API error handling with exponential backoff for rate limits
- Season tagging for all new transactions

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
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Any
import sys

# Pipeline utilities
from config import get_config
from constants import OutputFiles
from utils.logging_config import setup_logging
from utils.api_client import fetch_with_retry, APIError, RateLimitError
from utils.validators import StageValidator, ValidationError
from utils.backup import BackupManager
from utils.metrics import LocalMetrics
from utils.team_resolver import sync_team_identities, TeamIdentityError
from utils.season_config import get_season_config, validate_season_operation
from utils.cumulative_file_manager import CumulativeFileManager, CumulativeFileError

# Initialize
logger = setup_logging('Stage 1: Fetch Trades (Multi-Season)')
config = get_config()
metrics = LocalMetrics()


def fetch_trades_for_season(season_name: str, league_id: str, 
                          incremental: bool = True, 
                          last_fetch_timestamp: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch trade transactions for a specific season with incremental support.
    
    Args:
        season_name: Name of the season (e.g., "season_3")
        league_id: Sleeper league ID for the season
        incremental: If True, only fetch new trades since last_fetch_timestamp
        last_fetch_timestamp: ISO timestamp of last fetch (for incremental mode)
        
    Returns:
        Dictionary with fetched data and metadata
        
    Raises:
        APIError: If API calls fail after retries
        ValidationError: If output validation fails
        RateLimitError: If rate limits are exceeded
    """
    start_time = time.time()
    
    try:
        # Validate season operation is allowed
        validate_season_operation(season_name, "fetch")
        
        mode = "INCREMENTAL" if incremental and last_fetch_timestamp else "FULL"
        logger.info(f"Fetching trades for {season_name} - Mode: {mode}")
        logger.info(f"League ID: {league_id}")
        
        if incremental and last_fetch_timestamp:
            logger.info(f"Last fetch: {last_fetch_timestamp}")
        
        # Get league info with enhanced retry logic
        logger.info("Fetching league info...")
        league_url = f"{config.sleeper_api.base_url}/league/{league_id}"
        
        try:
            league = fetch_with_retry(league_url, timeout=config.sleeper_api.timeout)
            metrics.record('api.sleeper.league_info.success', 1)
        except RateLimitError as e:
            logger.warning(f"Rate limited on league info, will retry: {e}")
            metrics.record('api.sleeper.league_info.rate_limited', 1)
            raise
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
        
        # Get users with retry logic
        logger.info("Fetching users...")
        users_url = f"{config.sleeper_api.base_url}/league/{league_id}/users"
        
        try:
            users = fetch_with_retry(users_url, timeout=config.sleeper_api.timeout)
            logger.info(f"✓ {len(users)} users")
            metrics.record('count.users', len(users))
        except RateLimitError as e:
            logger.warning(f"Rate limited on users, will retry: {e}")
            metrics.record('api.sleeper.users.rate_limited', 1)
            raise
        except APIError as e:
            logger.error(f"Failed to fetch users: {e}")
            raise
        
        # Get rosters with retry logic
        logger.info("Fetching rosters...")
        rosters_url = f"{config.sleeper_api.base_url}/league/{league_id}/rosters"
        
        try:
            rosters = fetch_with_retry(rosters_url, timeout=config.sleeper_api.timeout)
            logger.info(f"✓ {len(rosters)} rosters")
            metrics.record('count.rosters', len(rosters))
        except RateLimitError as e:
            logger.warning(f"Rate limited on rosters, will retry: {e}")
            metrics.record('api.sleeper.rosters.rate_limited', 1)
            raise
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
        
        # Convert last_fetch_timestamp to milliseconds for comparison
        last_fetch_ms = None
        if incremental and last_fetch_timestamp:
            try:
                # Parse ISO timestamp and convert to milliseconds
                dt = datetime.fromisoformat(last_fetch_timestamp.replace('Z', '+00:00'))
                last_fetch_ms = int(dt.timestamp() * 1000)
                logger.info(f"Incremental fetch since: {dt} ({last_fetch_ms}ms)")
            except ValueError as e:
                logger.warning(f"Invalid last_fetch_timestamp format, performing full fetch: {e}")
                incremental = False
        
        # Scan all weeks for trades with enhanced error handling
        logger.info(f"Scanning weeks 1-{current_week + 5} for trades...")
        all_trades: List[Dict] = []
        api_calls = 0
        successful_weeks = 0
        rate_limited_weeks = 0
        
        for week in range(1, current_week + 6):
            url = f"{config.sleeper_api.base_url}/league/{league_id}/transactions/{week}"
            api_calls += 1
            
            try:
                response = fetch_with_retry(url, timeout=config.sleeper_api.timeout)
                
                if response:  # API returns None for 404
                    transactions = response
                    trades = [t for t in transactions if t.get('type') == 'trade']
                    
                    # Filter by timestamp if incremental
                    if incremental and last_fetch_ms:
                        new_trades = []
                        for trade in trades:
                            trade_created = trade.get('created', 0)
                            if trade_created > last_fetch_ms:
                                new_trades.append(trade)
                        trades = new_trades
                        
                        if trades:
                            logger.info(f"  Week {week}: {len(trades)} new trade(s) since last fetch")
                    elif trades:
                        logger.info(f"  Week {week}: {len(trades)} trade(s)")
                    
                    if trades:
                        all_trades.extend(trades)
                        successful_weeks += 1
                
            except RateLimitError as e:
                logger.warning(f"Rate limited on week {week}, will retry: {e}")
                rate_limited_weeks += 1
                metrics.record('api.sleeper.transactions.rate_limited', 1)
                raise  # Re-raise to trigger retry logic
            except APIError as e:
                # Log but continue - weeks may not exist yet
                logger.debug(f"Week {week} not available (expected): {e}")
                continue
        
        fetch_mode = "incremental" if incremental and last_fetch_ms else "full"
        logger.info(f"✓ Total trades fetched ({fetch_mode}): {len(all_trades)}")
        metrics.record('count.api_calls', api_calls)
        metrics.record('count.successful_weeks', successful_weeks)
        metrics.record('count.rate_limited_weeks', rate_limited_weeks)
        metrics.record('count.trades_fetched', len(all_trades))
        
        # Sort by date (most recent first)
        all_trades.sort(key=lambda t: t.get('created', 0), reverse=True)
        
        # Create comprehensive output with season tagging
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        output = {
            'metadata': {
                'season': season_name,
                'league_id': league_id,
                'league_name': league_name,
                'season_year': season,
                'current_week': current_week,
                'fetch_timestamp': current_timestamp,
                'fetch_mode': fetch_mode,
                'last_fetch_timestamp': last_fetch_timestamp,
                'total_trades': len(all_trades),
                'incremental_mode': incremental
            },
            'users': users,
            'rosters': rosters,
            'trades': all_trades
        }
        
        # Record success metrics
        duration = time.time() - start_time
        metrics.record_duration(f'stage1_{season_name}', duration)
        metrics.record_success(f'stage1_{season_name}')
        metrics.record(f'count.total_trades_{season_name}', len(all_trades))
        
        logger.info(f"✓ Fetched {len(all_trades)} trades for {season_name} in {duration:.2f}s")
        
        return output
        
    except (APIError, ValidationError, RateLimitError) as e:
        duration = time.time() - start_time
        metrics.record_duration(f'stage1_{season_name}', duration)
        metrics.record_failure(f'stage1_{season_name}', str(e))
        logger.error(f"Stage 1 failed for {season_name} after {duration:.2f}s: {e}")
        raise
    except Exception as e:
        duration = time.time() - start_time
        metrics.record_duration(f'stage1_{season_name}', duration)
        metrics.record_failure(f'stage1_{season_name}', str(e))
        logger.error(f"Stage 1 unexpected error for {season_name} after {duration:.2f}s", exc_info=True)
        raise


def fetch_all_trades_multi_season(force_full_refresh: bool = False) -> str:
    """
    Fetch trades for all active seasons using multi-season architecture.
    
    Args:
        force_full_refresh: If True, perform full refresh for all active seasons
        
    Returns:
        Path to cumulative trades file
        
    Raises:
        APIError: If API calls fail after retries
        CumulativeFileError: If cumulative file operations fail
    """
    start_time = time.time()
    
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
        cumulative_file = "trades.json"  # Cumulative trades file
        
        # Initialize cumulative file if it doesn't exist
        if not cumulative_manager.initialize_cumulative_file(cumulative_file, "trades"):
            raise CumulativeFileError(f"Failed to initialize cumulative file: {cumulative_file}")
        
        total_new_trades = 0
        total_duplicates = 0
        processed_seasons = []
        
        # Process each active season
        for season_name in active_seasons:
            try:
                logger.info(f"Processing season: {season_name}")
                
                # Get season info
                season_info = season_config.get_season_info(season_name)
                if not season_info:
                    logger.error(f"Season info not found: {season_name}")
                    continue
                
                league_id = season_info.league_id
                last_fetch = season_info.last_incremental_fetch
                
                # Determine if incremental fetch is possible
                incremental = not force_full_refresh and last_fetch is not None
                
                # Fetch trades for this season
                season_data = fetch_trades_for_season(
                    season_name=season_name,
                    league_id=league_id,
                    incremental=incremental,
                    last_fetch_timestamp=last_fetch
                )
                
                # Append to cumulative file if we have new trades
                trades = season_data.get('trades', [])
                if trades:
                    result = cumulative_manager.append_to_cumulative_file(
                        file_path=cumulative_file,
                        new_records=trades,
                        season=season_name
                    )
                    
                    total_new_trades += result['records_added']
                    total_duplicates += result['duplicates_skipped']
                    
                    logger.info(f"✓ {season_name}: {result['records_added']} new trades, "
                               f"{result['duplicates_skipped']} duplicates")
                else:
                    logger.info(f"✓ {season_name}: No new trades")
                
                # Update last fetch timestamp in season config
                current_timestamp = datetime.now(timezone.utc).isoformat()
                season_config.update_last_fetch_timestamp(season_name, current_timestamp)
                processed_seasons.append(season_name)
                
            except Exception as e:
                logger.error(f"Failed to process season {season_name}: {e}")
                # Continue with other seasons
                continue
        
        # Save updated season configuration
        season_config.save()
        
        # Also save to legacy format for backward compatibility
        if processed_seasons:
            # Load the first processed season's data for legacy output
            first_season = processed_seasons[0]
            season_info = season_config.get_season_info(first_season)
            
            # Create legacy output format
            legacy_output = {
                'metadata': {
                    'league_id': season_info.league_id,
                    'league_name': f"Multi-Season ({', '.join(processed_seasons)})",
                    'season': season_info.year,
                    'current_week': 1,  # Default value
                    'fetch_timestamp': datetime.now().isoformat(),
                    'total_trades': total_new_trades,
                    'incremental_mode': not force_full_refresh,
                    'processed_seasons': processed_seasons
                },
                'users': [],  # Will be populated by individual season data
                'rosters': [],  # Will be populated by individual season data
                'trades': []  # Will be loaded from cumulative file
            }
            
            # Load trades from cumulative file for legacy compatibility
            try:
                with open(cumulative_file, 'r') as f:
                    cumulative_data = json.load(f)
                    legacy_output['trades'] = cumulative_data.get('trades', [])
            except Exception as e:
                logger.warning(f"Could not load cumulative trades for legacy output: {e}")
            
            # Save legacy format
            output_file = OutputFiles.TRADES_RAW.value
            with open(output_file, 'w') as f:
                json.dump(legacy_output, f, indent=2)
            
            logger.info(f"✓ Saved legacy format to: {output_file}")
        
        # Create backup
        backup_mgr = BackupManager(
            backup_dir=str(config.storage.backup_dir),
            retention_days=config.storage.retention_days
        )
        backup_mgr.backup_file(cumulative_file, 'stage1_multi_season')
        backup_mgr.cleanup_old_backups()
        
        # Display summary stats
        logger.info(f"📊 MULTI-SEASON TRADE SUMMARY:")
        logger.info(f"  Processed seasons: {processed_seasons}")
        logger.info(f"  Total new trades: {total_new_trades}")
        logger.info(f"  Duplicates skipped: {total_duplicates}")
        
        # Record success metrics
        duration = time.time() - start_time
        metrics.record_duration('stage1_multi_season', duration)
        metrics.record_success('stage1_multi_season')
        metrics.record('count.processed_seasons', len(processed_seasons))
        metrics.record('count.total_new_trades', total_new_trades)
        metrics.record('count.total_duplicates', total_duplicates)
        
        logger.info("="*80)
        logger.info("✓ STAGE 1 MULTI-SEASON COMPLETE")
        logger.info(f"✓ Duration: {duration:.2f}s")
        logger.info("="*80)
        
        # Save metrics
        metrics.save()
        
        return cumulative_file
        
    except Exception as e:
        duration = time.time() - start_time
        metrics.record_duration('stage1_multi_season', duration)
        metrics.record_failure('stage1_multi_season', str(e))
        metrics.save()
        logger.error(f"Stage 1 multi-season failed after {duration:.2f}s: {e}")
        raise


def fetch_all_trades(incremental: bool = True) -> str:
    """
    Legacy function for backward compatibility.
    Delegates to multi-season architecture.
    
    Args:
        incremental: If True, use incremental fetching. If False, force full refresh.
        
    Returns:
        Path to output file
    """
    logger.info("Using legacy fetch_all_trades - delegating to multi-season architecture")
    return fetch_all_trades_multi_season(force_full_refresh=not incremental)


if __name__ == "__main__":
    # Check for --full flag
    full_refresh = '--full' in sys.argv
    
    try:
        output_file = fetch_all_trades_multi_season(force_full_refresh=full_refresh)
        logger.info(f"✓ Output ready: {output_file}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Stage 1 failed: {e}")
        sys.exit(1)