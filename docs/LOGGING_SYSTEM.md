# Comprehensive Logging System

## Overview

The multi-season architecture includes a comprehensive logging system that tracks all pipeline operations with structured metadata. This system provides both machine-readable JSON logs and human-readable text logs with automatic rotation.

## Features

### 1. Structured Logging
- **JSON Format**: Machine-parseable logs with structured metadata
- **Human-Readable Format**: Easy-to-read logs for debugging
- **Log Rotation**: Automatic rotation at 10MB per file, keeping 5 backups
- **Multiple Handlers**: Console, JSON file, and human-readable file outputs

### 2. Operation Tracking
The `OperationLogger` class provides specialized methods for tracking pipeline operations:

#### Fetch Operations
```python
op_logger.log_fetch_operation(
    season='season_3',
    count=150,
    duplicates=10,
    incremental=True,
    duration=2.5
)
```
Logs: transactions fetched, duplicates skipped, fetch mode, duration

#### Process Operations
```python
op_logger.log_process_operation(
    season='season_3',
    operation='extract',
    count=140,
    duration=1.2,
    status='success'
)
```
Logs: records processed, operation type, duration, status

#### Deduplication Operations
```python
op_logger.log_deduplication(
    season='season_3',
    total=150,
    duplicates=10,
    kept=140
)
```
Logs: total records, duplicates found, unique records kept, duplicate rate

#### Season Summary
```python
op_logger.log_season_summary(
    active_seasons=['season_3'],
    static_seasons=['season_1', 'season_2'],
    processed_seasons=['season_3']
)
```
Logs: active/static/processed seasons, success rate

#### Error Logging
```python
op_logger.log_error(
    operation='fetch',
    season='season_3',
    error=exception,
    context={'additional': 'info'}
)
```
Logs: operation, season, error details, stack trace, context

### 3. Operation Statistics
The logger accumulates statistics throughout execution:

```python
# Get accumulated stats
stats = op_logger.get_operation_stats()

# Log stats summary
op_logger.log_operation_stats()
```

Statistics include:
- Fetch counts and modes per season
- Processing counts and durations
- Deduplication metrics and rates
- Season processing summary
- Error details and contexts

## Usage

### Basic Setup
```python
from utils.logging_config import setup_logging, get_operation_logger

# Initialize logging
logger = setup_logging('Stage Name', log_level=logging.INFO)
op_logger = get_operation_logger(__name__)
```

### In Pipeline Stages
```python
# Log fetch operation
op_logger.log_fetch_operation(
    season=season_name,
    count=len(transactions),
    duplicates=duplicates_skipped,
    incremental=True,
    duration=fetch_duration
)

# Log deduplication
op_logger.log_deduplication(
    season=season_name,
    total=total_records,
    duplicates=duplicate_count,
    kept=unique_count
)

# Log errors
try:
    # ... operation ...
except Exception as e:
    op_logger.log_error('operation_name', season_name, e)
    raise
```

### In Main Pipeline
```python
# Log season summary
op_logger.log_season_summary(
    active_seasons=active_seasons,
    static_seasons=static_seasons,
    processed_seasons=processed_seasons
)

# Log final statistics
op_logger.log_operation_stats()
```

## Log Files

### Location
All logs are written to the `logs/` directory:
- `logs/pipeline_YYYYMMDD.json` - JSON format for machine parsing
- `logs/pipeline_YYYYMMDD_human.log` - Human-readable format

### JSON Log Format
```json
{
  "timestamp": "2026-01-02T22:44:54.675156Z",
  "level": "INFO",
  "logger": "stage1",
  "module": "stage1_fetch_trades",
  "function": "fetch_trades_for_season",
  "line": 123,
  "message": "Fetch operation completed for season_3: 150 records fetched",
  "operation": "fetch",
  "season": "season_3",
  "count": 150,
  "duration": 2.5,
  "status": "success"
}
```

### Human-Readable Log Format
```
2026-01-02 14:44:54 | INFO     | stage1                    | Fetch operation completed for season_3: 150 records fetched, 10 duplicates skipped (mode: incremental) in 2.50s
```

## Log Rotation

Logs automatically rotate when they reach 10MB:
- Maximum file size: 10MB
- Backup count: 5 files
- Naming: `pipeline_YYYYMMDD.json.1`, `pipeline_YYYYMMDD.json.2`, etc.

## Requirements Satisfied

This logging system satisfies the following requirements:

### Requirement 5.5: Operation Logging
- Logs number of new transactions fetched vs skipped
- Tracks incremental vs full fetch operations
- Records API call counts and rate limiting

### Requirement 6.3: Deduplication Logging
- Logs number of duplicate records skipped during each append
- Tracks deduplication rates per season
- Records total vs unique transaction counts

### Requirement 12.5: Pipeline Orchestration Logging
- Logs which seasons were processed vs skipped in each run
- Tracks pipeline stage execution and durations
- Records comprehensive operation summaries

## Best Practices

1. **Use Operation Logger for Metrics**: Use `OperationLogger` for tracking counts, durations, and statistics
2. **Use Standard Logger for Events**: Use standard logger for general events and messages
3. **Include Context**: Always include season name and operation type in logs
4. **Log Errors with Context**: Include relevant context when logging errors
5. **Review JSON Logs**: Use JSON logs for automated monitoring and alerting
6. **Review Human Logs**: Use human-readable logs for debugging and troubleshooting

## Monitoring

### Key Metrics to Monitor
- Fetch operation counts per season
- Duplicate rates (should be low for incremental fetches)
- Processing durations (watch for performance degradation)
- Error rates and types
- Season processing success rates

### Example Queries

Parse JSON logs to extract metrics:
```bash
# Count fetch operations per season
jq -r 'select(.operation=="fetch") | .season' logs/pipeline_*.json | sort | uniq -c

# Calculate average duplicate rate
jq -r 'select(.operation=="deduplication") | .duplicate_rate' logs/pipeline_*.json | awk '{sum+=$1; count++} END {print sum/count}'

# List all errors
jq -r 'select(.level=="ERROR") | {timestamp, season, message}' logs/pipeline_*.json
```

## Troubleshooting

### No Logs Generated
- Check that `logs/` directory exists (created automatically)
- Verify logging is initialized with `setup_logging()`
- Check file permissions on logs directory

### Logs Not Rotating
- Verify `max_bytes` parameter in `setup_logging()`
- Check disk space availability
- Ensure write permissions on log files

### Missing Operation Statistics
- Verify `OperationLogger` is used (not just standard logger)
- Check that `log_operation_stats()` is called at end of execution
- Ensure operations are logged with proper metadata

## Future Enhancements

Potential improvements for the logging system:
- Centralized log aggregation (e.g., CloudWatch, Elasticsearch)
- Real-time monitoring dashboards
- Automated alerting on error thresholds
- Performance profiling integration
- Log compression for archived logs
