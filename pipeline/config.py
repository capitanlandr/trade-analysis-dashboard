"""
Pipeline Configuration Loader
Loads configuration from YAML files and provides type-safe access
"""

from dataclasses import dataclass
from typing import Dict, Optional
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API configuration"""
    base_url: str
    timeout: int
    max_retries: int
    retry_backoff: int


@dataclass
class GitHubConfig:
    """GitHub API configuration"""
    base_url: str
    repo: str
    values_path: str
    timeout: int
    max_retries: int
    retry_backoff: int


@dataclass
class TierValues:
    """Pick tier valuations"""
    early_first: int
    mid_first: int
    late_first: int


@dataclass
class ValuationConfig:
    """Valuation configuration"""
    tiers: TierValues
    faab_multiplier: float
    draft_completion_date: str
    season_start_date: str


@dataclass
class StorageConfig:
    """Storage configuration"""
    output_dir: Path
    backup_dir: Path
    logs_dir: Path
    metrics_dir: Path
    retention_days: int


@dataclass
class ValidationConfig:
    """Validation configuration"""
    max_zero_value_pct: float
    min_trades_expected: int
    fail_fast: bool
    git_commit_search_days: int


@dataclass
class PipelineConfig:
    """Complete pipeline configuration"""
    league_id: str
    league_name: str
    sleeper_api: APIConfig
    github_api: GitHubConfig
    valuations: ValuationConfig
    storage: StorageConfig
    validation: ValidationConfig
    log_level: str
    parallel_workers: int
    
    @classmethod
    def load(cls, config_file: str = 'config/default.yaml') -> 'PipelineConfig':
        """
        Load configuration from YAML file.
        
        Args:
            config_file: Path to YAML config file (default: 'config/default.yaml')
            
        Returns:
            PipelineConfig instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Parse sections
        league = data['league']
        api = data['api']
        vals = data['valuations']
        storage = data['storage']
        validation = data['validation']
        logging_cfg = data['logging']
        perf = data['performance']
        
        return cls(
            league_id=league['id'],
            league_name=league['name'],
            sleeper_api=APIConfig(**api['sleeper']),
            github_api=GitHubConfig(**api['github']),
            valuations=ValuationConfig(
                tiers=TierValues(**vals['tiers']),
                faab_multiplier=vals['faab_multiplier'],
                draft_completion_date=vals['draft_completion_date'],
                season_start_date=vals['season_start_date']
            ),
            storage=StorageConfig(
                output_dir=Path(storage['output_dir']),
                backup_dir=Path(storage['backup_dir']),
                logs_dir=Path(storage['logs_dir']),
                metrics_dir=Path(storage['metrics_dir']),
                retention_days=storage['retention_days']
            ),
            validation=ValidationConfig(**validation),
            log_level=logging_cfg['level'],
            parallel_workers=perf['parallel_workers']
        )
    
    def get_tier_value(self, pick_in_round: int) -> int:
        """Get tier value for pick position"""
        if pick_in_round <= 4:
            return self.valuations.tiers.early_first
        elif pick_in_round <= 8:
            return self.valuations.tiers.mid_first
        else:
            return self.valuations.tiers.late_first
    
    def get_output_path(self, filename: str) -> Path:
        """Get full path for output file"""
        return self.storage.output_dir / filename
    
    def validate(self):
        """Validate configuration values"""
        if not self.league_id:
            raise ValueError("League ID cannot be empty")
        
        if self.sleeper_api.timeout <= 0:
            raise ValueError("API timeout must be positive")
        
        if not (0 < self.validation.max_zero_value_pct <= 1):
            raise ValueError("max_zero_value_pct must be between 0 and 1")
        
        logger.info("✓ Configuration validated")


# Global config instance
_config: Optional[PipelineConfig] = None


def get_config() -> PipelineConfig:
    """
    Get global configuration instance (singleton pattern).
    
    Returns:
        PipelineConfig instance
    """
    global _config
    if _config is None:
        _config = PipelineConfig.load()
        _config.validate()
    return _config