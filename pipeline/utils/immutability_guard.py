"""
Immutability Guard System
Protects static season data from accidental modification
"""

import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import json
import hashlib
from datetime import datetime

from .season_config import get_season_config, ImmutabilityViolation

logger = logging.getLogger(__name__)


class ImmutabilityGuard:
    """
    Guards against modification of static season data.
    
    Provides verification methods to ensure static seasons remain immutable
    and detects any attempts to modify protected data.
    """
    
    def __init__(self):
        self.config = get_season_config()
        self._static_seasons = set(self.config.get_static_seasons())
        logger.debug(f"Initialized immutability guard for static seasons: {self._static_seasons}")
    
    def verify_no_static_modifications(self, records: List[Dict[str, Any]], operation: str = "modify") -> None:
        """
        Verify that no records belong to static seasons.
        
        Args:
            records: List of transaction records to check
            operation: Description of the operation being performed
            
        Raises:
            ImmutabilityViolation: If any record belongs to a static season
        """
        if not records:
            return
        
        logger.debug(f"Verifying {len(records)} records for static season modifications")
        
        # Check each record for static season violations
        violations = []
        for i, record in enumerate(records):
            season = record.get('season')
            if not season:
                # Records without season tags are allowed (will be tagged appropriately)
                continue
            
            if season in self._static_seasons:
                violations.append({
                    'record_index': i,
                    'season': season,
                    'transaction_id': record.get('transaction_id', 'unknown'),
                    'operation': operation
                })
        
        if violations:
            violation_details = []
            for v in violations:
                violation_details.append(
                    f"Record {v['record_index']} (transaction_id: {v['transaction_id']}) "
                    f"belongs to static season '{v['season']}'"
                )
            
            error_msg = (
                f"Immutability violation detected during '{operation}' operation. "
                f"Cannot modify {len(violations)} record(s) from static seasons:\n" +
                "\n".join(violation_details) +
                f"\nStatic seasons are immutable: {sorted(self._static_seasons)}"
            )
            
            logger.error(error_msg)
            raise ImmutabilityViolation(error_msg)
        
        logger.debug(f"✓ No static season modifications detected in {len(records)} records")
    
    def verify_season_operation_allowed(self, season_name: str, operation: str) -> None:
        """
        Verify that an operation is allowed on a specific season.
        
        Args:
            season_name: Name of the season
            operation: Type of operation (fetch, modify, update, delete)
            
        Raises:
            ImmutabilityViolation: If operation is not allowed on static season
        """
        if season_name in self._static_seasons:
            forbidden_operations = {'fetch', 'modify', 'update', 'delete', 'refetch', 'overwrite'}
            
            if operation.lower() in forbidden_operations:
                error_msg = (
                    f"Operation '{operation}' not allowed on static season '{season_name}'. "
                    f"Static seasons are immutable to preserve historical data integrity. "
                    f"Static seasons: {sorted(self._static_seasons)}"
                )
                logger.error(error_msg)
                raise ImmutabilityViolation(error_msg)
        
        logger.debug(f"✓ Operation '{operation}' allowed on season '{season_name}'")
    
    def verify_cumulative_file_integrity(self, file_path: str, expected_static_records: Optional[Dict[str, int]] = None) -> bool:
        """
        Verify that static season data in cumulative files hasn't been modified.
        
        Args:
            file_path: Path to cumulative file to check
            expected_static_records: Expected count of records per static season
            
        Returns:
            True if integrity is maintained, False otherwise
            
        Raises:
            ImmutabilityViolation: If static data has been modified
        """
        if not Path(file_path).exists():
            logger.debug(f"File {file_path} does not exist, skipping integrity check")
            return True
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            records = data.get('trades', data.get('transactions', data.get('waiver-wire', [])))
            metadata = data.get('metadata', {})
            
            # Count records by season
            season_counts = {}
            static_record_count = 0
            
            for record in records:
                season = record.get('season')
                if season:
                    season_counts[season] = season_counts.get(season, 0) + 1
                    if season in self._static_seasons:
                        static_record_count += 1
            
            # Check if expected counts match (if provided)
            if expected_static_records:
                for season, expected_count in expected_static_records.items():
                    if season in self._static_seasons:
                        actual_count = season_counts.get(season, 0)
                        if actual_count != expected_count:
                            error_msg = (
                                f"Static season '{season}' record count mismatch in {file_path}. "
                                f"Expected: {expected_count}, Actual: {actual_count}. "
                                f"This indicates potential data modification."
                            )
                            logger.error(error_msg)
                            raise ImmutabilityViolation(error_msg)
            
            # Verify metadata consistency
            metadata_counts = metadata.get('trades_by_season', 
                                         metadata.get('transactions_by_season', 
                                                    metadata.get('waiver-wire_by_season', {})))
            for season in self._static_seasons:
                if season in season_counts and season in metadata_counts:
                    if season_counts[season] != metadata_counts[season]:
                        error_msg = (
                            f"Metadata inconsistency for static season '{season}' in {file_path}. "
                            f"Record count: {season_counts[season]}, Metadata count: {metadata_counts[season]}"
                        )
                        logger.error(error_msg)
                        raise ImmutabilityViolation(error_msg)
            
            logger.debug(f"✓ File integrity verified for {file_path}. Static records: {static_record_count}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error verifying file integrity for {file_path}: {e}")
            return False
    
    def get_static_seasons(self) -> Set[str]:
        """Get set of static season names"""
        return self._static_seasons.copy()
    
    def is_season_static(self, season_name: str) -> bool:
        """Check if a season is static (immutable)"""
        return season_name in self._static_seasons
    
    def log_protection_status(self) -> None:
        """Log current immutability protection status"""
        logger.info(f"Immutability protection active for {len(self._static_seasons)} static seasons")
        for season in sorted(self._static_seasons):
            season_info = self.config.get_season_info(season)
            if season_info:
                logger.info(f"  - {season} (year: {season_info.year}, status: {season_info.status})")
            else:
                logger.info(f"  - {season} (no season info found)")


