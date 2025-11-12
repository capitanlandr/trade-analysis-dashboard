#!/usr/bin/env python3
"""
STAGE 2: Extract Assets from Trades
Flattens trade data into individual asset transactions
Creates asset_transactions.csv where each row = one asset changing hands

IMPROVEMENTS:
- Structured logging
- Error handling for API calls
- Pre/post validation
- Automatic backups
- Metrics collection
"""

import json
import pandas as pd
import time
from datetime import datetime
from typing import Dict, List, Tuple
import sys

# Pipeline utilities
from config import get_config
from constants import OutputFiles, AssetType
from utils.logging_config import setup_logging
from utils.api_client import fetch_with_retry, APIError
from utils.validators import StageValidator, ValidationError
from utils.backup import BackupManager
from utils.metrics import LocalMetrics

# Initialize
logger = setup_logging('Stage 2: Extract Assets')
config = get_config()
metrics = LocalMetrics()


def load_trades() -> Dict:
    """
    Load trades from Stage 1 output.
    
    Returns:
        Trade data dictionary
        
    Raises:
        ValidationError: If trades_raw.json not found or invalid
    """
    logger.info("Loading trades_raw.json...")
    
    try:
        with open(OutputFiles.TRADES_RAW.value, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValidationError("trades_raw.json not found - run Stage 1 first")
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in trades_raw.json: {e}")
    
    metadata = data['metadata']
    logger.info(f"✓ League: {metadata['league_name']}")
    logger.info(f"✓ Season: {metadata['season']}")
    logger.info(f"✓ Total trades: {metadata['total_trades']}")
    
    metrics.record('count.input_trades', metadata['total_trades'])
    
    return data


def create_user_maps(users: List, rosters: List) -> Tuple[Dict, Dict, Dict]:
    """
    Create lookup dictionaries for users and rosters.
    
    Args:
        users: List of user objects
        rosters: List of roster objects
        
    Returns:
        Tuple of (user_map, roster_to_user, roster_to_username)
    """
    user_map = {u['user_id']: u.get('display_name', u.get('username')) for u in users}
    roster_to_user = {r['roster_id']: r.get('owner_id') for r in rosters}
    roster_to_username = {
        r['roster_id']: user_map.get(r.get('owner_id'), f"Roster{r['roster_id']}") 
        for r in rosters
    }
    
    logger.debug(f"Created maps for {len(users)} users and {len(rosters)} rosters")
    
    return user_map, roster_to_user, roster_to_username


def fetch_player_data() -> Dict:
    """
    Fetch NFL player data from Sleeper API with retry logic.
    
    Returns:
        Dictionary mapping player IDs to player data
        
    Raises:
        APIError: If fetching fails after retries
    """
    logger.info("Loading NFL players...")
    
    try:
        players_url = f"{config.sleeper_api.base_url}/players/nfl"
        players = fetch_with_retry(players_url, timeout=config.sleeper_api.timeout)
        
        logger.info(f"✓ {len(players)} players loaded")
        metrics.record('count.players_loaded', len(players))
        metrics.record('api.sleeper.players.success', 1)
        
        return players
        
    except APIError as e:
        logger.error(f"Failed to fetch player data: {e}")
        metrics.record('api.sleeper.players.error', 1)
        raise


def extract_assets_from_trades(data: Dict) -> List[Dict]:
    """
    Extract all assets from all trades.
    
    Args:
        data: Trade data from Stage 1
        
    Returns:
        List of asset transaction dictionaries
    """
    logger.info("="*80)
    logger.info("EXTRACTING ASSETS")
    logger.info("="*80)
    
    trades = data['trades']
    users = data['users']
    rosters = data['rosters']
    
    user_map, roster_to_user, roster_to_username = create_user_maps(users, rosters)
    
    # Load player data once
    players = fetch_player_data()
    
    # Extract all assets
    asset_transactions = []
    
    logger.info(f"Processing {len(trades)} trades...")
    
    player_count = 0
    pick_count = 0
    faab_count = 0
    
    for trade_idx, trade in enumerate(trades, 1):
        trade_id = trade.get('transaction_id')
        trade_date = datetime.fromtimestamp(trade.get('created', 0)/1000).strftime('%Y-%m-%d')
        status = trade.get('status', 'unknown')
        roster_ids = trade.get('roster_ids', [])
        
        # Determine trade type
        trade_type = '2-team' if len(roster_ids) == 2 else f'{len(roster_ids)}-team'
        
        # For 2-team, set team_a and team_b for roster_a/roster_b columns
        if len(roster_ids) == 2:
            roster_a, roster_b = roster_ids[0], roster_ids[1]
            team_a = roster_to_username[roster_a]
            team_b = roster_to_username[roster_b]
        else:
            # Multi-team: set to first two for compatibility, but mark as multi-team
            team_a = f"{len(roster_ids)}-team trade"
            team_b = ""
        
        # Process player adds
        adds = trade.get('adds') or {}
        for player_id, to_roster in adds.items():
            player_name = players.get(str(player_id), {}).get('full_name', f'Player_{player_id}')
            
            # Find receiving and giving teams
            receiving_team = roster_to_username.get(to_roster, f'Roster{to_roster}')
            
            # Giving team = everyone else who didn't receive (for 2-team it's the other team)
            if len(roster_ids) == 2:
                giving_team = team_b if to_roster == roster_a else team_a
            else:
                # For multi-team, mark as multi-team
                giving_team = f'{len(roster_ids)}-team'
            
            asset_transactions.append({
                'trade_date': trade_date,
                'trade_id': trade_id,
                'trade_status': status,
                'trade_type': trade_type,
                'asset_type': AssetType.PLAYER.value,
                'asset_name': player_name,
                'receiving_team': receiving_team,
                'giving_team': giving_team,
                'origin_owner': None,
                'roster_a': team_a,
                'roster_b': team_b
            })
            player_count += 1
        
        # Process draft picks
        draft_picks = trade.get('draft_picks') or []
        for pick in draft_picks:
            season = pick.get('season')
            round_num = pick.get('round')
            new_roster_id = pick.get('owner_id')
            original_roster_id = pick.get('roster_id')
            
            pick_name = f"{season} Round {round_num}"
            
            origin_owner = roster_to_username.get(original_roster_id, f'Roster{original_roster_id}')
            
            # Find teams
            receiving_team = roster_to_username.get(new_roster_id, f'Roster{new_roster_id}')
            
            if len(roster_ids) == 2:
                giving_team = team_b if new_roster_id == roster_a else team_a
            else:
                giving_team = f'{len(roster_ids)}-team'
            
            asset_transactions.append({
                'trade_date': trade_date,
                'trade_id': trade_id,
                'trade_status': status,
                'trade_type': trade_type,
                'asset_type': AssetType.PICK.value,
                'asset_name': pick_name,
                'receiving_team': receiving_team,
                'giving_team': giving_team,
                'origin_owner': origin_owner,
                'roster_a': team_a,
                'roster_b': team_b
            })
            pick_count += 1
        
        # Process FAAB
        waiver_budget = trade.get('waiver_budget') or []
        for faab in waiver_budget:
            amount = faab.get('amount', 0)
            sender = faab.get('sender')
            receiver = faab.get('receiver')
            
            faab_name = f"${amount} FAAB"
            
            receiving_team = roster_to_username.get(receiver, f'Roster{receiver}')
            
            if len(roster_ids) == 2:
                giving_team = team_b if receiver == roster_a else team_a
            else:
                giving_team = f'{len(roster_ids)}-team'
            
            asset_transactions.append({
                'trade_date': trade_date,
                'trade_id': trade_id,
                'trade_status': status,
                'trade_type': trade_type,
                'asset_type': AssetType.FAAB.value,
                'asset_name': faab_name,
                'receiving_team': receiving_team,
                'giving_team': giving_team,
                'origin_owner': None,
                'roster_a': team_a,
                'roster_b': team_b
            })
            faab_count += 1
        
        if trade_idx % 10 == 0:
            logger.info(f"  Processed {trade_idx}/{len(trades)} trades...")
    
    logger.info(f"✓ Processed all trades")
    logger.info(f"✓ Extracted {len(asset_transactions)} individual asset transactions")
    logger.info(f"  Players: {player_count}")
    logger.info(f"  Picks: {pick_count}")
    logger.info(f"  FAAB: {faab_count}")
    
    metrics.record('count.assets_players', player_count)
    metrics.record('count.assets_picks', pick_count)
    metrics.record('count.assets_faab', faab_count)
    metrics.record('count.total_assets', len(asset_transactions))
    
    return asset_transactions


def main():
    """Main execution function for Stage 2"""
    start_time = time.time()
    
    try:
        # Validate prerequisites
        StageValidator.validate_stage2_prerequisites()
        
        # Load data
        data = load_trades()
        
        # Extract assets
        asset_transactions = extract_assets_from_trades(data)
        
        # Create DataFrame
        df = pd.DataFrame(asset_transactions)
        
        # Save to CSV
        output_file = OutputFiles.ASSET_TRANSACTIONS.value
        df.to_csv(output_file, index=False)
        
        logger.info(f"✓ Saved {len(df)} asset transactions to: {output_file}")
        
        # Create backup
        backup_mgr = BackupManager(
            backup_dir=str(config.storage.backup_dir),
            retention_days=config.storage.retention_days
        )
        backup_mgr.backup_file(output_file, 'stage2')
        
        # Validate output
        StageValidator.validate_stage2_output(output_file)
        
        # Summary statistics
        logger.info("📊 ASSET BREAKDOWN:")
        logger.info(f"  Players: {len(df[df['asset_type'] == 'player'])}")
        logger.info(f"  Picks: {len(df[df['asset_type'] == 'pick'])}")
        logger.info(f"  FAAB: {len(df[df['asset_type'] == 'faab'])}")
        
        # Show unique assets
        logger.info("📦 UNIQUE ASSETS:")
        unique_players = df[df['asset_type'] == 'player']['asset_name'].nunique()
        unique_picks = df[df['asset_type'] == 'pick']['asset_name'].nunique()
        logger.info(f"  Unique players traded: {unique_players}")
        logger.info(f"  Unique picks traded: {unique_picks}")
        
        metrics.record('count.unique_players', unique_players)
        metrics.record('count.unique_picks', unique_picks)
        
        # Most traded assets
        logger.info("🔄 MOST TRADED ASSETS:")
        player_counts = df[df['asset_type'] == 'player']['asset_name'].value_counts()
        if len(player_counts) > 0:
            logger.info("  Players:")
            for player, count in player_counts.head(5).items():
                logger.info(f"    {player}: {count} times")
        
        pick_counts = df[df['asset_type'] == 'pick']['asset_name'].value_counts()
        if len(pick_counts) > 0:
            logger.info("  Picks:")
            for pick, count in pick_counts.head(5).items():
                logger.info(f"    {pick}: {count} times")
        
        # Record success metrics
        duration = time.time() - start_time
        metrics.record_duration('stage2', duration)
        metrics.record_success('stage2')
        
        logger.info("="*80)
        logger.info("✓ STAGE 2 COMPLETE")
        logger.info(f"✓ Duration: {duration:.2f}s")
        logger.info("="*80)
        
        # Save metrics
        metrics.save()
        
        return output_file
        
    except (APIError, ValidationError) as e:
        duration = time.time() - start_time
        metrics.record_duration('stage2', duration)
        metrics.record_failure('stage2', str(e))
        metrics.save()
        logger.error(f"Stage 2 failed after {duration:.2f}s: {e}")
        raise
    except Exception as e:
        duration = time.time() - start_time
        metrics.record_duration('stage2', duration)
        metrics.record_failure('stage2', str(e))
        metrics.save()
        logger.error(f"Stage 2 unexpected error after {duration:.2f}s", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        output_file = main()
        logger.info(f"✓ Output ready: {output_file}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Stage 2 failed: {e}")
        sys.exit(1)