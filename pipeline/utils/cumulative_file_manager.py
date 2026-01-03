"""
Cumulative File Manager with Atomic Operations
Manages unified multi-season data files with atomic writes, deduplication, and backup creation
"""

import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import logging
from .backup import BackupManager
from .logging_config import get_logger, get_operation_logger
from .immutability_guard import verify_no_static_modifications, verify_season_operation_allowed, verify_cumulative_file_integrity

logger = get_logger(__name__)
op_logger = get_operation_logger(__name__)


class CumulativeFileError(Exception):
    """Base exception for cumulative file operations"""
    pass


class FileIntegrityError(CumulativeFileError):
    """Raised when file integrity validation fails"""
    pass


class DeduplicationError(CumulativeFileError):
    """Raised when deduplication logic encounters issues"""
    pass


class CumulativeFileManager:
    """
    Manages cumulative files with atomic operations, deduplication, and backup creation.
    
    Provides safe append-only operations for multi-season data with:
    - Atomic write operations using temporary files
    - Transaction ID-based deduplication
    - Automatic backup creation before modifications
    - File integrity validation
    - Metadata management for seasons and counts
    """
    
    def __init__(self, backup_manager: Optional[BackupManager] = None):
        """
        Initialize cumulative file manager.
        
        Args:
            backup_manager: Optional backup manager instance. If None, creates default.
        """
        self.backup_manager = backup_manager or BackupManager()
        self.schema_version = "2.0.0"
    
    def initialize_cumulative_file(self, file_path: Union[str, Path], 
                                 file_type: str = "trades") -> bool:
        """
        Initialize a new cumulative file with proper structure.
        
        Creates an empty cumulative file with metadata structure if it doesn't exist.
        If file exists, validates its structure and immutability constraints.
        
        Args:
            file_path: Path to the cumulative file
            file_type: Type of file ("trades" or "waiver-wire")
            
        Returns:
            True if initialization successful, False otherwise
            
        Raises:
            CumulativeFileError: If initialization fails
            ImmutabilityViolation: If existing file violates immutability constraints
        """
        file_path = Path(file_path)
        
        try:
            if file_path.exists():
                logger.info(f"Cumulative file exists, validating structure: {file_path}")
                
                # Verify file integrity including immutability constraints
                integrity_valid = self.verify_file_integrity(file_path)
                
                # Additional immutability check for existing files
                immutability_valid = verify_cumulative_file_integrity(str(file_path))
                
                return integrity_valid and immutability_valid
            
            logger.info(f"Creating new cumulative file: {file_path}")
            
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize empty cumulative file structure
            initial_data = {
                "metadata": {
                    "schema_version": self.schema_version,
                    "last_updated": datetime.utcnow().isoformat() + "Z",
                    "seasons_included": [],
                    f"total_{file_type}": 0,
                    f"{file_type}_by_season": {},
                    "season_info": {}
                },
                file_type: []
            }
            
            # Write initial structure atomically
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', 
                                           dir=file_path.parent, delete=False) as temp_file:
                json.dump(initial_data, temp_file, indent=2)
                temp_path = Path(temp_file.name)
            
            # Atomic rename
            temp_path.rename(file_path)
            
            logger.info(f"✓ Initialized cumulative file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize cumulative file {file_path}: {e}")
            raise CumulativeFileError(f"Initialization failed: {e}")
    
    def append_to_cumulative_file(self, file_path: Union[str, Path], 
                                new_records: List[Dict[str, Any]], 
                                season: str) -> Dict[str, Any]:
        """
        Atomically append new records to cumulative file with deduplication.
        
        Performs the following operations atomically:
        1. Verify immutability constraints (no static season modifications)
        2. Validate season operation is allowed
        3. Create backup of existing file
        4. Load existing data
        5. Deduplicate new records against existing transaction_ids
        6. Append new records with season tags
        7. Update metadata (counts, timestamps, season info)
        8. Write to temporary file and atomic rename
        9. Verify file integrity including immutability constraints
        
        Args:
            file_path: Path to the cumulative file
            new_records: List of new records to append
            season: Season identifier for tagging records
            
        Returns:
            Dictionary with operation results:
            {
                "records_added": int,
                "duplicates_skipped": int,
                "total_records": int,
                "backup_path": str
            }
            
        Raises:
            CumulativeFileError: If append operation fails
            DeduplicationError: If deduplication logic fails
            ImmutabilityViolation: If attempting to modify static season data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise CumulativeFileError(f"Cumulative file not found: {file_path}")
        
        if not new_records:
            logger.info("No new records to append")
            return {
                "records_added": 0,
                "duplicates_skipped": 0,
                "total_records": 0,
                "backup_path": None
            }
        
        try:
            # IMMUTABILITY GUARD: Verify season operation is allowed
            verify_season_operation_allowed(season, "append")
            
            # IMMUTABILITY GUARD: Verify no records belong to static seasons
            verify_no_static_modifications(new_records, f"append to {file_path}")
            
            # Create backup before modification
            backup_path = self.backup_manager.backup_file(
                str(file_path), 
                f"cumulative_{file_path.stem}"
            )
            
            # Load existing data
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Validate file structure
            if not self._validate_file_structure(data, file_path):
                raise FileIntegrityError(f"Invalid file structure: {file_path}")
            
            # Determine data key (trades, waiver-wire, etc.)
            data_key = self._get_data_key(data)
            
            # Get existing transaction IDs for deduplication
            existing_ids = {record.get('transaction_id') for record in data[data_key] 
                          if record.get('transaction_id')}
            
            # Process new records with deduplication and season tagging
            records_added = 0
            duplicates_skipped = 0
            
            for record in new_records:
                # Validate required fields
                if not self._validate_record(record):
                    logger.warning(f"Skipping invalid record: {record}")
                    continue
                
                transaction_id = record.get('transaction_id')
                
                # Check for duplicates
                if transaction_id in existing_ids:
                    duplicates_skipped += 1
                    logger.debug(f"Skipping duplicate transaction_id: {transaction_id}")
                    continue
                
                # Tag record with season
                tagged_record = record.copy()
                tagged_record['season'] = season
                
                # Add to data
                data[data_key].append(tagged_record)
                existing_ids.add(transaction_id)
                records_added += 1
            
            # Update metadata
            self._update_metadata(data, season, records_added, data_key)
            
            # Write atomically using temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', 
                                           dir=file_path.parent, delete=False) as temp_file:
                json.dump(data, temp_file, indent=2)
                temp_path = Path(temp_file.name)
            
            # Atomic rename
            temp_path.rename(file_path)
            
            # Verify integrity after write (including immutability constraints)
            if not self.verify_file_integrity(file_path):
                # Restore from backup on integrity failure
                if backup_path:
                    self.backup_manager.restore_backup(backup_path.name, str(file_path))
                raise FileIntegrityError(f"File integrity check failed after write: {file_path}")
            
            result = {
                "records_added": records_added,
                "duplicates_skipped": duplicates_skipped,
                "total_records": len(data[data_key]),
                "backup_path": str(backup_path) if backup_path else None
            }
            
            # Comprehensive operation logging (Requirement 5.5, 6.3, 12.5)
            logger.info(f"✓ Appended to {file_path}: {records_added} new, "
                       f"{duplicates_skipped} duplicates skipped, "
                       f"{result['total_records']} total")
            
            # Log detailed deduplication metrics
            if len(new_records) > 0:
                op_logger.log_deduplication(
                    season=season,
                    total=len(new_records),
                    duplicates=duplicates_skipped,
                    kept=records_added
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to append to cumulative file {file_path}: {e}")
            
            # Attempt to restore from backup on failure
            if backup_path:
                try:
                    self.backup_manager.restore_backup(backup_path.name, str(file_path))
                    logger.info(f"Restored from backup after failure: {backup_path.name}")
                except Exception as restore_error:
                    logger.error(f"Failed to restore from backup: {restore_error}")
            
            raise CumulativeFileError(f"Append operation failed: {e}")
    
    def verify_file_integrity(self, file_path: Union[str, Path]) -> bool:
        """
        Verify the integrity and structure of a cumulative file.
        
        Validates:
        - File exists and is readable
        - Valid JSON structure
        - Required metadata fields present
        - Data array exists and is valid
        - Transaction ID uniqueness
        - Season tag consistency
        - Metadata counts match actual data
        - Immutability constraints for static seasons
        
        Args:
            file_path: Path to the cumulative file
            
        Returns:
            True if file integrity is valid, False otherwise
            
        Raises:
            ImmutabilityViolation: If static season data has been modified
        """
        file_path = Path(file_path)
        
        try:
            if not file_path.exists():
                logger.error(f"File does not exist: {file_path}")
                return False
            
            # Load and parse JSON
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Validate basic structure
            if not self._validate_file_structure(data, file_path):
                return False
            
            # Get data key and records
            data_key = self._get_data_key(data)
            records = data[data_key]
            
            # Validate transaction ID uniqueness
            transaction_ids = [r.get('transaction_id') for r in records 
                             if r.get('transaction_id')]
            if len(transaction_ids) != len(set(transaction_ids)):
                logger.error(f"Duplicate transaction IDs found in {file_path}")
                return False
            
            # Validate season tags
            seasons_in_data = {r.get('season') for r in records if r.get('season')}
            seasons_in_metadata = set(data['metadata'].get('seasons_included', []))
            
            if seasons_in_data != seasons_in_metadata:
                logger.error(f"Season mismatch in {file_path}: "
                           f"data={seasons_in_data}, metadata={seasons_in_metadata}")
                return False
            
            # Validate metadata counts
            total_key = f"total_{data_key}"
            expected_total = data['metadata'].get(total_key, 0)
            actual_total = len(records)
            
            if expected_total != actual_total:
                logger.error(f"Count mismatch in {file_path}: "
                           f"metadata={expected_total}, actual={actual_total}")
                return False
            
            # Validate per-season counts
            by_season_key = f"{data_key}_by_season"
            expected_by_season = data['metadata'].get(by_season_key, {})
            
            for season in seasons_in_data:
                actual_count = sum(1 for r in records if r.get('season') == season)
                expected_count = expected_by_season.get(season, 0)
                
                if actual_count != expected_count:
                    logger.error(f"Season count mismatch in {file_path} for {season}: "
                               f"metadata={expected_count}, actual={actual_count}")
                    return False
            
            # IMMUTABILITY GUARD: Verify static season data integrity
            try:
                immutability_valid = verify_cumulative_file_integrity(str(file_path), expected_by_season)
                if not immutability_valid:
                    logger.error(f"Immutability check failed for {file_path}")
                    return False
            except Exception as e:
                logger.error(f"Immutability verification failed for {file_path}: {e}")
                # Re-raise ImmutabilityViolation exceptions to preserve error context
                if "ImmutabilityViolation" in str(type(e)):
                    raise
                return False
            
            logger.debug(f"✓ File integrity verified: {file_path}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"File integrity check failed for {file_path}: {e}")
            return False
    
    def _validate_file_structure(self, data: Dict[str, Any], file_path: Path) -> bool:
        """Validate basic cumulative file structure"""
        if not isinstance(data, dict):
            logger.error(f"File is not a JSON object: {file_path}")
            return False
        
        if 'metadata' not in data:
            logger.error(f"Missing metadata section: {file_path}")
            return False
        
        metadata = data['metadata']
        required_meta_fields = ['schema_version', 'last_updated', 'seasons_included']
        
        for field in required_meta_fields:
            if field not in metadata:
                logger.error(f"Missing metadata field '{field}': {file_path}")
                return False
        
        # Find data key (trades, waiver-wire, etc.)
        data_keys = [key for key in data.keys() if key != 'metadata']
        if len(data_keys) != 1:
            logger.error(f"Expected exactly one data key, found {data_keys}: {file_path}")
            return False
        
        data_key = data_keys[0]
        if not isinstance(data[data_key], list):
            logger.error(f"Data section '{data_key}' is not a list: {file_path}")
            return False
        
        return True
    
    def _get_data_key(self, data: Dict[str, Any]) -> str:
        """Get the data key (trades, waiver-wire, etc.) from cumulative file"""
        data_keys = [key for key in data.keys() if key != 'metadata']
        if len(data_keys) != 1:
            raise CumulativeFileError(f"Expected exactly one data key, found {data_keys}")
        return data_keys[0]
    
    def _validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate that a record has required fields"""
        required_fields = ['transaction_id', 'league_id']
        
        for field in required_fields:
            if field not in record or not record[field]:
                logger.warning(f"Record missing required field '{field}': {record}")
                return False
        
        return True
    
    def _update_metadata(self, data: Dict[str, Any], season: str, 
                        records_added: int, data_key: str) -> None:
        """Update metadata after adding records"""
        metadata = data['metadata']
        
        # Update timestamp
        metadata['last_updated'] = datetime.utcnow().isoformat() + "Z"
        
        # Update seasons included (only if we actually added records for this season)
        if records_added > 0 and season not in metadata['seasons_included']:
            metadata['seasons_included'].append(season)
            metadata['seasons_included'].sort()
        
        # Update total count
        total_key = f"total_{data_key}"
        metadata[total_key] = len(data[data_key])
        
        # Update per-season counts
        by_season_key = f"{data_key}_by_season"
        if by_season_key not in metadata:
            metadata[by_season_key] = {}
        
        season_count = sum(1 for r in data[data_key] if r.get('season') == season)
        metadata[by_season_key][season] = season_count
        
        # Update season info if not exists (only if we added records)
        if 'season_info' not in metadata:
            metadata['season_info'] = {}
        
        if records_added > 0 and season not in metadata['season_info']:
            metadata['season_info'][season] = {
                "status": "active",  # Default, can be updated by caller
                "last_fetched": metadata['last_updated']
            }
        else:
            metadata['season_info'][season]['last_fetched'] = metadata['last_updated']
    
    def validate_immutability_constraints(self, file_path: Union[str, Path]) -> bool:
        """
        Validate immutability constraints for a cumulative file.
        
        This method provides a dedicated interface for checking immutability
        constraints without performing full file integrity validation.
        
        Args:
            file_path: Path to the cumulative file
            
        Returns:
            True if immutability constraints are satisfied, False otherwise
            
        Raises:
            ImmutabilityViolation: If static season data has been modified
        """
        try:
            return verify_cumulative_file_integrity(str(file_path))
        except Exception as e:
            logger.error(f"Immutability validation failed for {file_path}: {e}")
            # Re-raise ImmutabilityViolation exceptions to preserve error context
            if "ImmutabilityViolation" in str(type(e)):
                raise
            return False
    
    def check_season_modification_allowed(self, season: str, operation: str = "modify") -> bool:
        """
        Check if a modification operation is allowed on a specific season.
        
        Args:
            season: Season identifier
            operation: Type of operation (modify, append, update, etc.)
            
        Returns:
            True if operation is allowed, False if season is static
            
        Raises:
            ImmutabilityViolation: If operation is not allowed on static season
        """
        try:
            verify_season_operation_allowed(season, operation)
            return True
        except Exception as e:
            logger.debug(f"Season operation check failed for {season}: {e}")
            # Re-raise ImmutabilityViolation exceptions to preserve error context
            if "ImmutabilityViolation" in str(type(e)):
                raise
            return False