# Global immutability guard instance
_immutability_guard: Optional[ImmutabilityGuard] = None


def get_immutability_guard() -> ImmutabilityGuard:
    """
    Get global immutability guard instance (singleton pattern).
    
    Returns:
        ImmutabilityGuard instance
    """
    global _immutability_guard
    if _immutability_guard is None:
        _immutability_guard = ImmutabilityGuard()
    return _immutability_guard


def verify_no_static_modifications(records: List[Dict[str, Any]], operation: str = "modify") -> None:
    """
    Convenience function to verify no static season modifications.
    
    Args:
        records: List of transaction records to check
        operation: Description of the operation being performed
        
    Raises:
        ImmutabilityViolation: If any record belongs to a static season
    """
    guard = get_immutability_guard()
    guard.verify_no_static_modifications(records, operation)


def verify_season_operation_allowed(season_name: str, operation: str) -> None:
    """
    Convenience function to verify season operation is allowed.
    
    Args:
        season_name: Name of the season
        operation: Type of operation
        
    Raises:
        ImmutabilityViolation: If operation is not allowed on static season
    """
    guard = get_immutability_guard()
    guard.verify_season_operation_allowed(season_name, operation)


def verify_cumulative_file_integrity(file_path: str, expected_static_records: Optional[Dict[str, int]] = None) -> bool:
    """
    Convenience function to verify cumulative file integrity.
    
    Args:
        file_path: Path to cumulative file to check
        expected_static_records: Expected count of records per static season
        
    Returns:
        True if integrity is maintained, False otherwise
    """
    guard = get_immutability_guard()
    return guard.verify_cumulative_file_integrity(file_path, expected_static_records)


def log_immutability_status() -> None:
    """Log current immutability protection status"""
    guard = get_immutability_guard()
    guard.log_protection_status()