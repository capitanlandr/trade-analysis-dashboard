# Data Architecture: Pipeline vs Dashboard Files

## Overview

The project maintains JSON files in two locations with distinct purposes:

```
pipeline/
├── standings_data.json              # Pipeline copy (debugging/audit)
├── playoff_scenarios_simulated.json # Pipeline copy (debugging/audit)
└── [other pipeline outputs]

dashboard/frontend/public/
├── api-standings.json               # Dashboard copy (frontend consumption)
├── api-playoff-scenarios.json       # Dashboard copy (frontend consumption)
├── api-trades.json                  # Generated from CSVs
├── api-teams.json                   # Generated from CSVs
└── api-stats-summary.json           # Generated from CSVs
```

## Why Two Locations?

### Pipeline Directory Files (`pipeline/*.json`)
- **Purpose**: Debugging, auditing, historical records
- **Read by**: No other scripts (write-only archives)
- **Kept for**: Troubleshooting pipeline issues, comparing runs, manual inspection
- **Lifecycle**: Preserved across runs for reference

### Dashboard Directory Files (`dashboard/frontend/public/api-*.json`)
- **Purpose**: Frontend data consumption
- **Read by**: React dashboard components
- **Updated**: Every pipeline run
- **Lifecycle**: Overwritten with latest data

## File Generation Pattern

### Direct Write (Efficient - No Redundant I/O)

Scripts write to both locations **from memory** (no copy operation):

#### `fetch_standings.py` (Lines 454-471)
```python
# 1. Write pipeline copy
output_path = Path(...).parent.parent / "standings_data.json"
with open(output_path, 'w') as f:
    json.dump(output, f, indent=2)

# 2. Write dashboard copy (SAME data from memory)
dashboard_path = Path(...) / 'api-standings.json'
with open(dashboard_path, 'w') as f:
    json.dump(output, f, indent=2)  # No file read - direct from memory!
```

#### `simulate_playoff_scenarios.py` (Lines 484-499)
```python
# 1. Write pipeline copy
output_file = Path(...) / 'playoff_scenarios_simulated.json'
with open(output_file, 'w') as f:
    json.dump(simulation_results, f, indent=2)

# 2. Write dashboard copy (SAME data from memory)
dashboard_file = Path(...) / 'api-playoff-scenarios.json'
with open(dashboard_file, 'w') as f:
    json.dump(simulation_results, f, indent=2)  # No file read!
```

## What generate_dashboard_json.py Does

This script **transforms CSV data into JSON** - it does NOT copy JSON files:

### CSV → JSON Transformations
- `league_trades_analysis_pipeline.csv` → `api-trades.json`
- `team_identity_mapping.csv` → `api-teams.json`
- Calculated statistics → `api-stats-summary.json`

### NOT Responsible For
- ❌ `api-standings.json` (written by `fetch_standings.py`)
- ❌ `api-playoff-scenarios.json` (written by `simulate_playoff_scenarios.py`)

## Design Rationale

### Why Not Single Location?
**Considered but rejected** - writing only to dashboard would:
- Eliminate pipeline debugging artifacts
- Make troubleshooting harder
- Lose historical context for comparisons

### Why Not Copy Files?
**Copying JSON → JSON is wasteful:**
```python
# INEFFICIENT (old approach):
write(data, 'pipeline.json')
data = read('pipeline.json')    # ← Unnecessary disk I/O
write(data, 'dashboard.json')

# EFFICIENT (current approach):
write(data, 'pipeline.json')    # ← From memory
write(data, 'dashboard.json')   # ← Same data, still in memory
```

## Benefits

1. **Performance**: Eliminates 2+ file read operations per run
2. **Simplicity**: Each script owns its complete output
3. **Debuggability**: Pipeline artifacts preserved
4. **Single Source of Truth**: Data generated once, written twice
5. **Clear Separation**: Pipeline vs Dashboard concerns

## When to Use Each File

### Development/Debugging
Use **pipeline directory files**:
- Inspect raw simulation results
- Compare historical runs
- Verify calculation logic
- Manual data validation

### Production/Dashboard
Use **dashboard directory files**:
- Frontend reads these exclusively
- Always contain latest data
- Optimized for web delivery
- Deployed to Vercel

## Week Detection Architecture

The pipeline uses a centralized week detection system to avoid timing issues with Sleeper's `leg` field during Tuesday waivers.

### The Problem: Tuesday Timing ⏰

When Sleeper processes waivers on Tuesday morning (~3 AM EST), the `leg` field advances to the next week **before** games are actually played. If scripts trust `leg` blindly:
- ❌ Week advances prematurely (e.g., shows Week 13 when only Week 12 games completed)
- ❌ Playoff scenarios calculate incorrectly
- ❌ Dashboard shows wrong week context

### The Solution: Roster Record Validation ✓

Instead of trusting `leg`, we validate using actual game results:

```python
# Formula for dual-game-per-week format
weeks_completed = (wins + losses + ties) / 2
```

**Example:**
```
Roster Record: 6-6-0 = 12 total games
Calculation: 12 games / 2 = 6 weeks completed
Result: Week 6 ✓ (regardless of what leg says)
```

### Centralized Detection Flow

```
Stage 0: detect_current_week.py
├─ Fetch league info & rosters
├─ Validate: (wins + losses + ties) / 2
└─ Write: pipeline/config/current_week.json

All Other Stages
└─ Read: get_current_week_from_config()
```

### Config File Location

```
pipeline/
├── config/
│   └── current_week.json    ← Single source of truth
│       {
│         "current_week": 12,
│         "last_updated": "Generated by detect_current_week.py"
│       }
└── utils/
    └── week_config.py        ← Utility to read config
```

### Scripts That Depend on current_week.json

1. **Stage 8: `fetch_standings.py`** - Week context for standings
2. **Stage 9: `simulate_playoff_scenarios.py`** - Critical for remaining games calculation
3. **Stage 9: `calculate_playoff_scenarios.py`** - Clinch/elimination scenarios
4. **Dashboard JSON** - Week labels on frontend

### Benefits

- ✅ **Tuesday-safe**: Works correctly during waiver processing
- ✅ **Consistent**: All scripts use same validated week
- ✅ **Accurate**: Based on actual games played, not Sleeper's timing
- ✅ **Debuggable**: Single config file to inspect/override

### When Week Advances

Week only advances when **all teams** have completed the same number of games:
- Monday Night Football ends → Records update
- All rosters show new game count → Week validated
- Config updates → Scripts see new week

For detailed information on week detection logic, validation scenarios, and troubleshooting, see [WEEK_DETECTION.md](./WEEK_DETECTION.md).

## Future Considerations

If pipeline JSON files are never read by scripts or humans, consider:
- Making them optional (command-line flag)
- Moving to separate `artifacts/` directory
- Implementing retention policy (keep last N runs)

However, current dual-write overhead is minimal (~2ms per file) and provides valuable debugging capability.