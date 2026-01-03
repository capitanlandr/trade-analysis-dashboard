"""
Structured Logging Configuration
Provides JSON-formatted logs for machine parsing and human-readable logs for debugging

MULTI-SEASON LOGGING FEATURES:
- Comprehensive operation logging (transactions fetched, duplicates skipped, seasons processed)
- Structured logging with appropriate log levels
- Log rotation support
- Performance metrics tracking
- Season-specific logging context
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing with enhanced metadata"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage()
        }
        
        # Add custom fields if present (for operation logging)
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        if hasattr(record, 'season'):
            log_data['season'] = record.season
        if hasattr(record, 'count'):
            log_data['count'] = record.count
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration
        if hasattr(record, 'status'):
            log_data['status'] = record.status
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class OperationLogger:
    """
    Enhanced logger for tracking pipeline operations with structured metadata.
    
    Provides methods for logging:
    - Transactions fetched/processed
    - Duplicates skipped
    - Seasons processed
    - Performance metrics
    - Error conditions
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._operation_stats: Dict[str, Any] = {}
    
    def log_fetch_operation(self, season: str, count: int, duplicates: int = 0, 
                          incremental: bool = False, duration: float = None):
        """
        Log data fetch operation with comprehensive metadata.
        
        Args:
            season: Season name
            count: Number of records fetched
            duplicates: Number of duplicate records skipped
            incremental: Whether this was an incremental fetch
            duration: Operation duration in seconds
        """
        mode = "incremental" if incremental else "full"
        
        # Create log record with custom attributes
        extra = {
            'operation': 'fetch',
            'season': season,
            'count': count,
            'status': 'success'
        }
        
        if duration is not None:
            extra['duration'] = round(duration, 2)
        
        message = f"Fetch operation completed for {season}: {count} records fetched"
        if duplicates > 0:
            message += f", {duplicates} duplicates skipped"
        message += f" (mode: {mode})"
        
        if duration is not None:
            message += f" in {duration:.2f}s"
        
        self.logger.info(message, extra=extra)
        
        # Track in operation stats
        self._operation_stats[f'fetch_{season}'] = {
            'count': count,
            'duplicates': duplicates,
            'mode': mode,
            'duration': duration
        }
    
    def log_process_operation(self, season: str, operation: str, count: int, 
                            duration: float = None, status: str = 'success'):
        """
        Log data processing operation.
        
        Args:
            season: Season name
            operation: Operation type (e.g., 'extract', 'validate', 'transform')
            count: Number of records processed
            duration: Operation duration in seconds
            status: Operation status ('success', 'partial', 'failed')
        """
        extra = {
            'operation': operation,
            'season': season,
            'count': count,
            'status': status
        }
        
        if duration is not None:
            extra['duration'] = round(duration, 2)
        
        message = f"{operation.capitalize()} operation for {season}: {count} records processed"
        if duration is not None:
            message += f" in {duration:.2f}s"
        
        log_level = logging.INFO if status == 'success' else logging.WARNING
        self.logger.log(log_level, message, extra=extra)
        
        # Track in operation stats
        self._operation_stats[f'{operation}_{season}'] = {
            'count': count,
            'status': status,
            'duration': duration
        }
    
    def log_deduplication(self, season: str, total: int, duplicates: int, kept: int):
        """
        Log deduplication operation results.
        
        Args:
            season: Season name
            total: Total records processed
            duplicates: Number of duplicates found
            kept: Number of unique records kept
        """
        extra = {
            'operation': 'deduplication',
            'season': season,
            'count': kept,
            'status': 'success'
        }
        
        duplicate_rate = (duplicates / total * 100) if total > 0 else 0
        
        message = (f"Deduplication for {season}: {kept} unique records kept, "
                  f"{duplicates} duplicates skipped ({duplicate_rate:.1f}% duplicate rate)")
        
        self.logger.info(message, extra=extra)
        
        # Track in operation stats
        self._operation_stats[f'dedup_{season}'] = {
            'total': total,
            'duplicates': duplicates,
            'kept': kept,
            'duplicate_rate': round(duplicate_rate, 2)
        }
    
    def log_season_summary(self, active_seasons: list, static_seasons: list, 
                          processed_seasons: list):
        """
        Log comprehensive season processing summary.
        
        Args:
            active_seasons: List of active season names
            static_seasons: List of static season names
            processed_seasons: List of successfully processed season names
        """
        extra = {
            'operation': 'season_summary',
            'status': 'success'
        }
        
        message = (f"Season processing summary: "
                  f"{len(processed_seasons)}/{len(active_seasons)} active seasons processed, "
                  f"{len(static_seasons)} static seasons skipped")
        
        self.logger.info(message, extra=extra)
        
        # Log detailed breakdown
        self.logger.info(f"Active seasons: {', '.join(active_seasons)}")
        self.logger.info(f"Static seasons: {', '.join(static_seasons)}")
        self.logger.info(f"Processed seasons: {', '.join(processed_seasons)}")
        
        # Track in operation stats
        self._operation_stats['season_summary'] = {
            'active_seasons': active_seasons,
            'static_seasons': static_seasons,
            'processed_seasons': processed_seasons,
            'success_rate': len(processed_seasons) / len(active_seasons) if active_seasons else 0
        }
    
    def log_error(self, operation: str, season: str, error: Exception, 
                 context: Dict[str, Any] = None):
        """
        Log error with comprehensive context.
        
        Args:
            operation: Operation that failed
            season: Season being processed
            error: Exception that occurred
            context: Additional context information
        """
        extra = {
            'operation': operation,
            'season': season,
            'status': 'failed'
        }
        
        if context:
            extra.update(context)
        
        message = f"{operation.capitalize()} failed for {season}: {str(error)}"
        
        self.logger.error(message, extra=extra, exc_info=True)
        
        # Track in operation stats
        self._operation_stats[f'error_{operation}_{season}'] = {
            'error': str(error),
            'error_type': type(error).__name__,
            'context': context
        }
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """
        Get accumulated operation statistics.
        
        Returns:
            Dictionary of operation statistics
        """
        return self._operation_stats.copy()
    
    def log_operation_stats(self):
        """Log accumulated operation statistics as summary."""
        if not self._operation_stats:
            return
        
        self.logger.info("=" * 80)
        self.logger.info("OPERATION STATISTICS SUMMARY")
        self.logger.info("=" * 80)
        
        for operation, stats in self._operation_stats.items():
            self.logger.info(f"{operation}: {json.dumps(stats, indent=2)}")
        
        self.logger.info("=" * 80)


