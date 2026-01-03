"""
Season Configuration Management
Handles loading, validation, and access to multi-season configuration
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime
import yaml
import logging

logger = logging.getLogger(__name__)


@dataclass
class SeasonInfo:
    """Information about a specific season"""
    status: str  # "active", "static", "unavailable"
    league_id: str
    year: int
    description: str
    backfill_completed: Optional[bool] = None
    last_incremental_fetch: Optional[str] = None


@dataclass
class PipelineConfig:
    """Pipeline behavior configuration"""
    active_seasons: List[str]
    static_seasons: List[str]
    allow_static_refetch: bool
    cumulative_files: Dict[str, str]
    backup_before_append: bool
    validation: Dict[str, bool]


@dataclass
class SeasonConfiguration:
    """Complete season configuration"""
    seasons: Dict[str, SeasonInfo]
    pipeline: PipelineConfig
    schema_version: str
    last_updated: Optional[str]
    created_date: str
    migration_notes: str
    
    @classmethod
    def load(cls, config_file: str = 'config/seasons.yaml') -> 'SeasonConfiguration':
        """
        Load season configuration from YAML file.
        
        Args:
            config_file: Path to YAML config file (default: 'config/seasons.yaml')
            
        Returns:
            SeasonConfiguration instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Season config file not found: {config_file}")
        
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Parse seasons
        seasons = {}
        for season_name, season_data in data['seasons'].items():
            seasons[season_name] = SeasonInfo(**season_data)
        
        # Parse pipeline config
        pipeline_data = data['pipeline']
        pipeline = PipelineConfig(**pipeline_data)
        
        # Parse metadata
        metadata = data['metadata']
        
        config = cls(
            seasons=seasons,
            pipeline=pipeline,
            schema_version=metadata['schema_version'],
            last_updated=metadata.get('last_updated'),
            created_date=metadata['created_date'],
            migration_notes=metadata['migration_notes']
        )
        
        # Validate configuration
        config.validate()
        
        return config
    
    def validate(self):
        """
        Validate season configuration for consistency and safety.
        
        Raises:
            ValueError: If configuration is invalid
        """
        logger.info("Validating season configuration...")
        
        # Check for active vs static season conflicts (Requirement 10.3)
        active_set = set(self.pipeline.active_seasons)
        static_set = set(self.pipeline.static_seasons)
        
        conflicts = active_set.intersection(static_set)
        if conflicts:
            raise ValueError(f"Seasons cannot be both active and static: {conflicts}")
        
        # Validate that all referenced seasons exist (Requirement 10.4)
        all_referenced = active_set.union(static_set)
        defined_seasons = set(self.seasons.keys())
        
        missing_seasons = all_referenced - defined_seasons
        if missing_seasons:
            raise ValueError(f"Referenced seasons not defined: {missing_seasons}")
        
        # Validate active seasons have valid league IDs (Requirement 10.1)
        if self.pipeline.validation.get('require_league_ids', True):
            for season_name in self.pipeline.active_seasons:
                season = self.seasons[season_name]
                if not season.league_id or season.league_id.strip() == "":
                    raise ValueError(f"Active season '{season_name}' missing league_id")
                
                # Check for placeholder values (Requirement 10.2)
                placeholder_patterns = ['placeholder', 'TODO', 'CHANGE_ME', 'xxx']
                if any(pattern.lower() in season.league_id.lower() for pattern in placeholder_patterns):
                    raise ValueError(f"Active season '{season_name}' has placeholder league_id: {season.league_id}")
        
        # Validate season statuses
        valid_statuses = {'active', 'static', 'unavailable'}
        for season_name, season in self.seasons.items():
            if season.status not in valid_statuses:
                raise ValueError(f"Invalid status '{season.status}' for season '{season_name}'. Must be one of: {valid_statuses}")
        
        # Validate static seasons are not marked as active status
        for season_name in self.pipeline.static_seasons:
            season = self.seasons[season_name]
            if season.status == 'active':
                raise ValueError(f"Season '{season_name}' is in static_seasons list but has status 'active'")
        
        # Validate active seasons are marked with active status
        for season_name in self.pipeline.active_seasons:
            season = self.seasons[season_name]
            if season.status != 'active':
                raise ValueError(f"Season '{season_name}' is in active_seasons list but has status '{season.status}'")
        
        logger.info("✓ Season configuration validated successfully")
    
    def get_active_seasons(self) -> List[str]:
        """Get list of active season names"""
        return self.pipeline.active_seasons.copy()
    
    def get_static_seasons(self) -> List[str]:
        """Get list of static season names"""
        return self.pipeline.static_seasons.copy()
    
    def is_season_active(self, season_name: str) -> bool:
        """Check if a season is active"""
        return season_name in self.pipeline.active_seasons
    
    def is_season_static(self, season_name: str) -> bool:
        """Check if a season is static (immutable)"""
        return season_name in self.pipeline.static_seasons
    
    def get_season_info(self, season_name: str) -> Optional[SeasonInfo]:
        """Get information about a specific season"""
        return self.seasons.get(season_name)
    
    def get_league_id(self, season_name: str) -> Optional[str]:
        """Get league ID for a specific season"""
        season = self.get_season_info(season_name)
        return season.league_id if season else None
    
    def get_all_league_ids(self) -> Dict[str, str]:
        """Get mapping of season names to league IDs"""
        return {name: season.league_id for name, season in self.seasons.items()}
    
    def update_last_fetch_timestamp(self, season_name: str, timestamp: str):
        """
        Update the last incremental fetch timestamp for a season.
        
        Args:
            season_name: Name of the season
            timestamp: ISO format timestamp string
        """
        if season_name not in self.seasons:
            raise ValueError(f"Season '{season_name}' not found")
        
        self.seasons[season_name].last_incremental_fetch = timestamp
        logger.info(f"Updated last fetch timestamp for {season_name}: {timestamp}")
    
    def save(self, config_file: str = 'config/seasons.yaml'):
        """
        Save configuration back to YAML file.
        
        Args:
            config_file: Path to YAML config file
        """
        # Update metadata
        self.last_updated = datetime.utcnow().isoformat() + 'Z'
        
        # Prepare data structure for YAML
        data = {
            'seasons': {},
            'pipeline': {
                'active_seasons': self.pipeline.active_seasons,
                'static_seasons': self.pipeline.static_seasons,
                'allow_static_refetch': self.pipeline.allow_static_refetch,
                'cumulative_files': self.pipeline.cumulative_files,
                'backup_before_append': self.pipeline.backup_before_append,
                'validation': self.pipeline.validation
            },
            'metadata': {
                'schema_version': self.schema_version,
                'last_updated': self.last_updated,
                'created_date': self.created_date,
                'migration_notes': self.migration_notes
            }
        }
        
        # Convert season info to dict format
        for season_name, season_info in self.seasons.items():
            season_dict = {
                'status': season_info.status,
                'league_id': season_info.league_id,
                'year': season_info.year,
                'description': season_info.description
            }
            
            # Add optional fields if present
            if season_info.backfill_completed is not None:
                season_dict['backfill_completed'] = season_info.backfill_completed
            if season_info.last_incremental_fetch is not None:
                season_dict['last_incremental_fetch'] = season_info.last_incremental_fetch
            
            data['seasons'][season_name] = season_dict
        
        # Write to file
        config_path = Path(config_file)
        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Season configuration saved to {config_file}")


