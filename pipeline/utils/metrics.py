"""
Local Metrics Collection
Tracks pipeline performance and data quality metrics
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


def convert_numpy_types(obj):
    """
    Recursively convert numpy types to native Python types for JSON serialization.
    
    Args:
        obj: Object that may contain numpy types
        
    Returns:
        Object with numpy types converted to native Python types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


class LocalMetrics:
    """Simple local metrics tracking to JSON files"""
    
    def __init__(self, metrics_dir: str = 'metrics'):
        """
        Initialize metrics collector.
        
        Args:
            metrics_dir: Directory for metrics files (default: 'metrics')
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        self.current_run = {}
        self.run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.start_time = datetime.now()
    
    def record(self, metric_name: str, value: Any, tags: Optional[Dict] = None):
        """
        Record a metric value.
        
        Args:
            metric_name: Name of the metric (e.g., 'stage1.trades_fetched')
            value: Metric value (int, float, string, etc.)
            tags: Optional tags for categorization
        """
        self.current_run[metric_name] = {
            'value': value,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'tags': tags or {}
        }
        logger.debug(f"Recorded metric: {metric_name} = {value}")
    
    def record_duration(self, stage_name: str, duration_seconds: float):
        """
        Record stage execution duration.
        
        Args:
            stage_name: Name of the stage
            duration_seconds: Duration in seconds
        """
        self.record(f'{stage_name}.duration_seconds', duration_seconds)
        self.record(f'{stage_name}.duration_minutes', duration_seconds / 60)
    
    def record_count(self, entity: str, count: int):
        """
        Record a count metric.
        
        Args:
            entity: Entity being counted (e.g., 'trades', 'assets')
            count: Count value
        """
        self.record(f'count.{entity}', count)
    
    def record_success(self, stage_name: str):
        """Record stage success"""
        self.record(f'{stage_name}.status', 'success')
    
    def record_failure(self, stage_name: str, error: str):
        """Record stage failure"""
        self.record(f'{stage_name}.status', 'failure')
        self.record(f'{stage_name}.error', error)
    
    def save(self):
        """Save metrics to file"""
        # Add run metadata
        self.current_run['_metadata'] = {
            'run_id': self.run_id,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'total_duration_seconds': (datetime.now() - self.start_time).total_seconds()
        }
        
        filename = self.metrics_dir / f'run_{self.run_id}.json'
        
        try:
            # Convert numpy types before JSON serialization
            metrics_to_save = convert_numpy_types(self.current_run)
            
            with open(filename, 'w') as f:
                json.dump(metrics_to_save, f, indent=2)
            logger.info(f"✓ Metrics saved to: {filename}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def summary(self):
        """Print metrics summary to console"""
        print("\n" + "="*80)
        print("METRICS SUMMARY")
        print("="*80)
        
        # Group by category
        categories = {}
        for name, data in self.current_run.items():
            if name == '_metadata':
                continue
            
            category = name.split('.')[0] if '.' in name else 'other'
            if category not in categories:
                categories[category] = []
            categories[category].append((name, data['value']))
        
        # Print by category
        for category, metrics in sorted(categories.items()):
            print(f"\n{category.upper()}:")
            for name, value in metrics:
                print(f"  {name}: {value}")
        
        # Print metadata
        if '_metadata' in self.current_run:
            meta = self.current_run['_metadata']
            print(f"\nRUN INFO:")
            print(f"  Run ID: {meta['run_id']}")
            print(f"  Duration: {meta['total_duration_seconds']:.2f}s")
        
        print("="*80)
    
    def get_metric(self, metric_name: str) -> Optional[Any]:
        """Get a specific metric value"""
        return self.current_run.get(metric_name, {}).get('value')