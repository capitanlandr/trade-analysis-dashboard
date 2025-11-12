"""
Unit Tests for Stage 4 Calculation Logic
Tests trade margin calculations, swing calculations, and winner determination
"""

import pytest
import pandas as pd
import json
import numpy as np
from utils.metrics import LocalMetrics


class TestTradeMarginCalculations:
    """Test margin calculation logic"""
    
    def test_margin_at_trade_calculation(self):
        """Test margin_at_trade is absolute difference"""
        team_a_value = 10000
        team_b_value = 7500
        
        margin = abs(team_a_value - team_b_value)
        assert margin == 2500
        
        # Test reverse
        margin_reverse = abs(team_b_value - team_a_value)
        assert margin_reverse == 2500
    
    def test_margin_current_calculation(self):
        """Test margin_current with value changes"""
        # Original values
        team_a_then = 10000
        team_b_then = 7500
        
        # Current values
        team_a_now = 9000  # Decreased
        team_b_now = 8500  # Increased
        
        margin_then = abs(team_a_then - team_b_then)
        margin_now = abs(team_a_now - team_b_now)
        
        assert margin_then == 2500
        assert margin_now == 500  # Margin narrowed


class TestSwingCalculations:
    """Test swing margin calculations"""
    
    def test_swing_when_winner_changes(self):
        """Test swing calculation when winner changes"""
        # Team A won at trade
        team_a_then = 10000
        team_b_then = 7500
        
        # Team B winning now
        team_a_now = 8000
        team_b_now = 9000
        
        # Original margin: 2500 in favor of A
        # Current margin: 1000 in favor of B
        # Swing: went from +2500 A to -1000 A = 3500 point swing
        
        margin_then = team_a_then - team_b_then  # 2500
        margin_now = team_a_now - team_b_now     # -1000
        swing = margin_now - margin_then         # -3500
        
        assert abs(swing) == 3500
    
    def test_swing_when_winner_stays_same_but_margin_increases(self):
        """Test swing when same winner but margin grows"""
        # Team A won at trade
        team_a_then = 10000
        team_b_then = 7500
        
        # Team A still winning but by more
        team_a_now = 12000
        team_b_now = 8000
        
        margin_then = team_a_then - team_b_then  # 2500
        margin_now = team_a_now - team_b_now     # 4000
        swing = margin_now - margin_then         # 1500 (positive = margin grew)
        
        assert swing == 1500
    
    def test_swing_with_tied_trade(self):
        """Test swing calculation with even trades"""
        team_a_then = 10000
        team_b_then = 10000
        
        team_a_now = 11000
        team_b_now = 10500
        
        margin_then = abs(team_a_then - team_b_then)  # 0
        margin_now = abs(team_a_now - team_b_now)     # 500
        
        assert margin_then == 0
        assert margin_now == 500


class TestWinnerDetermination:
    """Test winner determination logic"""
    
    def test_winner_at_trade(self):
        """Test determining winner at trade time"""
        team_a_value = 10000
        team_b_value = 7500
        
        winner = 'Team A' if team_a_value > team_b_value else 'Team B'
        assert winner == 'Team A'
        
        # Test tie
        winner_tie = 'Tie' if team_a_value == team_a_value else ('Team A' if team_a_value > team_a_value else 'Team B')
        assert winner_tie == 'Tie'
    
    def test_winner_current(self):
        """Test determining current winner after value changes"""
        team_a_now = 8000
        team_b_now = 9000
        
        winner = 'Team A' if team_a_now > team_b_now else 'Team B'
        assert winner == 'Team B'


class TestTradeAggregation:
    """Test trade aggregation from asset level to trade level"""
    
    def test_aggregate_assets_by_trade(self, mock_cached_values):
        """Test grouping assets by trade_id"""
        df = mock_cached_values
        
        # Group by trade
        trades = {}
        for _, row in df.iterrows():
            trade_id = row['trade_id']
            if trade_id not in trades:
                trades[trade_id] = {
                    'team_a_value': 0,
                    'team_b_value': 0
                }
            
            if row['receiving_team'] == 'Manager A':
                trades[trade_id]['team_a_value'] += row['value_at_trade']
            else:
                trades[trade_id]['team_b_value'] += row['value_at_trade']
        
        # Should have 1 trade
        assert len(trades) == 1
        
        # Get the single trade_id (now an integer: 1001)
        trade_id = list(trades.keys())[0]
        
        # Team A got Justin Jefferson (7500)
        # Team B got 2025 Round 1 (5430)
        assert trades[trade_id]['team_a_value'] == 7500
        assert trades[trade_id]['team_b_value'] == 5430
    
    def test_value_change_calculation(self, mock_cached_values):
        """Test calculating value change for each team"""
        df = mock_cached_values
        
        # Justin Jefferson: 7500 → 8000 (+500)
        jj = df[df['asset_name'] == 'Justin Jefferson'].iloc[0]
        change_a = jj['value_current'] - jj['value_at_trade']
        assert change_a == 500
        
        # 2025 Round 1: 5430 → 3500 (-1930)
        pick = df[df['asset_name'] == '2025 Round 1'].iloc[0]
        change_b = pick['value_current'] - pick['value_at_trade']
        assert change_b == -1930


