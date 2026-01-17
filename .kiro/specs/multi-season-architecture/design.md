# Design Document

## Overview

The multi-season architecture transforms the Fantasy Football Trade Analysis Dashboard from a single-season system to a unified cumulative data model. This design enables Season 3 launch while preserving historical Season 2 data immutability through append-only operations and client-side filtering.

The system transitions from separate per-season files to unified cumulative files containing all seasons' data with season tags. This approach provides better user experience through "All Seasons" views, enables cross-season analysis, and ensures historical data can never be accidentally modified.

## Architecture

### High-Level Architecture

```mermaid
graph TD
    A[Sleeper API] -->|Season 3 Only| B[Daily Pipeline Run]
    B --> C{Season Status Check}
    C -->|Active: S3| D[Fetch New Transactions]
    C -->|Static: S1, S2| E[Skip - Immutable]
    D --> F[Tag with season: season_3]
    F --> G[Append to trades.json]
    F --> H[Append to cumulative_processed_waiver_transactions.json]
    G --> I[Deduplication Check]
    H --> I
    I --> J[Dashboard JSON Copy]
    J --> K[Frontend: api-trades.json]
    K --> L[React: Filter by Season]
    L --> M[Display: All Seasons | S1 | S2 | S3]
    
    E -.->|Never Fetched| G
    E -.->|S1/S2 Records| H
    
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#f99,stroke:#333,stroke-width:2px
    style G fill:#9f9,stroke:#333,stroke-width:2px
    style I fill:#ff9,stroke:#333,stroke-width:2px
```

### Data Flow Architecture

The system implements a cumulative data model where:

1. **Historical Seasons (S1, S2)**: Marked as "static" - never fetched again after backfill
2. **Active Season (S3)**: Marked as "active" - fetched daily with incremental updates
3. **Unified Storage**: All seasons stored in single files with season tags
4. **Append-Only Operations**: New data only appended, existing data never modified
5. **Client-Side Filtering**: Frontend filters unified data by season in memory

## Components and Interfaces

### Core Components

#### 1. Cumulative File Manager
**File**: `pipeline/utils/cumulative_file_manager.py`

Handles atomic append operations with deduplication:
- `initialize_cumulative_file()`: Creates empty cumulative file structure
- `append_to_cumulative_file()`: Atomically appends new records with deduplication
- `verify_file_integrity()`: Validates file structure and metadata consistency

**Key Features**:
- Atomic write operations (temp file → rename)
- Transaction ID-based deduplication
- Automatic backup creation
- Crash-safe operations
- Metadata updates (counts, timestamps)

#### 2. Season Configuration Manager
**File**: `pipeline/config/seasons.yaml` + `pipeline/config.py`

Manages season lifecycle and pipeline behavior:
- Season status tracking (static, active, unavailable)
- League ID management per season
- Pipeline execution rules (which seasons to process)
- Immutability protection settings

#### 3. Immutability Guard
**File**: `pipeline/utils/immutability_guard.py`

Prevents accidental modification of static season data:
- `verify_no_static_modifications()`: Validates new records don't modify static seasons
- `ImmutabilityViolation`: Exception for protection violations
- Configuration-based protection rules

#### 4. Season Filter Components
**Files**: 
- `dashboard/frontend/src/components/UI/SeasonFilter.tsx`
- `dashboard/frontend/src/hooks/useSeasonMetrics.ts`

Provides client-side season filtering:
- Season selection UI component
- Metric calculation hooks for filtered data
- Support for season combinations (S1+S2, S2+S3, All)

### Interface Specifications

#### Cumulative File Interface
```typescript
interface CumulativeTradesFile {
  metadata: {
    schema_version: string;
    last_updated: string;
    seasons_included: string[];
    total_trades: number;
    trades_by_season: Record<string, number>;
    season_info: Record<string, SeasonInfo>;
  };
  trades: TradeRecord[];
}

interface TradeRecord {
  season: string;           // "season_2" | "season_3"
  league_id: string;
  transaction_id: string;   // Unique identifier for deduplication
  // ... all original Sleeper API fields preserved
}
```

#### Season Configuration Interface
```yaml
seasons:
  season_2:
    status: "static"              # Never fetch again
    league_id: string
    backfill_completed: boolean
  season_3:
    status: "active"              # Fetch daily
    league_id: string
    last_incremental_fetch: string

pipeline:
  active_seasons: string[]        # Process these seasons
  static_seasons: string[]        # Protect these seasons
  allow_static_refetch: boolean   # Safety override
```

## Data Models

### Unified Data Schema

