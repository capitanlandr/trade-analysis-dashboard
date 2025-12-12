#!/usr/bin/env python3
"""
Explore Sleeper API for Waiver Wire Transaction Data
Tests various endpoints to see what waiver wire data is available
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from utils.logging_config import setup_logging
from utils.api_client import fetch_with_retry, APIError

logger = setup_logging('Waiver Wire API Explorer')
config = get_config()

def explore_waiver_wire_data():
    """
    Explore what waiver wire transaction data is available from Sleeper API
    """
    league_id = config.league_id
    base_url = config.sleeper_api.base_url
    
    logger.info("="*80)
    logger.info("EXPLORING SLEEPER API FOR WAIVER WIRE DATA")
    logger.info(f"League ID: {league_id}")
    logger.info("="*80)
    
    # 1. Get league info first
    logger.info("\n1. FETCHING LEAGUE INFO...")
    try:
        league_url = f"{base_url}/league/{league_id}"
        league = fetch_with_retry(league_url)
        
        season = league.get('season')
        league_name = league.get('name')
        current_week = league.get('settings', {}).get('leg', 1)
        
        logger.info(f"✓ League: {league_name}")
        logger.info(f"✓ Season: {season}")
        logger.info(f"✓ Current week: {current_week}")
        
    except APIError as e:
        logger.error(f"Failed to fetch league info: {e}")
        return
    
    # 2. Explore transactions by week
    logger.info(f"\n2. EXPLORING TRANSACTIONS BY WEEK (weeks 1-{current_week + 2})...")
    
    all_waiver_transactions = []
    all_free_agent_transactions = []
    other_transactions = []
    
    for week in range(1, current_week + 3):
        logger.info(f"\n--- Week {week} ---")
        
        try:
            url = f"{base_url}/league/{league_id}/transactions/{week}"
            transactions = fetch_with_retry(url)
            
            if not transactions:
                logger.info(f"  No transactions found for week {week}")
                continue
                
            logger.info(f"  Total transactions: {len(transactions)}")
            
            # Categorize transactions by type
            by_type = {}
            for t in transactions:
                t_type = t.get('type', 'unknown')
                by_type[t_type] = by_type.get(t_type, 0) + 1
            
            logger.info(f"  Transaction types: {dict(by_type)}")
            
            # Look for waiver and free agent transactions
            waiver_txns = [t for t in transactions if t.get('type') == 'waiver']
            free_agent_txns = [t for t in transactions if t.get('type') == 'free_agent']
            
            if waiver_txns:
                logger.info(f"  🎯 WAIVER transactions: {len(waiver_txns)}")
                all_waiver_transactions.extend(waiver_txns)
                
                # Show sample waiver transaction structure
                if len(all_waiver_transactions) == len(waiver_txns):  # First batch
                    logger.info(f"  Sample waiver transaction structure:")
                    sample = waiver_txns[0]
                    for key, value in sample.items():
                        if isinstance(value, (dict, list)) and len(str(value)) > 100:
                            logger.info(f"    {key}: {type(value).__name__} (length: {len(value) if isinstance(value, list) else 'complex'})")
                        else:
                            logger.info(f"    {key}: {value}")
            
            if free_agent_txns:
                logger.info(f"  🎯 FREE AGENT transactions: {len(free_agent_txns)}")
                all_free_agent_transactions.extend(free_agent_txns)
                
                # Show sample free agent transaction structure
                if len(all_free_agent_transactions) == len(free_agent_txns):  # First batch
                    logger.info(f"  Sample free agent transaction structure:")
                    sample = free_agent_txns[0]
                    for key, value in sample.items():
                        if isinstance(value, (dict, list)) and len(str(value)) > 100:
                            logger.info(f"    {key}: {type(value).__name__} (length: {len(value) if isinstance(value, list) else 'complex'})")
                        else:
                            logger.info(f"    {key}: {value}")
            
            # Collect other transaction types for analysis
            other_txns = [t for t in transactions if t.get('type') not in ['waiver', 'free_agent', 'trade']]
            if other_txns:
                other_transactions.extend(other_txns)
                
        except APIError as e:
            logger.debug(f"  Week {week} not available: {e}")
            continue
    
    # 3. Summary of findings
    logger.info("\n" + "="*80)
    logger.info("WAIVER WIRE DATA SUMMARY")
    logger.info("="*80)
    
    logger.info(f"Total waiver transactions found: {len(all_waiver_transactions)}")
    logger.info(f"Total free agent transactions found: {len(all_free_agent_transactions)}")
    logger.info(f"Other transaction types found: {len(other_transactions)}")
    
    if other_transactions:
        other_types = {}
        for t in other_transactions:
            t_type = t.get('type', 'unknown')
            other_types[t_type] = other_types.get(t_type, 0) + 1
        logger.info(f"Other transaction types: {dict(other_types)}")
    
    # 4. Analyze waiver transaction structure in detail
    if all_waiver_transactions:
        logger.info(f"\n4. DETAILED WAIVER TRANSACTION ANALYSIS")
        logger.info(f"Analyzing {len(all_waiver_transactions)} waiver transactions...")
        
        # Get all unique fields across all waiver transactions
        all_fields = set()
        for t in all_waiver_transactions:
            all_fields.update(t.keys())
        
        logger.info(f"Fields available in waiver transactions:")
        for field in sorted(all_fields):
            # Show sample values for each field
            sample_values = []
            for t in all_waiver_transactions[:3]:  # First 3 transactions
                if field in t:
                    value = t[field]
                    if isinstance(value, (dict, list)):
                        sample_values.append(f"{type(value).__name__}({len(value) if isinstance(value, list) else 'complex'})")
                    else:
                        sample_values.append(str(value))
            
            logger.info(f"  {field}: {', '.join(sample_values[:3])}")
        
        # Analyze waiver priorities and outcomes
        logger.info(f"\nWaiver transaction status analysis:")
        statuses = {}
        for t in all_waiver_transactions:
            status = t.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
        
        for status, count in statuses.items():
            logger.info(f"  {status}: {count}")
    
    # 5. Analyze free agent transaction structure
    if all_free_agent_transactions:
        logger.info(f"\n5. DETAILED FREE AGENT TRANSACTION ANALYSIS")
        logger.info(f"Analyzing {len(all_free_agent_transactions)} free agent transactions...")
        
        # Get all unique fields
        all_fields = set()
        for t in all_free_agent_transactions:
            all_fields.update(t.keys())
        
        logger.info(f"Fields available in free agent transactions:")
        for field in sorted(all_fields):
            sample_values = []
            for t in all_free_agent_transactions[:3]:
                if field in t:
                    value = t[field]
                    if isinstance(value, (dict, list)):
                        sample_values.append(f"{type(value).__name__}({len(value) if isinstance(value, list) else 'complex'})")
                    else:
                        sample_values.append(str(value))
            
            logger.info(f"  {field}: {', '.join(sample_values[:3])}")
    
    # 6. Save sample data for further analysis
    if all_waiver_transactions or all_free_agent_transactions:
        sample_data = {
            'metadata': {
                'league_id': league_id,
                'league_name': league_name,
                'season': season,
                'exploration_timestamp': datetime.now().isoformat(),
                'total_waiver_transactions': len(all_waiver_transactions),
                'total_free_agent_transactions': len(all_free_agent_transactions)
            },
            'sample_waiver_transactions': all_waiver_transactions[:5],  # First 5
            'sample_free_agent_transactions': all_free_agent_transactions[:5],  # First 5
            'all_waiver_transactions': all_waiver_transactions,
            'all_free_agent_transactions': all_free_agent_transactions
        }
        
        output_file = 'waiver_wire_exploration.json'
        with open(output_file, 'w') as f:
            json.dump(sample_data, f, indent=2)
        
        logger.info(f"\n✓ Sample data saved to: {output_file}")
        logger.info(f"✓ This file contains all waiver/free agent transactions for analysis")
    
    # 7. Recommendations
    logger.info(f"\n6. RECOMMENDATIONS FOR WAIVER WIRE ANALYSIS")
    logger.info("="*50)
    
    if all_waiver_transactions:
        logger.info("✓ Waiver transactions are available!")
        logger.info("  - Can track waiver claims and priorities")
        logger.info("  - Can analyze success/failure rates")
        logger.info("  - Can identify most active waiver users")
    
    if all_free_agent_transactions:
        logger.info("✓ Free agent transactions are available!")
        logger.info("  - Can track free agent pickups")
        logger.info("  - Can analyze pickup/drop patterns")
        logger.info("  - Can identify valuable free agents")
    
    if not all_waiver_transactions and not all_free_agent_transactions:
        logger.info("⚠️  No waiver/free agent transactions found")
        logger.info("  - League may not have waiver activity yet")
        logger.info("  - Check again during active season")
    
    logger.info("\nNext steps:")
    logger.info("1. Review the saved JSON file for detailed transaction structure")
    logger.info("2. Identify key fields for analysis (player_ids, roster_ids, etc.)")
    logger.info("3. Create pipeline stage to process waiver wire data")
    logger.info("4. Build dashboard components to visualize waiver activity")


if __name__ == "__main__":
    try:
        explore_waiver_wire_data()
        logger.info("\n✓ Exploration complete!")
    except Exception as e:
        logger.error(f"❌ Exploration failed: {e}", exc_info=True)
        sys.exit(1)