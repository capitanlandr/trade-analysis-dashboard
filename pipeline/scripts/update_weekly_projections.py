#!/usr/bin/env python3
"""
Automatic Weekly Projections Column Generator

Automatically adds missing weekly columns for 2026 2nd/3rd/4th round picks
as the season progresses, using tier-based value calculations.
"""

import pandas as pd
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.week_config import get_through_week

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

# Season configuration
PROJECTIONS_FILE = 'weekly_2026_pick_projections_expanded.csv'

# Tier-based values for 2nd/3rd/4th round picks
TIER_VALUES = {
    'Early': {
        '2nd': 622,
        '3rd': 106, 
        '4th': 29
    },
    'Mid': {
        '2nd': 330,
        '3rd': 65,
        '4th': 20
    },
    'Late': {
        '2nd': 183,
        '3rd': 42,
        '4th': 15
    }
}


# Removed get_current_week() - now using get_through_week() from week_config


def get_missing_columns(df: pd.DataFrame, current_week: int) -> List[str]:
    """
    Identify missing weekly columns for 2nd/3rd/4th round picks.
    
    Args:
        df: Projections DataFrame
        current_week: Current NFL week
        
    Returns:
        List of missing column names
    """
    missing_columns = []
    
    for week in range(2, current_week + 1):
        for round_name in ['2nd', '3rd', '4th']:
            col_name = f'Week{week}_2026_{round_name}'
            if col_name not in df.columns:
                missing_columns.append(col_name)
    
    return missing_columns


def add_missing_columns(df: pd.DataFrame, missing_columns: List[str]) -> pd.DataFrame:
    """
    Add missing weekly columns with tier-based values.
    
    Args:
        df: Projections DataFrame
        missing_columns: List of column names to add
        
    Returns:
        Updated DataFrame with new columns
    """
    df_updated = df.copy()
    
    for col_name in missing_columns:
        # Parse column name to extract round
        parts = col_name.split('_')
        if len(parts) >= 3:
            round_name = parts[2]  # '2nd', '3rd', or '4th'
            
            # Add column with tier-based values
            df_updated[col_name] = df_updated['Tier'].map(
                lambda tier: TIER_VALUES.get(tier, {}).get(round_name, 0)
            )
            
            logger.info(f"✓ Added column: {col_name}")
            
            # Log tier breakdown
            for tier in ['Early', 'Mid', 'Late']:
                count = len(df_updated[df_updated['Tier'] == tier])
                value = TIER_VALUES[tier][round_name]
                logger.info(f"  {tier} tier ({count} teams): {value} points")
    
    return df_updated


def backup_projections_file() -> str:
    """Create backup of projections file before modification."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backups/weekly_projections_backup_{timestamp}.csv'
    
    import shutil
    shutil.copy2(PROJECTIONS_FILE, backup_file)
    logger.info(f"✓ Created backup: {backup_file}")
    return backup_file


def update_weekly_projections() -> bool:
    """
    Main function to update weekly projections with missing columns.
    
    Returns:
        True if updates were made, False if no updates needed
    """
    logger.info("="*80)
    logger.info("AUTOMATIC WEEKLY PROJECTIONS UPDATE")
    logger.info("="*80)
    
    # Get through week (last week with complete data)
    current_week = get_through_week()
    logger.info(f"Through week (last scored): {current_week}")
    
    # Load projections file
    try:
        df = pd.read_csv(PROJECTIONS_FILE)
        logger.info(f"✓ Loaded projections: {len(df)} teams")
    except Exception as e:
        logger.error(f"Failed to load projections file: {e}")
        return False
    
    # Check for missing columns
    missing_columns = get_missing_columns(df, current_week)
    
    if not missing_columns:
        logger.info("✓ All weekly columns up to date - no updates needed")
        return False
    
    logger.info(f"Found {len(missing_columns)} missing columns:")
    for col in missing_columns:
        logger.info(f"  - {col}")
    
    # Create backup before making changes
    backup_file = backup_projections_file()
    
    # Add missing columns
    try:
        df_updated = add_missing_columns(df, missing_columns)
        
        # Save updated file
        df_updated.to_csv(PROJECTIONS_FILE, index=False)
        logger.info(f"✓ Updated projections file: {PROJECTIONS_FILE}")
        
        # Verify update
        df_verify = pd.read_csv(PROJECTIONS_FILE)
        logger.info(f"✓ Verification: {len(df_verify.columns)} total columns")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update projections: {e}")
        logger.info(f"Restore from backup: {backup_file}")
        return False


if __name__ == "__main__":
    success = update_weekly_projections()
    if success:
        print("\n🎉 Weekly projections updated successfully!")
    else:
        print("\n✅ No updates needed - projections are current")