#### Cumulative Trades File
```json
{
  "metadata": {
    "schema_version": "2.0.0",
    "last_updated": "2025-12-31T14:16:59Z",
    "seasons_included": ["season_2", "season_3"],
    "total_trades": 158,
    "trades_by_season": {
      "season_2": 81,
      "season_3": 77
    },
    "season_info": {
      "season_2": {
        "league_id": "1180814327660371968",
        "year": 2024,
        "status": "static",
        "last_fetched": "2025-12-31T10:00:00Z",
        "backfill_completed": true
      },
      "season_3": {
        "league_id": "1312166810505719808", 
        "year": 2025,
        "status": "active",
        "last_fetched": "2025-12-31T14:16:59Z",
        "incremental_updates": 12
      }
    }
  },
  "trades": [
    {
      "season": "season_2",
      "league_id": "1180814327660371968",
      "transaction_id": "1296312256438497280",
      // ... all original Sleeper API fields
    }
  ]
}
```

#### Season-Specific Data Files
Point-in-time data remains separate per season:
- `standings/season_3.json`: Current standings for Season 3
- `playoff-scenarios/season_3.json`: Playoff simulations for Season 3

### Data Relationships

1. **Transaction Uniqueness**: `transaction_id` is globally unique across all seasons
2. **Season Isolation**: Each record tagged with exactly one season
3. **League Association**: Each season has distinct `league_id`
4. **Temporal Ordering**: Records maintain chronological order within seasons

## Error Handling

### Immutability Protection
- **Static Season Modification**: Throws `ImmutabilityViolation` if attempting to modify static season data
- **Configuration Validation**: Prevents pipeline execution with invalid season configurations
- **Backup Recovery**: Automatic restoration from backups on write failures

### Data Integrity
- **Duplicate Detection**: Skips records with existing `transaction_id`
- **Required Field Validation**: Rejects records missing critical fields
- **Atomic Operations**: Ensures files never left in partially written state
- **Schema Validation**: Validates cumulative file structure on load

### API Failures
- **Rate Limiting**: Exponential backoff for Sleeper API rate limits
- **Network Errors**: Retry logic with configurable attempts
- **Partial Failures**: Continue processing other seasons if one fails
- **Rollback Capability**: Restore from backups on critical failures

## Testing Strategy

The testing approach combines unit tests for specific functionality with property-based tests for universal correctness guarantees.

### Unit Testing
- **Configuration Validation**: Test season config validation rules
- **File Operations**: Test atomic write operations and backup creation
- **Deduplication Logic**: Test transaction ID uniqueness enforcement
- **Error Conditions**: Test immutability violations and invalid data handling
- **Frontend Filtering**: Test season filter UI components and hooks

### Property-Based Testing
Property-based tests validate universal properties across all valid inputs using randomized test data.

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

#### Correctness Properties

**Property 1: Cumulative File Storage Consistency**
*For any* set of transactions from multiple seasons, storing them in cumulative files should result in all transactions being present with correct season tags and proper file structure.
**Validates: Requirements 1.1, 1.2**

**Property 2: Metadata Accuracy**
*For any* cumulative file after append operations, the metadata should accurately reflect the seasons present, transaction counts per season, and last update timestamps.
**Validates: Requirements 1.3, 1.4, 3.5**

**Property 3: Data Preservation**
*For any* transaction from the Sleeper API, storing it in the cumulative system should preserve all original fields while adding only the season tag.
**Validates: Requirements 1.5, 7.3, 11.2**

**Property 4: Static Season Immutability**
*For any* pipeline execution, existing static season records should remain completely unchanged regardless of new data or operations.
**Validates: Requirements 2.1, 2.3**

**Property 5: Immutability Violation Detection**
*For any* attempt to modify static season data, the system should detect and prevent the modification while logging appropriate errors.
**Validates: Requirements 2.4**

**Property 6: Atomic Write Operations**
*For any* file modification operation, the system should either complete the write entirely or leave the original file unchanged, never creating partially written files.
**Validates: Requirements 3.2, 9.1, 9.4**

**Property 7: Deduplication Consistency**
*For any* set of transactions including duplicates, appending them to cumulative files should result in only unique transaction_ids being stored.
**Validates: Requirements 3.3, 6.1, 6.2**

**Property 8: Season Tagging Accuracy**
*For any* transaction being stored, it should be tagged with the correct season identifier based on its source and timing.
**Validates: Requirements 3.4, 7.2**

**Property 9: Configuration-Based Pipeline Behavior**
*For any* season configuration (active vs static), the pipeline should fetch data only for active seasons and skip all static seasons.
**Validates: Requirements 4.2, 4.3, 12.1, 12.2**

