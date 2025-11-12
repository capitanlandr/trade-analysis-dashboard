#!/usr/bin/env python3
"""
STAGE 3: Cache Asset Values
Fetches historical and current values for all traded assets
Applies tiered 2025 pick valuations and 2026+ projections
Uses static pick origin mapping (not Sleeper API's confused roster_id)

IMPROVEMENTS:
- Structured logging
- Retry logic for Git API calls
- Configuration management
- Pre/post validation
- Automatic backups
- Metrics collection
- Better error handling
"""

import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sys

# Pipeline utilities
from config import get_config
from constants import (OutputFiles, PickTier, DRAFT_COMPLETION_DATE, 
                      FAAB_VALUE_PER_DOLLAR, ROUND_ORDINALS, SEASON_START_DATE)
from utils.logging_config import setup_logging
from utils.api_client import fetch_with_retry, APIError
from utils.validators import StageValidator, ValidationError
from utils.backup import BackupManager
from utils.metrics import LocalMetrics
from pick_origin_mapping import get_pick_origin_owner

# Initialize
logger = setup_logging('Stage 3: Cache Values')
config = get_config()
metrics = LocalMetrics()

# Auto-update weekly projections before loading
logger.info("Checking for missing weekly projection columns...")
try:
    from scripts.update_weekly_projections import update_weekly_projections
    updated = update_weekly_projections()
    if updated:
        logger.info("✓ Weekly projections updated with missing columns")
    else:
        logger.info("✓ Weekly projections are current")
except Exception as e:
    logger.warning(f"Failed to auto-update projections: {e}")
    logger.info("Continuing with existing projections file...")

# Load supporting data
logger.info("Loading supporting data...")
try:
    PICK_PROJECTIONS = pd.read_csv('weekly_2026_pick_projections_expanded.csv')
    DRAFT_RESULTS = pd.read_csv('sleeper_rookie_draft_2025.csv')
    logger.info("✓ Loaded EXPANDED projections (1st/2nd/3rd/4th) and draft results")
    logger.info("✓ Using static pick origin mapping from pick_origin_mapping.py")
    metrics.record('count.projections_loaded', len(PICK_PROJECTIONS))
    metrics.record('count.draft_results_loaded', len(DRAFT_RESULTS))
except FileNotFoundError as e:
    logger.error(f"Required data file not found: {e}")
    raise ValidationError(f"Missing required file: {e}")

# Create pick lineage using CORRECTED origins from static mapping
PICK_LINEAGE = {}

for _, row in DRAFT_RESULTS.iterrows():
    round_num = row['Round']
    pick_in_round = row['Pick in Round']
    final_owner = row['Owner']
    player = row['Player']
    
    # Get CORRECT origin from static mapping
    origin_owner = get_pick_origin_owner(round_num, pick_in_round)
    
    key = (origin_owner, round_num)
    
    # Handle multiple picks from same origin in same round
    if key not in PICK_LINEAGE:
        PICK_LINEAGE[key] = []
    
    PICK_LINEAGE[key].append({
        'final_owner': final_owner,
        'pick_in_round': pick_in_round,
        'player': player,
        'overall_pick': row['Pick']
    })

logger.info(f"✓ Built pick lineage for {sum(len(v) for v in PICK_LINEAGE.values())} picks")
logger.info(f"✓ {len(PICK_LINEAGE)} unique (origin, round) combinations")
metrics.record('count.pick_lineage_entries', len(PICK_LINEAGE))


def get_all_commits_since(since_date: datetime) -> Dict[str, str]:
    """
    Get Git commits for historical values with retry logic.
    
    Args:
        since_date: Earliest date to fetch commits for
        
    Returns:
        Dictionary mapping date strings to commit SHAs
    """
    url = f"{config.github_api.base_url}/repos/{config.github_api.repo}/commits"
    params = {
        'path': config.github_api.values_path,
        'since': since_date.strftime('%Y-%m-%dT00:00:00Z'),
        'per_page': 100
    }
    
    try:
        commits = fetch_with_retry(url, timeout=config.github_api.timeout, params=params)
        
        if commits and isinstance(commits, list):
            commit_map = {c['commit']['committer']['date'][:10]: c['sha'] for c in commits}
            logger.info(f"✓ Fetched {len(commit_map)} Git commits")
            metrics.record('count.git_commits_fetched', len(commit_map))
            metrics.record('api.github.commits.success', 1)
            return commit_map
        
        logger.warning("No commits returned from GitHub API")
        metrics.record('api.github.commits.empty', 1)
        return {}
        
    except APIError as e:
        logger.error(f"Failed to fetch Git commits: {e}")
        metrics.record('api.github.commits.error', 1)
        # Return empty dict to use current values as fallback
        return {}