def setup_logging(stage_name: str, log_level: int = logging.INFO, log_dir: str = 'logs',
                 max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5) -> logging.Logger:
    """
    Configure logging for pipeline stage with rotation support.
    
    Creates two log files with rotation:
    - logs/pipeline_YYYYMMDD.json (JSON format for parsing)
    - logs/pipeline_YYYYMMDD_human.log (Human readable for debugging)
    
    Args:
        stage_name: Name of the pipeline stage (e.g., "Stage 1: Fetch Trades")
        log_level: Logging level (default: INFO)
        log_dir: Directory for log files (default: 'logs')
        max_bytes: Maximum size per log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Date-based log files
    date_str = datetime.now().strftime('%Y%m%d')
    json_log = log_path / f'pipeline_{date_str}.json'
    human_log = log_path / f'pipeline_{date_str}_human.log'
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # JSON handler for machine parsing with rotation
    json_handler = RotatingFileHandler(
        json_log, 
        mode='a',
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)
    
    # Human-readable handler for debugging with rotation
    human_handler = RotatingFileHandler(
        human_log,
        mode='a',
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    human_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    human_handler.setFormatter(human_format)
    logger.addHandler(human_handler)
    
    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(human_format)
    logger.addHandler(console)
    
    # Log stage start with metadata
    logger.info("=" * 80)
    logger.info(f"{stage_name} Started")
    logger.info(f"Log Level: {logging.getLevelName(log_level)}")
    logger.info(f"Log Directory: {log_path.absolute()}")
    logger.info(f"Rotation: {max_bytes / (1024 * 1024):.1f}MB per file, {backup_count} backups")
    logger.info("=" * 80)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name or __name__)


def get_operation_logger(name: Optional[str] = None) -> OperationLogger:
    """
    Get an operation logger instance for enhanced operation tracking.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        OperationLogger instance
    """
    base_logger = get_logger(name)
    return OperationLogger(base_logger)