**Property 10: Configuration Validation**
*For any* season configuration, the system should validate that active seasons have league_ids, no season appears in both active and static lists, and required files exist.
**Validates: Requirements 4.4, 10.1, 10.2, 10.3, 10.4**

**Property 11: Incremental Fetch Behavior**
*For any* active season with a last fetch timestamp, subsequent fetches should only retrieve transactions newer than that timestamp.
**Validates: Requirements 5.1, 5.3**

**Property 12: Initial Fetch Completeness**
*For any* active season without a previous fetch timestamp, the system should fetch all available data for that season.
**Validates: Requirements 5.2**

**Property 13: API Error Handling**
*For any* Sleeper API rate limit or network error, the system should implement exponential backoff and retry logic.
**Validates: Requirements 5.4**

**Property 14: Record Validation**
*For any* transaction record, the system should validate required fields (transaction_id, season, league_id) and reject invalid records with appropriate logging.
**Validates: Requirements 6.4, 6.5**

**Property 15: Backup Creation and Recovery**
*For any* file modification operation, the system should create timestamped backups beforehand and restore from backups on write failures.
**Validates: Requirements 2.5, 9.2, 9.3**

**Property 16: File Integrity Validation**
*For any* write operation, the system should validate file integrity after completion to ensure data consistency.
**Validates: Requirements 9.5**

**Property 17: Backfill Data Consistency**
*For any* historical season data being backfilled, the resulting cumulative files should contain exactly the same transaction data with added season tags.
**Validates: Requirements 7.4, 7.5**

**Property 18: Frontend Data Provision**
*For any* cumulative data files, the frontend should receive complete multi-season data that can be filtered client-side by season.
**Validates: Requirements 8.1, 8.2**

**Property 19: Season Count Accuracy**
*For any* season filter in the frontend, the displayed counts should match the actual number of transactions for that season in the data.
**Validates: Requirements 8.5**

**Property 20: Cross-Season Schema Consistency**
*For any* transactions from different seasons, the field names and structure should be consistent across seasons in cumulative files.
**Validates: Requirements 11.1, 11.3**

**Property 21: Schema Compatibility Handling**
*For any* schema differences between seasons, the system should handle them gracefully and document variations in metadata.
**Validates: Requirements 11.4, 11.5**

**Property 22: Dashboard Data Synchronization**
*For any* pipeline update, the dashboard JSON files should be updated with the latest cumulative data and copied to the frontend directory.
**Validates: Requirements 12.3, 12.4**

**Property 23: Operation Logging Completeness**
*For any* pipeline operation, the system should log comprehensive information about transactions fetched, duplicates skipped, and seasons processed.
**Validates: Requirements 5.5, 6.3, 12.5**

### Property-Based Test Configuration

The system will use **pytest** with **Hypothesis** for property-based testing in Python components and **fast-check** for TypeScript frontend components.

**Test Configuration Requirements**:
- Minimum 100 iterations per property test
- Each test tagged with format: **Feature: multi-season-architecture, Property {number}: {property_text}**
- Custom generators for transaction data, season configurations, and file states
- Comprehensive input space coverage through smart constraint generation

**Example Test Structure**:
```python
@given(transactions=transaction_list_strategy(), seasons=season_config_strategy())
def test_cumulative_file_storage_consistency(transactions, seasons):
    """Feature: multi-season-architecture, Property 1: Cumulative File Storage Consistency"""
    # Test implementation
```

### Dual Testing Approach

The testing strategy combines unit tests for specific functionality with property-based tests for universal correctness guarantees.

**Unit Testing Focus**:
- Configuration file parsing and validation
- Error message formatting and logging
- Frontend component rendering and interaction
- API client retry logic and rate limiting
- File system operations and backup creation
- Specific edge cases (empty files, missing directories)

**Property-Based Testing Focus**:
- Universal properties across all valid inputs
- Data consistency and integrity guarantees
- Cross-season compatibility and schema consistency
- Deduplication and immutability enforcement
- Atomic operations and failure recovery

**Testing Framework Selection**:
- **Python Pipeline**: pytest + Hypothesis for property-based testing
- **TypeScript Frontend**: Jest + fast-check for property-based testing
- **Integration Tests**: Custom test harness for end-to-end pipeline validation

**Test Data Generation**:
- Smart generators that create realistic transaction data
- Season configuration generators with valid/invalid combinations
- File state generators for testing atomic operations and recovery
- API response generators for testing error handling and rate limiting

Both testing approaches are essential for comprehensive coverage - unit tests catch concrete implementation bugs while property tests verify general correctness across the entire input space.