def get_available_weeks(team_row: pd.DataFrame, round_name: str) -> List[int]:
    """
    Get all available week numbers for team/round combination.
    
    Args:
        team_row: DataFrame row for specific team
        round_name: Round name ('1st', '2nd', '3rd', '4th')
        
    Returns:
        List of available week numbers, sorted
    """
    import re
    available_weeks = []
    pattern = f'Week(\\d+)_2026_{round_name}'
    
    for col in team_row.columns:
        match = re.match(pattern, col)
        if match:
            week_num = int(match.group(1))
            available_weeks.append(week_num)
    
    return sorted(available_weeks)


def get_best_week_column(team_row: pd.DataFrame, round_name: str, target_week: int) -> Tuple[str, int]:
    """
    Select best available week column for target week.
    
    Args:
        team_row: DataFrame row for specific team
        round_name: Round name ('1st', '2nd', '3rd', '4th')
        target_week: Desired week number
        
    Returns:
        Tuple of (column_name, selected_week)
        
    Raises:
        ValueError: If no weekly columns found
    """
    available_weeks = get_available_weeks(team_row, round_name)
    
    if not available_weeks:
        raise ValueError(f"No weekly columns found for {round_name}")
    
    # Strategy 1: Exact match
    if target_week in available_weeks:
        selected_week = target_week
    
    # Strategy 2: Latest available week <= target week
    # (Use most recent projection that's not from the future)
    elif any(w <= target_week for w in available_weeks):
        selected_week = max(w for w in available_weeks if w <= target_week)
    
    # Strategy 3: Earliest available week (fallback for early season trades)
    else:
        selected_week = min(available_weeks)
    
    column_name = f'Week{selected_week}_2026_{round_name}'
    return column_name, selected_week


def get_latest_week_column(team_row: pd.DataFrame, round_name: str) -> Tuple[str, int]:
    """
    Get the latest available week column for 2027/2028 picks.
    
    Args:
        team_row: DataFrame row for specific team
        round_name: Round name ('1st', '2nd', '3rd', '4th')
        
    Returns:
        Tuple of (column_name, latest_week)
        
    Raises:
        ValueError: If no weekly columns found
    """
    available_weeks = get_available_weeks(team_row, round_name)
    
    if not available_weeks:
        raise ValueError(f"No weekly columns found for {round_name}")
    
    latest_week = max(available_weeks)
    column_name = f'Week{latest_week}_2026_{round_name}'
    return column_name, latest_week


def get_values_from_commit(commit_sha: str, cache: Dict = {}) -> Optional[pd.DataFrame]:
    """
    Fetch values from Git commit with caching and retry logic.
    
    Args:
        commit_sha: Git commit SHA
        cache: In-memory cache of loaded commits
        
    Returns:
        DataFrame of values or None if fetch fails
    """
    if commit_sha in cache:
        return cache[commit_sha]
    
    url = f"https://raw.githubusercontent.com/{config.github_api.repo}/{commit_sha}/{config.github_api.values_path}"
    
    try:
        # Use pandas to read CSV directly from URL
        df = pd.read_csv(url)
        cache[commit_sha] = df
        logger.debug(f"✓ Loaded values from commit {commit_sha[:7]}")
        metrics.record('api.github.values.success', 1)
        return df
    except Exception as e:
        logger.warning(f"Failed to load values from commit {commit_sha[:7]}: {e}")
        metrics.record('api.github.values.error', 1)
        return None


