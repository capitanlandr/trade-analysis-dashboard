"""
Pipeline Stage Validators
Provides validation for each pipeline stage with fail-fast behavior
"""

import logging
from pathlib import Path
import json
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class StageValidator:
    """Validation for each pipeline stage"""
    
    @staticmethod
    def validate_stage1_prerequisites(league_id: str):
        """
        Validate prerequisites before Stage 1 execution.
        
        Args:
            league_id: League ID to validate
            
        Raises:
            ValidationError: If prerequisites not met
        """
        logger.info("Validating Stage 1 prerequisites...")
        
        if not league_id or len(league_id) < 10:
            raise ValidationError(f"Invalid league ID: {league_id}")
        
        # Test API connectivity
        try:
            import requests
            response = requests.get("https://api.sleeper.app/v1/state/nfl", timeout=5)
            if response.status_code != 200:
                raise ValidationError("Cannot reach Sleeper API")
        except requests.exceptions.RequestException as e:
            raise ValidationError(f"Sleeper API unreachable: {e}")
        
        logger.info("✓ Stage 1 prerequisites validated")
    
    @staticmethod
    def validate_stage1_output(output_file: str):
        """
        Validate Stage 1 output before proceeding to Stage 2.
        
        Args:
            output_file: Path to trades_raw.json
            
        Raises:
            ValidationError: If validation fails
        """
        logger.info("Validating Stage 1 output...")
        
        if not Path(output_file).exists():
            raise ValidationError(f"Output file not found: {output_file}")
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        # Check required fields
        if 'trades' not in data:
            raise ValidationError("Missing 'trades' field in output")
        
        if len(data['trades']) == 0:
            raise ValidationError("No trades fetched - check league has trades")
        
        if 'metadata' not in data:
            raise ValidationError("Missing 'metadata' field in output")
        
        # Check for duplicates
        trade_ids = [t['transaction_id'] for t in data['trades']]
        if len(trade_ids) != len(set(trade_ids)):
            raise ValidationError("Duplicate transaction IDs found")
        
        # Check metadata completeness
        required_meta = ['league_id', 'season', 'total_trades']
        for field in required_meta:
            if field not in data['metadata']:
                raise ValidationError(f"Missing metadata field: {field}")
        
        logger.info(f"✓ Stage 1 validation passed: {len(data['trades'])} trades")
    
    @staticmethod
    def validate_stage2_prerequisites():
        """
        Validate prerequisites before Stage 2 execution.
        
        Raises:
            ValidationError: If prerequisites not met
        """
        logger.info("Validating Stage 2 prerequisites...")
        
        if not Path('trades_raw.json').exists():
            raise ValidationError("trades_raw.json not found - run Stage 1 first")
        
        logger.info("✓ Stage 2 prerequisites validated")
    
    @staticmethod
    def validate_stage2_output(output_file: str):
        """
        Validate Stage 2 output before proceeding to Stage 3.
        
        Args:
            output_file: Path to asset_transactions.csv
            
        Raises:
            ValidationError: If validation fails
        """
        logger.info("Validating Stage 2 output...")
        
        df = pd.read_csv(output_file)
        
        if len(df) == 0:
            raise ValidationError("No assets extracted - check trade data")
        
        # Check required columns
        required = ['trade_date', 'trade_id', 'asset_type', 'asset_name', 
                   'receiving_team', 'giving_team']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValidationError(f"Missing columns: {missing}")
        
        # Check for nulls in critical fields
        critical = ['asset_name', 'receiving_team', 'giving_team']
        for col in critical:
            null_count = df[col].isna().sum()
            if null_count > 0:
                raise ValidationError(f"{col} has {null_count} null values")
        
        # Validate asset types
        valid_types = ['player', 'pick', 'faab']
        invalid = df[~df['asset_type'].isin(valid_types)]
        if len(invalid) > 0:
            raise ValidationError(f"{len(invalid)} assets with invalid type")
        
        logger.info(f"✓ Stage 2 validation passed: {len(df)} assets")
    
    @staticmethod
    def validate_stage3_prerequisites():
        """
        Validate prerequisites before Stage 3 execution.
        
        Raises:
            ValidationError: If prerequisites not met
        """
        logger.info("Validating Stage 3 prerequisites...")
        
        required_files = [
            'asset_transactions.csv',
            'weekly_2026_pick_projections_expanded.csv',
            'sleeper_rookie_draft_2025.csv',
            'pick_origin_mapping.py'
        ]
        
        for file in required_files:
            if not Path(file).exists():
                raise ValidationError(f"Required file not found: {file}")
        
        logger.info("✓ Stage 3 prerequisites validated")
    
    @staticmethod
    def validate_stage3_output(output_file: str, max_zero_pct: float = 0.10):
        """
        Validate Stage 3 output with data quality checks.
        
        Args:
            output_file: Path to asset_values_cache.csv
            max_zero_pct: Maximum allowed percentage of zero values (default: 10%)
            
        Raises:
            ValidationError: If validation fails
        """
        logger.info("Validating Stage 3 output...")
        
        df = pd.read_csv(output_file)
        
        if len(df) == 0:
            raise ValidationError("No cached values - check Stage 2 output")
        
        # Check value columns exist
        required = ['value_at_trade', 'value_current', 
                   'value_source_at_trade', 'value_source_current']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValidationError(f"Missing columns: {missing}")
        
        # Data quality: Check zero value percentage
        zero_at_trade = (df['value_at_trade'] == 0).sum()
        zero_pct = zero_at_trade / len(df)
        
        if zero_pct > max_zero_pct:
            raise ValidationError(
                f"Too many zero values: {zero_pct:.1%} > {max_zero_pct:.1%}"
            )
        
        if zero_pct > 0.05:
            logger.warning(f"Zero value percentage: {zero_pct:.1%} ({zero_at_trade} assets)")
        
        logger.info(f"✓ Stage 3 validation passed: {len(df)} cached values")
    
    @staticmethod
    def validate_stage4_prerequisites():
        """
        Validate prerequisites before Stage 4 execution.
        
        Raises:
            ValidationError: If prerequisites not met
        """
        logger.info("Validating Stage 4 prerequisites...")
        
        if not Path('asset_values_cache.csv').exists():
            raise ValidationError("asset_values_cache.csv not found - run Stage 3 first")
        
        logger.info("✓ Stage 4 prerequisites validated")
    
    @staticmethod
    def validate_stage4_output(output_file: str):
        """
        Validate Stage 4 output.
        
        Args:
            output_file: Path to league_trades_analysis_pipeline.csv
            
        Raises:
            ValidationError: If validation fails
        """
        logger.info("Validating Stage 4 output...")
        
        df = pd.read_csv(output_file)
        
        if len(df) == 0:
            raise ValidationError("No trades analyzed - check Stage 3 output")
        
        # Check required columns
        required = ['trade_date', 'transaction_id', 'team_a', 'team_b',
                   'winner_at_trade', 'winner_current']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValidationError(f"Missing columns: {missing}")
        
        # Validate calculations for first few trades
        for idx, row in df.head(5).iterrows():
            # Check margin calculation
            calc_margin_then = abs(row['team_a_value_then'] - row['team_b_value_then'])
            if abs(calc_margin_then - row['margin_at_trade']) > 0.1:
                raise ValidationError(
                    f"Trade {row['transaction_id']}: margin_at_trade calculation error"
                )
        
        logger.info(f"✓ Stage 4 validation passed: {len(df)} trades analyzed")