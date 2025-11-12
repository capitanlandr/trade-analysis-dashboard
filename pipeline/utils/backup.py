"""
Backup Manager for Pipeline Outputs
Provides automated backups with retention policy
"""

import shutil
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class BackupManager:
    """Manage local file backups with retention policy"""
    
    def __init__(self, backup_dir: str = 'backups', retention_days: int = 30):
        """
        Initialize backup manager.
        
        Args:
            backup_dir: Directory for backups (default: 'backups')
            retention_days: Days to retain backups (default: 30)
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.retention_days = retention_days
    
    def backup_file(self, source_file: str, stage_name: str) -> Optional[Path]:
        """
        Create timestamped backup of file.
        
        Format: backups/stage1_trades_raw_20251024_153045.json
        
        Args:
            source_file: File to backup
            stage_name: Stage identifier (e.g., 'stage1')
            
        Returns:
            Path to backup file or None if source doesn't exist
        """
        source = Path(source_file)
        
        if not source.exists():
            logger.warning(f"Source file not found, skipping backup: {source}")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{stage_name}_{source.stem}_{timestamp}{source.suffix}"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(source, backup_path)
            logger.info(f"✓ Backed up to: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to backup {source}: {e}")
            return None
    
    def cleanup_old_backups(self) -> int:
        """
        Remove backups older than retention period.
        
        Returns:
            Number of backups removed
        """
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        cutoff_timestamp = cutoff.timestamp()
        
        removed = 0
        for backup in self.backup_dir.glob('*'):
            if backup.is_file() and backup.stat().st_mtime < cutoff_timestamp:
                try:
                    backup.unlink()
                    removed += 1
                    logger.debug(f"Removed old backup: {backup.name}")
                except Exception as e:
                    logger.error(f"Failed to remove {backup}: {e}")
        
        if removed > 0:
            logger.info(f"✓ Removed {removed} old backups (>{self.retention_days} days)")
        
        return removed
    
    def list_backups(self, file_pattern: str = '*', limit: int = 10) -> List[Path]:
        """
        List available backups, most recent first.
        
        Args:
            file_pattern: Glob pattern to filter backups (default: '*')
            limit: Maximum number of backups to return (default: 10)
            
        Returns:
            List of backup file paths
        """
        backups = sorted(
            self.backup_dir.glob(file_pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return backups[:limit]
    
    def restore_backup(self, backup_file: str, target_file: str) -> bool:
        """
        Restore a backup file.
        
        Args:
            backup_file: Backup file to restore
            target_file: Target location for restored file
            
        Returns:
            True if successful, False otherwise
        """
        backup_path = self.backup_dir / backup_file
        
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            shutil.copy2(backup_path, target_file)
            logger.info(f"✓ Restored {backup_file} to {target_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def get_backup_size_mb(self) -> float:
        """
        Get total size of backups directory in MB.
        
        Returns:
            Size in megabytes
        """
        total_size = sum(f.stat().st_size for f in self.backup_dir.glob('*') if f.is_file())
        return total_size / (1024 * 1024)