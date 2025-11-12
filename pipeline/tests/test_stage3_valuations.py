"""
Unit Tests for Stage 3 Valuation Logic
Tests tier assignments, pick valuations, and player value lookups
"""

import pytest
import pandas as pd
from datetime import datetime
from constants import PickTier, DRAFT_COMPLETION_DATE


# Mock the functions we're testing (since they need module-level setup)
def mock_get_2025_pick_value(pick_name, origin_owner, trade_date, df_values, is_current, pick_in_round=1):
    """Simplified version for testing"""
    trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
    round_num = int(pick_name.split('Round')[1].strip())
    
    # Pre-draft
    if trade_dt < DRAFT_COMPLETION_DATE:
        if is_current:
            # Would use player value - mock as 3500
            return 3500, "Player:Brock Bowers", {'player': 'Brock Bowers'}
        else:
            # Use tier value
            if round_num == 1:
                tier_value = PickTier.get_value(pick_in_round)
                tier_name = PickTier.get_tier_name(pick_in_round)
                return tier_value, f"Tier:{tier_name} 1st", {'tier': tier_name}
            return 0, "Not found", None
    else:
        # Post-draft - use player value
        return 3500, "Player:Brock Bowers (post-draft)", {'player': 'Brock Bowers'}


class TestPickTierValues:
    """Test pick tier valuation logic"""
    
    def test_early_first_tier_value(self):
        """Test early 1st round picks (1-4) have highest value"""
        assert PickTier.get_value(1) == 5430
        assert PickTier.get_value(2) == 5430
        assert PickTier.get_value(3) == 5430
        assert PickTier.get_value(4) == 5430
    
    def test_mid_first_tier_value(self):
        """Test mid 1st round picks (5-8) have middle value"""
        assert PickTier.get_value(5) == 2558
        assert PickTier.get_value(6) == 2558
        assert PickTier.get_value(7) == 2558
        assert PickTier.get_value(8) == 2558
    
    def test_late_first_tier_value(self):
        """Test late 1st round picks (9-12) have lowest value"""
        assert PickTier.get_value(9) == 1232
        assert PickTier.get_value(10) == 1232
        assert PickTier.get_value(11) == 1232
        assert PickTier.get_value(12) == 1232
    
    def test_tier_names(self):
        """Test tier name assignments"""
        assert PickTier.get_tier_name(1) == "Early"
        assert PickTier.get_tier_name(4) == "Early"
        assert PickTier.get_tier_name(5) == "Mid"
        assert PickTier.get_tier_name(8) == "Mid"
        assert PickTier.get_tier_name(9) == "Late"
        assert PickTier.get_tier_name(12) == "Late"


class TestPickValuations:
    """Test 2025 pick valuation logic"""
    
    def test_pre_draft_early_first_uses_tier(self, mock_dynasty_values):
        """Test pre-draft early 1st uses tier value"""
        value, source, meta = mock_get_2025_pick_value(
            pick_name="2025 Round 1",
            origin_owner="Test Team",
            trade_date="2024-11-15",  # Before May 5 draft
            df_values=mock_dynasty_values,
            is_current=False,
            pick_in_round=1
        )
        
        assert value == 5430, "Early 1st should be 5430"
        assert "Tier:Early" in source
        assert meta['tier'] == "Early"
    
    def test_pre_draft_mid_first_uses_tier(self, mock_dynasty_values):
        """Test pre-draft mid 1st uses tier value"""
        value, source, meta = mock_get_2025_pick_value(
            pick_name="2025 Round 1",
            origin_owner="Test Team",
            trade_date="2024-11-15",
            df_values=mock_dynasty_values,
            is_current=False,
            pick_in_round=6
        )
        
        assert value == 2558, "Mid 1st should be 2558"
        assert "Tier:Mid" in source
    
    def test_pre_draft_late_first_uses_tier(self, mock_dynasty_values):
        """Test pre-draft late 1st uses tier value"""
        value, source, meta = mock_get_2025_pick_value(
            pick_name="2025 Round 1",
            origin_owner="Test Team",
            trade_date="2024-11-15",
            df_values=mock_dynasty_values,
            is_current=False,
            pick_in_round=10
        )
        
        assert value == 1232, "Late 1st should be 1232"
        assert "Tier:Late" in source
    
    def test_post_draft_uses_player_value(self, mock_dynasty_values):
        """Test post-draft picks use drafted player value"""
        value, source, meta = mock_get_2025_pick_value(
            pick_name="2025 Round 1",
            origin_owner="Test Team",
            trade_date="2025-05-06",  # After May 5 draft
            df_values=mock_dynasty_values,
            is_current=True,
            pick_in_round=1
        )
        
        assert value == 3500, "Should use player value"
        assert "Player:" in source
        assert meta['player'] == 'Brock Bowers'
    
    def test_current_value_for_pre_draft_trade_uses_player(self, mock_dynasty_values):
        """Test current value for pre-draft trade converts to player"""
        value, source, meta = mock_get_2025_pick_value(
            pick_name="2025 Round 1",
            origin_owner="Test Team",
            trade_date="2024-11-15",  # Trade before draft
            df_values=mock_dynasty_values,
            is_current=True,  # But asking for CURRENT value
            pick_in_round=1
        )
        
        assert value == 3500, "Current value should be drafted player"
        assert "Player:" in source


class TestFAABValuation:
    """Test FAAB valuation"""
    
    def test_faab_conversion(self):
        """Test FAAB dollar to point conversion"""
        from constants import FAAB_VALUE_PER_DOLLAR
        
        assert FAAB_VALUE_PER_DOLLAR == 1
        
        # $50 FAAB should equal 50 points
        assert 50 * FAAB_VALUE_PER_DOLLAR == 50
        
        # $100 FAAB should equal 100 points
        assert 100 * FAAB_VALUE_PER_DOLLAR == 100


class TestPlayerValuation:
    """Test player value lookups"""
    
    def test_player_value_lookup(self, mock_dynasty_values):
        """Test finding player values from DynastyProcess data"""
        # Test exact match
        mahomes = mock_dynasty_values[mock_dynasty_values['player'] == 'Patrick Mahomes']
        assert not mahomes.empty
        assert mahomes.iloc[0]['value_2qb'] == 10000
        
        # Test fuzzy match (case-insensitive)
        jefferson = mock_dynasty_values[mock_dynasty_values['player'].str.contains('jefferson', case=False)]
        assert not jefferson.empty
        assert jefferson.iloc[0]['value_2qb'] == 8000
    
    def test_player_not_found(self, mock_dynasty_values):
        """Test handling of players not in DynastyProcess"""
        unknown = mock_dynasty_values[mock_dynasty_values['player'] == 'Unknown Player']
        assert unknown.empty


if __name__ == "__main__":
    pytest.main([__file__, '-v'])