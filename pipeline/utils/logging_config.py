"""
Structured Logging Configuration
Provides JSON-formatted logs for machine parsing and human-readable logs for debugging
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing"""
    
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
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(stage_name: str, log_level: int = logging.INFO, log_dir: str = 'logs') -> logging.Logger:
    """
    Configure logging for pipeline stage.
    
    Creates two log files:
    - logs/pipeline_YYYYMMDD.json (JSON format for parsing)
    - logs/pipeline_YYYYMMDD_human.log (Human readable for debugging)
    
    Args:
        stage_name: Name of the pipeline stage (e.g., "Stage 1: Fetch Trades")
        log_level: Logging level (default: INFO)
        log_dir: Directory for log files (default: 'logs')
    
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
    
    # JSON handler for machine parsing
    json_handler = logging.FileHandler(json_log, mode='a')
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)
    
    # Human-readable handler for debugging
    human_handler = logging.FileHandler(human_log, mode='a')
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
    
    # Log stage start
    logger.info("=" * 80)
    logger.info(f"{stage_name} Started")
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