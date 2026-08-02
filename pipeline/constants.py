"""
Pipeline Constants
Centralized constants for tier values, dates, and other configuration
"""

from enum import Enum
from datetime import datetime
from config import get_config


class PickTier(Enum):
    """2025 1st round pick tier labels - values come from config"""
    EARLY_FIRST = "early_first"  # Picks 1-4: Elite prospects
    MID_FIRST = "mid_first"       # Picks 5-8: High-quality starters
    LATE_FIRST = "late_first"     # Picks 9-12: Depth/development pieces
    
    @classmethod
    def get_value(cls, pick_in_round: int) -> int:
        """
        Get tier value from centralized config based on pick position.
        
        Args:
            pick_in_round: Pick number within round (1-12)
            
        Returns:
            Tier value as integer from config.yaml
            
        Example:
            >>> value = PickTier.get_value(2)
            >>> print(value)  # 5430 (from config.yaml)
        """
        config = get_config()
        
        if pick_in_round <= 4:
            return config.valuations.tiers.early_first
        elif pick_in_round <= 8:
            return config.valuations.tiers.mid_first
        else:
            return config.valuations.tiers.late_first
    
    @classmethod
    def get_tier_name(cls, pick_in_round: int) -> str:
        """
        Get tier name for reporting.
        
        Args:
            pick_in_round: Pick number within round (1-12)
            
        Returns:
            Tier name ('Early', 'Mid', 'Late')
        """
        if pick_in_round <= 4:
            return "Early"
        elif pick_in_round <= 8:
            return "Mid"
        else:
            return "Late"


class AssetType(Enum):
    """Types of fantasy assets"""
    PLAYER = 'player'
    PICK = 'pick'
    FAAB = 'faab'


class TradeType(Enum):
    """Types of trades"""
    TWO_TEAM = '2-team'
    MULTI_TEAM = 'multi-team'


class TradeStatus(Enum):
    """Trade status values"""
    COMPLETE = 'complete'
    PENDING = 'pending'
    FAILED = 'failed'


# Important dates
DRAFT_COMPLETION_DATE = datetime(2025, 5, 5)
SEASON_START_DATE = datetime(2025, 9, 3)

# Date DynastyProcess switched 2026 picks from tier generics ("2026 Early 1st")
# to exact per-slot entries ("2026 Pick 1.01"), once the 2026 draft order was
# determined. Verified by binary search over dynastyprocess/data commit history:
# the 2026-01-01 snapshot of files/values.csv carries 0 exact entries, 2026-01-02
# carries 60.
#
# Stage 3 values each asset from the DynastyProcess snapshot matching its TRADE
# date, so an exact-slot lookup cannot succeed for a 2026 pick traded before this
# date -- the string did not exist yet. Those trades fall back to team
# projections, which is the more faithful valuation anyway, since the draft order
# was still unknown at the time of the trade.
DYNASTYPROCESS_2026_EXACT_PICKS_DATE = datetime(2026, 1, 2)

# FAAB conversion rate
FAAB_VALUE_PER_DOLLAR = 1

# API endpoints
SLEEPER_API_BASE = "https://api.sleeper.app/v1"
GITHUB_API_BASE = "https://api.github.com"
DYNASTYPROCESS_REPO = "dynastyprocess/data"
DYNASTYPROCESS_VALUES_PATH = "files/values.csv"

# Output file names
class OutputFiles(Enum):
    """Standard output file names"""
    TRADES_RAW = 'trades_raw.json'
    ASSET_TRANSACTIONS = 'asset_transactions.csv'
    ASSET_VALUES_CACHE = 'asset_values_cache.csv'
    TRADES_ANALYSIS = 'league_trades_analysis_pipeline.csv'
    MULTITEAM_ANALYSIS = '3team_trades_analysis.json'
    MANAGER_RANKINGS = 'manager_rankings_pipeline.csv'
    TEAM_IDENTITY_MAPPING = 'team_identity_mapping.csv'


# Validation thresholds
MAX_ZERO_VALUE_PCT = 0.10  # Maximum 10% zero values acceptable
MIN_TRADES_EXPECTED = 1     # At least 1 trade required
GIT_COMMIT_SEARCH_DAYS = 7  # Days to search for Git commits

# Round name mappings
ROUND_ORDINALS = {
    1: '1st',
    2: '2nd', 
    3: '3rd',
    4: '4th',
    5: '5th'
}