def get_2025_pick_value(
    pick_name: str,
    origin_owner: str,
    trade_date: str,
    df_values: pd.DataFrame,
    is_current: bool
) -> Tuple[float, str, Optional[Dict]]:
    """
    Get value for 2025 picks using exact Git pick values.
    
    Pre-draft trades:
    - value_at_trade: Use exact "2025 Pick X.YY" value from Git
    - value_current: Use drafted player's current value
    
    Post-draft trades:
    - Both values use player value
    
    Args:
        pick_name: Pick identifier (e.g., "2025 Round 1")
        origin_owner: Original team that owned the pick
        trade_date: Trade date in YYYY-MM-DD format
        df_values: DataFrame with values
        is_current: True for current value, False for historical
        
    Returns:
        Tuple of (value, source_description, metadata_dict)
    """
    # Extract round number
    try:
        round_num = int(pick_name.split('Round')[1].strip())
    except:
        logger.warning(f"Failed to parse round from: {pick_name}")
        return 0, "Parse error", None
    
    trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
    
    # Look up pick lineage (may have multiple if origin had multiple picks in round)
    key = (origin_owner, round_num)
    lineage_list = PICK_LINEAGE.get(key, [])
    
    if not lineage_list:
        logger.warning(f"No lineage found for {origin_owner} Round {round_num}")
        return 0, "No lineage", None
    
    # For now, use first match (will need better logic for multiple picks)
    lineage = lineage_list[0]
    player = lineage['player']
    pick_in_round = lineage['pick_in_round']
    
    # Pre-draft trade
    if trade_dt < DRAFT_COMPLETION_DATE:
        if is_current:
            # Use player's current value
            player_matches = df_values[df_values['player'].str.contains(player, case=False, na=False)]
            if not player_matches.empty:
                value = player_matches.iloc[0]['value_2qb']
                return value, f"Player:{player}", {'player': player, 'pick_position': f"{round_num}.{pick_in_round:02d}"}
            logger.warning(f"Player not found in current values: {player}")
            return 0, f"Player not found:{player}", None
        else:
            # Use EXACT pick value from Git
            exact_pick = f"2025 Pick {round_num}.{pick_in_round:02d}"
            matches = df_values[df_values['player'].str.contains(exact_pick, case=False, na=False)]
            
            if not matches.empty:
                value = matches.iloc[0]['value_2qb']
                return value, f"Git:{exact_pick}", {'pick_exact': exact_pick}
            
            # Fallback to tier system if exact not found
            if round_num == 1:
                tier_value = PickTier.get_value(pick_in_round)
                tier_name = PickTier.get_tier_name(pick_in_round)
                return tier_value, f"Tier:{tier_name} 1st", {'tier': tier_name, 'pick_position': f"{round_num}.{pick_in_round:02d}"}
            else:
                # For 2nd/3rd/4th, try generic as last resort
                ordinal = ROUND_ORDINALS.get(round_num, f'{round_num}th')
                search = f"2026 {ordinal}"
                matches = df_values[df_values['player'].str.contains(search, case=False, na=False)]
                if not matches.empty:
                    value = matches.iloc[0]['value_2qb']
                    return value, f"Fallback:Generic {ordinal}", None
                return 0, f"Not found", None
    else:
        # Post-draft trade - both use player value
        player_matches = df_values[df_values['player'].str.contains(player, case=False, na=False)]
        if not player_matches.empty:
            value = player_matches.iloc[0]['value_2qb']
            return value, f"Player:{player} (post-draft)", {'player': player}
        return 0, f"Player not found:{player}", None