class TestDataQuality:
    """Test data quality checks"""
    
    def test_no_null_values_in_critical_fields(self, mock_cached_values):
        """Test that critical fields have no null values"""
        df = mock_cached_values
        
        critical_fields = ['asset_name', 'value_at_trade', 'value_current', 
                          'receiving_team', 'giving_team']
        
        for field in critical_fields:
            assert df[field].notna().all(), f"{field} should have no null values"
    
    def test_values_are_numeric(self, mock_cached_values):
        """Test that value fields are numeric"""
        df = mock_cached_values
        
        assert pd.api.types.is_numeric_dtype(df['value_at_trade'])
        assert pd.api.types.is_numeric_dtype(df['value_current'])
    
    def test_values_are_non_negative(self, mock_cached_values):
        """Test that values are non-negative"""
        df = mock_cached_values
        
        assert (df['value_at_trade'] >= 0).all()
        assert (df['value_current'] >= 0).all()


class TestJSONSerialization:
    """Test JSON serialization with numpy types"""
    
    def test_fixture_contains_numpy_types(self, mock_cached_values):
        """Verify test fixtures use numpy types like production"""
        df = mock_cached_values
        
        # Check that numeric columns are numpy types
        assert isinstance(df['trade_id'].iloc[0], (np.integer, np.int64))
        assert isinstance(df['value_at_trade'].iloc[0], (np.integer, np.int64))
        assert isinstance(df['value_current'].iloc[0], (np.integer, np.int64))
    
    def test_multiteam_fixture_contains_numpy_types(self, mock_multiteam_cached_values):
        """Verify multi-team fixture uses numpy types"""
        df = mock_multiteam_cached_values
        
        assert isinstance(df['trade_id'].iloc[0], (np.integer, np.int64))
        assert isinstance(df['value_at_trade'].iloc[0], (np.integer, np.int64))
    
    def test_analyze_multiteam_json_serializable(self, mock_multiteam_cached_values):
        """Test that analyze_multiteam output is JSON serializable"""
        from stage4_final import analyze_multiteam
        
        results = analyze_multiteam(mock_multiteam_cached_values)
        
        # Should not raise TypeError
        json_str = json.dumps(results)
        assert json_str is not None
        assert len(json_str) > 0
        
        # Verify structure
        assert len(results) == 1
        assert 'trade_id' in results[0]
        assert 'date' in results[0]
        assert 'teams' in results[0]
        
        # Verify trade_id is converted to int (not numpy.int64)
        assert isinstance(results[0]['trade_id'], int)
        assert not isinstance(results[0]['trade_id'], np.integer)
    
    def test_analyze_2team_with_numpy_types(self, mock_cached_values):
        """Test 2-team analysis handles numpy types correctly"""
        from stage4_final import analyze_2team_trades
        
        df_result = analyze_2team_trades(mock_cached_values)
        
        # DataFrame should be JSON serializable when converted to dict
        result_dict = df_result.to_dict('records')[0]
        
        # Should not raise TypeError
        json_str = json.dumps(result_dict)
        assert json_str is not None
    
    def test_metrics_with_numpy_types(self, mock_cached_values, tmp_path):
        """Test metrics system handles numpy types from pandas operations"""
        metrics = LocalMetrics(metrics_dir=str(tmp_path))
        
        # Simulate pandas operations that produce numpy types
        df = mock_cached_values
        
        # These return numpy.int64
        metrics.record('count.trades', df['trade_id'].nunique())
        metrics.record('count.total_assets', len(df))
        
        # These return numpy.float64
        metrics.record('avg.value_at_trade', df['value_at_trade'].mean())
        metrics.record('max.value_current', df['value_current'].max())
        
        # Should not raise TypeError when saving
        metrics.save()
        
        # Verify file was created and is valid JSON
        metrics_files = list(tmp_path.glob('run_*.json'))
        assert len(metrics_files) == 1
        
        with open(metrics_files[0]) as f:
            loaded = json.load(f)
            assert 'count.trades' in loaded
            # Verify values are native Python types
            assert isinstance(loaded['count.trades']['value'], int)
            assert isinstance(loaded['avg.value_at_trade']['value'], float)


class TestCSVRoundTrip:
    """Test that data behaves like production CSV workflow"""
    
    def test_csv_roundtrip_creates_numpy_types(self, mock_cached_values, tmp_path):
        """Verify CSV read creates numpy types like production"""
        df_original = mock_cached_values
        
        # Write to CSV and read back
        csv_path = tmp_path / "test_cache.csv"
        df_original.to_csv(csv_path, index=False)
        df_loaded = pd.read_csv(csv_path)
        
        # Verify loaded data has numpy types
        assert isinstance(df_loaded['trade_id'].iloc[0], (np.integer, np.int64))
        assert isinstance(df_loaded['value_at_trade'].iloc[0], (np.integer, np.int64))
    
    def test_stage4_with_csv_loaded_data(self, mock_cached_values, tmp_path):
        """Integration test: Stage 4 with CSV-loaded data like production"""
        from stage4_final import analyze_2team_trades
        
        # Simulate production: write to CSV, then read
        csv_path = tmp_path / "test_cache.csv"
        mock_cached_values.to_csv(csv_path, index=False)
        df_loaded = pd.read_csv(csv_path)
        
        # Run stage4 analysis
        result = analyze_2team_trades(df_loaded)
        
        # Convert to dict and verify JSON serializable
        result_dict = result.to_dict('records')
        json_str = json.dumps(result_dict)
        assert json_str is not None


if __name__ == "__main__":
    pytest.main([__file__, '-v'])