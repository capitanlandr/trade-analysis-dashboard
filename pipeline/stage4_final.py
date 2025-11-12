#!/usr/bin/env python3
"""
STAGE 4: Analyze Trades with Multi-Team Support
Aggregates asset values and calculates trade outcomes

IMPROVEMENTS:
- Structured logging
- Pre/post validation
- Automatic backups
- Metrics collection
- Better error handling
"""

import pandas as pd
import json
import time
from typing import Dict, List
import sys

# Pipeline utilities
from config import get_config
from constants import OutputFiles
from utils.logging_config import setup_logging
from utils.validators import StageValidator, ValidationError
from utils.backup import BackupManager
from utils.metrics import LocalMetrics

# Initialize
logger = setup_logging('Stage 4: Analyze Trades')
config = get_config()
metrics = LocalMetrics()


def analyze_2team_trades(df_cache: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze 2-team trades by aggregating values.
    
    Args:
        df_cache: Cached asset values DataFrame
        
    Returns:
        DataFrame of analyzed trades
    """
    logger.info("Analyzing 2-team trades...")
    trades = {}
    
    for _, row in df_cache.iterrows():
        trade_id = row['trade_id']
        
        if trade_id not in trades:
            trades[trade_id] = {
                'trade_date': row['trade_date'],
                'roster_a': None,
                'roster_b': None,
                'team_a_assets': [],
                'team_a_value_then': 0,
                'team_a_value_now': 0,
                'team_b_assets': [],
                'team_b_value_then': 0,
                'team_b_value_now': 0,
            }
        
        trade = trades[trade_id]
        
        if trade['roster_a'] is None:
            trade['roster_a'] = row['receiving_team']
            trade['roster_b'] = row['giving_team']
        
        if row['receiving_team'] == trade['roster_a']:
            trade['team_a_assets'].append(row['asset_name'])
            trade['team_a_value_then'] += row['value_at_trade']
            trade['team_a_value_now'] += row['value_current']
        else:
            trade['team_b_assets'].append(row['asset_name'])
            trade['team_b_value_then'] += row['value_at_trade']
            trade['team_b_value_now'] += row['value_current']
    
    results = []
    for trade_id, t in trades.items():
        winner_then = t['roster_a'] if t['team_a_value_then'] > t['team_b_value_then'] else t['roster_b']
        winner_now = t['roster_a'] if t['team_a_value_now'] > t['team_b_value_now'] else t['roster_b']
        
        if t['team_a_value_then'] > t['team_b_value_then']:
            margin_swing = (t['team_a_value_now'] - t['team_b_value_now']) - (t['team_a_value_then'] - t['team_b_value_then'])
        else:
            margin_swing = (t['team_b_value_now'] - t['team_a_value_now']) - (t['team_b_value_then'] - t['team_a_value_then'])
        
        results.append({
            'trade_date': t['trade_date'],
            'transaction_id': trade_id,
            'team_a': t['roster_a'],
            'team_a_received': ' | '.join(t['team_a_assets']),
            'team_a_value_then': t['team_a_value_then'],
            'team_a_value_now': t['team_a_value_now'],
            'team_a_value_change': t['team_a_value_now'] - t['team_a_value_then'],
            'team_b': t['roster_b'],
            'team_b_received': ' | '.join(t['team_b_assets']),
            'team_b_value_then': t['team_b_value_then'],
            'team_b_value_now': t['team_b_value_now'],
            'team_b_value_change': t['team_b_value_now'] - t['team_b_value_then'],
            'winner_at_trade': winner_then,
            'winner_current': winner_now,
            'margin_at_trade': abs(t['team_a_value_then'] - t['team_b_value_then']),
            'margin_current': abs(t['team_a_value_now'] - t['team_b_value_now']),
            'swing_winner': winner_now if margin_swing != 0 else 'Tie',
            'swing_margin': abs(margin_swing)
        })
    
    logger.info(f"✓ Analyzed {len(results)} 2-team trades")
    metrics.record('count.two_team_analyzed', len(results))
    
    return pd.DataFrame(results).sort_values('swing_margin', ascending=False)


def analyze_multiteam(df_cache: pd.DataFrame) -> List[Dict]:
    """
    Analyze multi-team trades by team net values.
    
    Args:
        df_cache: Cached asset values DataFrame
        
    Returns:
        List of multi-team trade analysis dictionaries
    """
    logger.info("Analyzing multi-team trades...")
    
    results = []
    for trade_id in df_cache['trade_id'].unique():
        assets = df_cache[df_cache['trade_id'] == trade_id]
        teams = set(assets['receiving_team'].unique())
        
        team_data = []
        for team in teams:
            received = assets[assets['receiving_team'] == team]
            team_data.append({
                'manager': team,
                'assets': list(received['asset_name']),
                'value_then': float(received['value_at_trade'].sum()),
                'value_now': float(received['value_current'].sum())
            })
        
        results.append({
            'date': str(assets.iloc[0]['trade_date']),
            'trade_id': int(trade_id),
            'teams': team_data
        })
    
    logger.info(f"✓ Analyzed {len(results)} multi-team trades")
    metrics.record('count.multi_team_analyzed', len(results))
    
    return results


def main():
    """Main execution function for Stage 4"""
    start_time = time.time()
    
    try:
        # Validate prerequisites
        StageValidator.validate_stage4_prerequisites()
        
        # Load cached values
        logger.info(f"Loading {OutputFiles.ASSET_VALUES_CACHE.value}...")
        df_cache = pd.read_csv(OutputFiles.ASSET_VALUES_CACHE.value)
        
        # Separate by trade type
        two_team = df_cache[df_cache.get('trade_type', '2-team') == '2-team']
        multi_team = df_cache[df_cache.get('trade_type', '2-team') != '2-team']
        
        logger.info(f"✓ Loaded {len(df_cache)} cached values")
        logger.info(f"✓ 2-team: {two_team['trade_id'].nunique()} trades")
        logger.info(f"✓ Multi-team: {multi_team['trade_id'].nunique()} trades")
        
        metrics.record('count.input_cached_values', len(df_cache))
        metrics.record('count.two_team_trades', two_team['trade_id'].nunique())
        metrics.record('count.multi_team_trades', multi_team['trade_id'].nunique())
        
        # Analyze 2-team trades
        df_2team = analyze_2team_trades(two_team)
        output_file = OutputFiles.TRADES_ANALYSIS.value
        df_2team.to_csv(output_file, index=False)
        
        logger.info(f"✓ Saved {len(df_2team)} analyzed trades to: {output_file}")
        
        # Create backup
        backup_mgr = BackupManager(
            backup_dir=str(config.storage.backup_dir),
            retention_days=config.storage.retention_days
        )
        backup_mgr.backup_file(output_file, 'stage4')
        
        # Validate output
        StageValidator.validate_stage4_output(output_file)
        
        # Analyze multi-team trades
        multiteam_results = []
        if len(multi_team) > 0:
            multiteam_results = analyze_multiteam(multi_team)
            
            multiteam_file = OutputFiles.MULTITEAM_ANALYSIS.value
            with open(multiteam_file, 'w') as f:
                json.dump(multiteam_results, f, indent=2)
            
            backup_mgr.backup_file(multiteam_file, 'stage4_multiteam')
            
            logger.info("="*80)
            logger.info("3-TEAM TRADE DETAILS:")
            logger.info("="*80)
            
            for result in multiteam_results:
                logger.info(f"\nDate: {result['date']}")
                logger.info(f"Trade ID: {result['trade_id']}")
                logger.info("-"*80)
                
                for team in result['teams']:
                    change = team['value_now'] - team['value_then']
                    logger.info(f"\n{team['manager']}:")
                    logger.info(f"  Value then: {team['value_now']:.0f}")
                    logger.info(f"  Value now: {team['value_now']:.0f}")
                    logger.info(f"  Net change: {change:+.0f}")
                    logger.info(f"  Assets: {', '.join(team['assets'][:3])}...")
        
        # Calculate summary statistics
        if len(df_2team) > 0:
            avg_swing = df_2team['swing_margin'].mean()
            max_swing = df_2team['swing_margin'].max()
            
            logger.info("📊 TRADE STATISTICS:")
            logger.info(f"  Average swing: {avg_swing:.0f}")
            logger.info(f"  Maximum swing: {max_swing:.0f}")
            
            metrics.record('avg_swing_margin', avg_swing)
            metrics.record('max_swing_margin', max_swing)
        
        # Record success metrics
        duration = time.time() - start_time
        metrics.record_duration('stage4', duration)
        metrics.record_success('stage4')
        metrics.record('count.output_trades', len(df_2team))
        
        logger.info("="*80)
        logger.info("✓ STAGE 4 COMPLETE")
        logger.info(f"✓ Duration: {duration:.2f}s")
        logger.info("="*80)
        logger.info(f"✓ {output_file} ({len(df_2team)} 2-team trades)")
        if multiteam_results:
            logger.info(f"✓ {OutputFiles.MULTITEAM_ANALYSIS.value} ({len(multiteam_results)} multi-team trades)")
        logger.info("="*80)
        
        # Save metrics
        metrics.save()
        
        return output_file
        
    except ValidationError as e:
        duration = time.time() - start_time
        metrics.record_duration('stage4', duration)
        metrics.record_failure('stage4', str(e))
        metrics.save()
        logger.error(f"Stage 4 failed after {duration:.2f}s: {e}")
        raise
    except Exception as e:
        duration = time.time() - start_time
        metrics.record_duration('stage4', duration)
        metrics.record_failure('stage4', str(e))
        metrics.save()
        logger.error(f"Stage 4 unexpected error after {duration:.2f}s", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        output_file = main()
        logger.info(f"✓ Output ready: {output_file}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Stage 4 failed: {e}")
        sys.exit(1)