class ImmutabilityViolation(Exception):
    """Exception raised when attempting to modify static season data"""
    pass


# Global season config instance
_season_config: Optional[SeasonConfiguration] = None


def get_season_config() -> SeasonConfiguration:
    """
    Get global season configuration instance (singleton pattern).
    
    Returns:
        SeasonConfiguration instance
    """
    global _season_config
    if _season_config is None:
        # Try to find the config file in the pipeline directory
        import os
        if os.path.exists('config/seasons.yaml'):
            _season_config = SeasonConfiguration.load('config/seasons.yaml')
        elif os.path.exists('pipeline/config/seasons.yaml'):
            _season_config = SeasonConfiguration.load('pipeline/config/seasons.yaml')
        else:
            raise FileNotFoundError("Season config file not found. Expected at config/seasons.yaml or pipeline/config/seasons.yaml")
    return _season_config


def reload_season_config():
    """Force reload of season configuration from file"""
    global _season_config
    _season_config = None
    return get_season_config()


def validate_season_operation(season_name: str, operation: str = "modify"):
    """
    Validate that an operation is allowed on a season.
    
    Args:
        season_name: Name of the season
        operation: Type of operation (modify, fetch, etc.)
        
    Raises:
        ImmutabilityViolation: If operation violates immutability rules
    """
    config = get_season_config()
    
    if config.is_season_static(season_name):
        if operation in ['modify', 'fetch', 'update', 'delete']:
            raise ImmutabilityViolation(
                f"Cannot {operation} static season '{season_name}'. "
                f"Static seasons are immutable to preserve historical data integrity."
            )
    
    logger.debug(f"✓ Operation '{operation}' allowed on season '{season_name}'")