def get_2026_plus_pick_value(
    pick_name: str,
    origin_owner: str,
    trade_date: str,
    df_values: pd.DataFrame
) -> Tuple[float, str, Optional[Dict]]:
    """
    Get value for 2026+ picks with team-specific projections.
    
    Args:
        pick_name: Pick identifier (e.g., "2026 Round 1")
        origin_owner: Original team that owned the pick
        trade_date: Trade date in YYYY-MM-DD format
        df_values: DataFrame with values
        
    Returns:
        Tuple of (value, source_description, metadata_dict)
    """
    trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
    
    # Extract round number
    parts = pick_name.split()
    if len(parts) >= 3 and parts[1] == 'Round':
        year = parts[0]
        round_num = parts[2]
    else:
        return 0, "Parse error", None
    
    # 2026 picks with team projections (1st/2nd/3rd/4th)
    if '2026' in pick_name and origin_owner:
        # Determine week for time-based projections (unlimited)
        days = (trade_dt - SEASON_START_DATE).days
        week = max(2, (days // 7) + 1)  # Remove artificial Week 7 cap
        
        # Map round number to round name
        round_name = ROUND_ORDINALS.get(int(round_num))
        
        if round_name:
            # Find team in projections
            team_row = PICK_PROJECTIONS[PICK_PROJECTIONS['Team'] == origin_owner]
            if not team_row.empty:
                try:
                    # Use dynamic column discovery to find best available week
                    column_name, selected_week = get_best_week_column(team_row, round_name, week)
                    value = team_row.iloc[0][column_name]
                    
                    # Enhanced metadata with target vs actual week
                    metadata = {
                        'week': selected_week,
                        'target_week': week,
                        'origin': origin_owner,
                        'round': round_name,
                        'column_used': column_name
                    }
                    
                    return value, f"Projection:Week{selected_week}_{round_name}", metadata
                    
                except ValueError as e:
                    # Fallback if no columns found - continue to generic values
                    logger.warning(f"No weekly columns for {origin_owner} {round_name}: {e}")
                    pass
    
    # 2027/2028+ picks - use latest available 2026 projection as proxy
    if ('2027' in pick_name or '2028' in pick_name) and origin_owner:
        round_name = ROUND_ORDINALS.get(int(round_num))
        
        if round_name:
            team_row = PICK_PROJECTIONS[PICK_PROJECTIONS['Team'] == origin_owner]
            if not team_row.empty:
                try:
                    # Use dynamic latest week detection for future picks
                    column_name, latest_week = get_latest_week_column(team_row, round_name)
                    value = team_row.iloc[0][column_name]
                    
                    metadata = {
                        'origin': origin_owner,
                        'round': round_name,
                        'latest_week_used': latest_week,
                        'column_used': column_name
                    }
                    
                    return value, f"Projection:Week{latest_week}_2026_{round_name}", metadata
                    
                except ValueError as e:
                    # Fallback if no columns found - continue to generic values
                    logger.warning(f"No weekly columns for {origin_owner} {round_name}: {e}")
                    pass
    
    # Fallback - generic value from DynastyProcess
    ordinal = ROUND_ORDINALS.get(int(round_num), f'{round_num}th')
    search = f"{year} {ordinal}"
    
    matches = df_values[df_values['player'].str.contains(search, case=False, na=False)]
    if not matches.empty:
        value = matches.iloc[0]['value_2qb']
        return value, f"Fallback:Generic:{search}", None
    
    return 0, "Not found", None


def cache_asset_values(df_assets: pd.DataFrame) -> List[Dict]:
    """
    Cache values for all assets with historical and current valuations.
    
    Args:
        df_assets: DataFrame of asset transactions
        
    Returns:
        List of cached value dictionaries
    """
    logger.info("="*80)
    logger.info("CACHING ASSET VALUES")
    logger.info("="*80)
    
    # Load current values
    logger.info("Loading current DynastyProcess values...")
    try:
        df_current = pd.read_csv("https://github.com/dynastyprocess/data/raw/master/files/values.csv")
        scrape_date = df_current['scrape_date'].iloc[0]
        logger.info(f"✓ Current values (scraped: {scrape_date})")
        metrics.record('count.current_values_loaded', len(df_current))
    except Exception as e:
        logger.error(f"Failed to load current values: {e}")
        raise APIError(f"Cannot load DynastyProcess values: {e}")
    
    # Get earliest trade date for Git history
    earliest_date = pd.to_datetime(df_assets['trade_date']).min()
    logger.info(f"Fetching Git history since {earliest_date.strftime('%Y-%m-%d')}...")
    
    commit_cache = get_all_commits_since(earliest_date - timedelta(days=config.validation.git_commit_search_days))
    logger.info(f"✓ Loaded {len(commit_cache)} commits")
    
    # Cache for loaded Git DataFrames
    git_df_cache = {}
    
    # Process each asset transaction
    logger.info(f"Caching values for {len(df_assets)} asset transactions...")
    
    cached_values = []
    zero_value_count = 0
    
    for idx, row in df_assets.iterrows():
        asset_name = row['asset_name']
        asset_type = row['asset_type']
        trade_date = row['trade_date']
        origin_owner = row['origin_owner']
        
        if (idx + 1) % 50 == 0:
            logger.info(f"  Processed {idx + 1}/{len(df_assets)}...")
        
        # Handle FAAB
        if asset_type == 'faab':
            amount = int(asset_name.replace('$', '').replace(' FAAB', ''))
            value = amount * FAAB_VALUE_PER_DOLLAR
            
            cached_values.append({
                'asset_name': asset_name,
                'asset_type': asset_type,
                'trade_date': trade_date,
                'trade_id': row['trade_id'],
                'trade_type': row.get('trade_type', '2-team'),
                'receiving_team': row['receiving_team'],
                'giving_team': row['giving_team'],
                'origin_owner': origin_owner,
                'value_at_trade': value,
                'value_current': value,
                'value_source_at_trade': 'FAAB',
                'value_source_current': 'FAAB',
                'metadata': f"${amount}"
            })
            continue
        
        # Get historical value (at trade time)
        # Find closest Git commit - search both before AND after trade date
        commit_sha = commit_cache.get(trade_date)
        if not commit_sha:
            trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
            
            # First try looking backwards (preferred - historical data)
            for delta in range(1, config.validation.git_commit_search_days + 1):
                before = (trade_dt - timedelta(days=delta)).strftime('%Y-%m-%d')
                if before in commit_cache:
                    commit_sha = commit_cache[before]
                    logger.debug(f"Found commit {delta} days before trade: {commit_sha[:7]}")
                    break
            
            # If no commit found before, try looking forward (for early season trades)
            if not commit_sha:
                for delta in range(1, config.validation.git_commit_search_days + 1):
                    after = (trade_dt + timedelta(days=delta)).strftime('%Y-%m-%d')
                    if after in commit_cache:
                        commit_sha = commit_cache[after]
                        logger.debug(f"Found commit {delta} days after trade: {commit_sha[:7]}")
                        break
        
        df_hist = None
        if commit_sha:
            df_hist = get_values_from_commit(commit_sha, git_df_cache)
        
        # Determine value based on asset type
        if asset_type == 'pick':
            # 2025 picks
            if '2025 Round' in asset_name and origin_owner:
                df_for_at_trade = df_hist if df_hist is not None else df_current
                value_at_trade, source_at_trade, meta_at_trade = get_2025_pick_value(
                    asset_name, origin_owner, trade_date, df_for_at_trade, False
                )
                value_current, source_current, meta_current = get_2025_pick_value(
                    asset_name, origin_owner, trade_date, df_current, True
                )
            
            # 2026+ picks
            elif ('2026' in asset_name or '2027' in asset_name or '2028' in asset_name) and origin_owner:
                df_for_at_trade = df_hist if df_hist is not None else df_current
                value_at_trade, source_at_trade, meta_at_trade = get_2026_plus_pick_value(
                    asset_name, origin_owner, trade_date, df_for_at_trade
                )
                value_current, source_current, meta_current = get_2026_plus_pick_value(
                    asset_name, origin_owner, trade_date, df_current
                )
            
            else:
                # Fallback
                value_at_trade = 0
                value_current = 0
                source_at_trade = "Unknown pick"
                source_current = "Unknown pick"
                meta_at_trade = None
                meta_current = None
        
        else:  # Players
            # Historical value
            if df_hist is not None:
                matches = df_hist[df_hist['player'].str.contains(asset_name, case=False, na=False)]
                value_at_trade = matches.iloc[0]['value_2qb'] if not matches.empty else 0
                source_at_trade = f"Git:{commit_sha[:7]}" if not matches.empty else "Not found"
            else:
                value_at_trade = 0
                source_at_trade = "No Git commit"
            
            # Current value
            matches = df_current[df_current['player'].str.contains(asset_name, case=False, na=False)]
            value_current = matches.iloc[0]['value_2qb'] if not matches.empty else 0
            source_current = "DynastyProcess" if not matches.empty else "Not found"
            
            meta_at_trade = None
            meta_current = None
        
        # Track zero values
        if value_at_trade == 0:
            zero_value_count += 1
        
        cached_values.append({
            'asset_name': asset_name,
            'asset_type': asset_type,
            'trade_date': trade_date,
            'trade_id': row['trade_id'],
            'trade_type': row.get('trade_type', '2-team'),
            'receiving_team': row['receiving_team'],
            'giving_team': row['giving_team'],
            'origin_owner': origin_owner,
            'value_at_trade': value_at_trade,
            'value_current': value_current,
            'value_source_at_trade': source_at_trade,
            'value_source_current': source_current,
            'metadata': str(meta_current or meta_at_trade or '')
        })
    
    logger.info(f"✓ Cached {len(cached_values)} asset valuations")
    
    zero_pct = zero_value_count / len(cached_values) if cached_values else 0
    logger.info(f"  Zero values: {zero_value_count} ({zero_pct:.1%})")
    metrics.record('count.zero_values', zero_value_count)
    metrics.record('percent.zero_values', zero_pct)
    
    return cached_values


def main():
    """Main execution function for Stage 3"""
    start_time = time.time()
    
    try:
        # Validate prerequisites
        StageValidator.validate_stage3_prerequisites()
        
        # Load asset transactions
        logger.info("Loading asset_transactions.csv...")
        df_assets = pd.read_csv(OutputFiles.ASSET_TRANSACTIONS.value)
        logger.info(f"✓ {len(df_assets)} asset transactions")
        metrics.record('count.input_assets', len(df_assets))
        
        # Cache values
        cached_values = cache_asset_values(df_assets)
        
        # Create DataFrame
        df_cache = pd.DataFrame(cached_values)
        
        # Save
        output_file = OutputFiles.ASSET_VALUES_CACHE.value
        df_cache.to_csv(output_file, index=False)
        
        logger.info(f"✓ Saved {len(df_cache)} cached values to: {output_file}")
        
        # Create backup
        backup_mgr = BackupManager(
            backup_dir=str(config.storage.backup_dir),
            retention_days=config.storage.retention_days
        )
        backup_mgr.backup_file(output_file, 'stage3')
        
        # Validate output
        StageValidator.validate_stage3_output(output_file, config.validation.max_zero_value_pct)
        
        # Statistics
        logger.info("📊 VALUE STATISTICS:")
        
        # By asset type
        for asset_type in df_cache['asset_type'].unique():
            subset = df_cache[df_cache['asset_type'] == asset_type]
            avg_at_trade = subset['value_at_trade'].mean()
            avg_current = subset['value_current'].mean()
            logger.info(f"  {asset_type.upper()}:")
            logger.info(f"    Count: {len(subset)}")
            logger.info(f"    Avg at trade: {avg_at_trade:.0f}")
            logger.info(f"    Avg current: {avg_current:.0f}")
            logger.info(f"    Avg change: {avg_current - avg_at_trade:+.0f}")
            
            metrics.record(f'avg_value_{asset_type}_at_trade', avg_at_trade)
            metrics.record(f'avg_value_{asset_type}_current', avg_current)
        
        # 2025 pick breakdown
        picks_2025 = df_cache[df_cache['asset_name'].str.contains('2025 Round', na=False)]
        if len(picks_2025) > 0:
            logger.info("  2025 PICKS BREAKDOWN:")
            logger.info(f"    Total: {len(picks_2025)}")
            
            # By round
            for round_num in [1, 2, 3, 4]:
                round_picks = picks_2025[picks_2025['asset_name'].str.contains(f'Round {round_num}', na=False)]
                if len(round_picks) > 0:
                    avg_at = round_picks['value_at_trade'].mean()
                    avg_now = round_picks['value_current'].mean()
                    logger.info(f"    Round {round_num}: {len(round_picks)} picks | At trade: {avg_at:.0f} → Current: {avg_now:.0f}")
                    
                    metrics.record(f'count.2025_round{round_num}_picks', len(round_picks))
        
        # Record success metrics
        duration = time.time() - start_time
        metrics.record_duration('stage3', duration)
        metrics.record_success('stage3')
        metrics.record('count.cached_values', len(df_cache))
        
        logger.info("="*80)
        logger.info("✓ STAGE 3 COMPLETE")
        logger.info(f"✓ Duration: {duration:.2f}s")
        logger.info("="*80)
        
        # Save metrics
        metrics.save()
        
        return output_file
        
    except (APIError, ValidationError) as e:
        duration = time.time() - start_time
        metrics.record_duration('stage3', duration)
        metrics.record_failure('stage3', str(e))
        metrics.save()
        logger.error(f"Stage 3 failed after {duration:.2f}s: {e}")
        raise
    except Exception as e:
        duration = time.time() - start_time
        metrics.record_duration('stage3', duration)
        metrics.record_failure('stage3', str(e))
        metrics.save()
        logger.error(f"Stage 3 unexpected error after {duration:.2f}s", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        output_file = main()
        logger.info(f"✓ Output ready: {output_file}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Stage 3 failed: {e}")
        sys.exit(1)