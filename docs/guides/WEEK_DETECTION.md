# Week Detection Architecture

## Overview

The centralized week detection system solves the **Tuesday timing problem** where Sleeper's `leg` field advances before games are actually completed and records are finalized. This document explains how we validate week completion using roster records and provide a single source of truth for all pipeline scripts.

---

## The Tuesday Timing Problem 🕒

### What Happens on Tuesday?

**Monday Night Football ends** → Games finish around 11:30 PM EST

**Tuesday Morning (~3 AM EST)** → Sleeper processes waivers and advances `leg`

**The Problem**: When you query Sleeper's API on Tuesday morning:
- `leg` field shows **Week 13** (next week)
- But roster records show **only Week 12** games completed
- Scripts that trust `leg` blindly think Week 13 is done
- This causes incorrect playoff calculations and standings

### Example Scenario

```
Monday Night (11:30 PM) - Week 12 games finish
├─ Rosters show: 6-6-0 record (12 games / 2 = Week 12 complete)
└─ Sleeper leg: 12 (correctly shows current week)

Tuesday Morning (3 AM) - Waivers process
├─ Rosters show: 6-6-0 record (still only Week 12 complete!)
└─ Sleeper leg: 13 (⚠️ advanced to NEXT week prematurely)

Tuesday Afternoon - Our scripts run
├─ ✅ CORRECT: Validate using records → Week 12
└─ ❌ WRONG: Trust leg blindly → Week 13 (games not played yet!)
```

---

## Mathematical Validation Formula

### Dual-Game-Per-Week League Format

Our league plays **2 games per week** (one matchup, counts twice). Therefore:

```python
weeks_completed = (wins + losses + ties) / 2
```

### Validation Examples

**Week 12 Complete:**
```
Roster Record: 6 wins + 6 losses + 0 ties = 12 total games
Calculation: 12 games / 2 = 6 weeks completed
Result: Week 6 ✓
```

**Week 13 In Progress (Tuesday morning):**
```
Roster Record: 6 wins + 6 losses + 0 ties = 12 total games
Calculation: 12 games / 2 = 6 weeks completed
Sleeper leg: 7 (next week)
Result: Week 6 ✓ (don't advance until games actually played)
```

**Week 13 Complete:**
```
Roster Record: 7 wins + 6 losses + 0 ties = 13 total games
Calculation: 13 games / 2 = 6.5 weeks... wait that's wrong!
Result: This shouldn't happen - each team plays 2 games per week
```

### Validation Logic

The script validates all rosters and checks:

1. **All teams have same weeks completed** → Use that week
2. **Teams differ** → Use minimum (safest completed week)
3. **Compare to Sleeper leg:**
   - If `weeks_completed == leg`: Week is finalized ✓
   - If `weeks_completed == leg - 1`: Games done, waivers pending ✓
   - If `weeks_completed < leg - 1`: Unexpected, use roster record as truth

---

## How Centralized Detection Works

### Architecture: Stage 0 → Config → All Scripts

```
┌─────────────────────────────────────────────────────────┐
│  Stage 0: detect_current_week.py                        │
│  ├─ Fetch league info (get leg)                         │
│  ├─ Fetch all rosters                                   │
│  ├─ Calculate: (wins + losses + ties) / 2               │
│  └─ Write: pipeline/config/current_week.json            │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
               ┌─────────────────────────┐
               │  current_week.json      │
               │  {                      │
               │    "current_week": 12,  │
               │    "last_updated": "…"  │
               │  }                      │
               └─────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
    Stage 1-6         Stage 7-9          Stage 10
    Trade Analysis    Standings &        Dashboard
    Pipeline          Simulations        Generation
```

### Config File Location

```
pipeline/
├── config/
│   └── current_week.json    ← Single source of truth
├── scripts/
│   ├── detect_current_week.py    ← Generates config
│   ├── fetch_standings.py        ← Reads config
│   ├── simulate_playoff_scenarios.py ← Reads config
│   └── calculate_playoff_scenarios.py ← Reads config
└── utils/
    └── week_config.py        ← Utility to read config
```

### Reading the Config

All scripts use the centralized utility:

```python
from utils.week_config import get_current_week_from_config

# Simple usage
current_week = get_current_week_from_config()
print(f"Current week: {current_week}")

# With fallback for scripts that can tolerate missing config
current_week = get_current_week_with_fallback(fallback=12)
```

---

## Example Scenarios

### Scenario 1: Games Just Finished (Monday Night)

**State:**
```
Time: Monday 11:45 PM EST
Rosters: All teams at 12 games played (6-6-0, 7-5-0, etc.)
Sleeper leg: 12
```

**Detection Result:**
```
✓ All teams completed 6 weeks (12 games / 2)
✓ Matches Sleeper leg 12
✓ Week 12 is FINALIZED
→ current_week.json: { "current_week": 12 }
```

### Scenario 2: Tuesday Morning After Waivers

**State:**
```
Time: Tuesday 9:00 AM EST
Rosters: Still at 12 games played (no new games yet!)
Sleeper leg: 13 (advanced during waivers)
```

**Detection Result:**
```
✓ All teams completed 6 weeks (12 games / 2)
⚠️ Sleeper leg is 13 (one ahead)
✓ Games complete, waivers processed, but Week 13 hasn't started
→ current_week.json: { "current_week": 12 }
```

**Why Week 12?** Because roster records prove only 12 games have been played. Week 13 games haven't happened yet!

### Scenario 3: Mid-Week Update

**State:**
```
Time: Wednesday 2:00 PM EST
Rosters: Still at 12 games played
Sleeper leg: 13
```

**Detection Result:**
```
✓ All teams completed 6 weeks (12 games / 2)
✓ Week 13 in progress but not complete
→ current_week.json: { "current_week": 12 }
```

### Scenario 4: Next Week Completes

**State:**
```
Time: Next Monday 11:00 PM EST
Rosters: All teams at 14 games played (7-7-0, 8-6-0, etc.)
Sleeper leg: 13
```

**Detection Result:**
```
✓ All teams completed 7 weeks (14 games / 2)
✓ Matches Sleeper leg 13
✓ Week 13 is FINALIZED
→ current_week.json: { "current_week": 13 }
```

---

## Troubleshooting

### Problem: "Week config file not found"

**Error:**
```
FileNotFoundError: Week config file not found: pipeline/config/current_week.json
Please run: python3 scripts/detect_current_week.py
```

**Solution:**
```bash
cd pipeline
python3 scripts/detect_current_week.py
```

**Why it happens:** Stage 0 (week detection) must run before other stages.

---

### Problem: Scripts using wrong week

**Symptoms:**
- Playoff scenarios show incorrect probabilities
- Standings reference future week
- Dashboard shows "Week 13" but games aren't played

**Diagnosis:**
```bash
# Check current week in config
cat pipeline/config/current_week.json

# Verify against Sleeper manually
# Check a team's roster record at: https://sleeper.com/roster/[league_id]/[roster_id]
# Calculate: (wins + losses + ties) / 2 = weeks_completed
```

**Solution:**
```bash
# Re-run Stage 0 to update week
cd pipeline
python3 scripts/detect_current_week.py

# Then re-run dependent stages
python3 scripts/fetch_standings.py
python3 scripts/simulate_playoff_scenarios.py
```

---

### Problem: Inconsistent roster records

**Symptoms:**
```
WARNING: Teams have inconsistent completion: 11 to 12 weeks
```

**Diagnosis:**
- One or more teams have different game counts
- Shouldn't happen in normal Sleeper leagues
- May indicate data sync issue

**Solution:**
1. Check Sleeper API directly for affected rosters
2. Wait 5-10 minutes and re-run detection (API may be syncing)
3. If persists, use minimum completed week as safe fallback
4. Report to Sleeper support if data issue confirmed

---

### Problem: Week advances too early

**Symptoms:**
- Scripts run Tuesday morning
- Week shows 13 but only 12 games played
- Need to revert to Week 12

**Solution:**
✅ **This is exactly what the validation prevents!** The math-based validation will:
1. Calculate `12 games / 2 = 6 weeks` from rosters
2. See Sleeper leg is 7 (one ahead)
3. Correctly report Week 6 as current
4. Write `current_week: 6` to config

**No manual intervention needed** - the system handles this automatically!

---

## When to Manually Run detect_current_week.py

### Run Detection When:

1. **🔄 Before running full pipeline** (automated in `update_dashboard.py`)
   ```bash
   python3 update_dashboard.py  # Runs Stage 0 automatically
   ```

2. **🐛 Debugging week-related issues**
   ```bash
   cd pipeline
   python3 scripts/detect_current_week.py
   cat config/current_week.json  # Verify output
   ```

3. **📅 After week transitions** (Monday night → Tuesday)
   ```bash
   # Wait until Tuesday afternoon to ensure waivers processed
   cd pipeline
   python3 scripts/detect_current_week.py
   ```

4. **🔧 Manual testing with specific week**
   ```python
   # Edit current_week.json manually for testing
   {
     "current_week": 11,  # Test with Week 11 data
     "last_updated": "Manual override for testing"
   }
   ```

### Don't Run Detection When:

❌ **Mid-week for routine updates** - Week doesn't change until games complete
❌ **Multiple times in same day** - Week won't change until next games play
❌ **During games** - Wait for Monday Night Football to finish

---

## Scripts That Depend on current_week.json

### Stage 8: `fetch_standings.py`
- Reads current week for context
- Includes in standings output
- Used for "X weeks remaining" calculations

### Stage 9: `simulate_playoff_scenarios.py`
- **Critical dependency** - Uses current week to:
  - Calculate remaining games
  - Determine simulation scope
  - Project final standings

### Stage 9: `calculate_playoff_scenarios.py`
- Uses current week for:
  - Clinch/elimination scenarios
  - Tiebreaker analysis
  - Remaining schedule strength

### Dashboard JSON Generation
- Week number displayed on frontend
- "Through Week X" labels
- Historical context for trades/standings

---

## Benefits of Centralized Detection

### ✅ Before: Each Script Had Its Own Logic
```python
# fetch_standings.py
current_week = league_info.get('settings', {}).get('leg', 1) - 1

# simulate_playoff_scenarios.py  
current_week = league_info.get('settings', {}).get('leg', 12)

# calculate_playoff_scenarios.py
current_week = rosters[0].get('settings', {}).get('wins', 0) // 2
```

**Problems:**
- 3 different formulas
- No validation
- Tuesday timing bugs
- Inconsistent across pipeline

### ✅ After: Single Source of Truth
```python
# All scripts
from utils.week_config import get_current_week_from_config
current_week = get_current_week_from_config()
```

**Benefits:**
- One formula, validated
- Consistent across pipeline
- Tuesday-safe
- Easy to debug

---

## Technical Implementation Details

### detect_current_week.py Key Functions

```python
def validate_week_completion(rosters: list, sleeper_leg: int) -> int:
    """
    Validate using roster records.
    Returns validated current week (1-14).
    """
    weeks_completed_list = []
    for roster in rosters:
        wins = roster['settings']['wins']
        losses = roster['settings']['losses']
        ties = roster['settings']['ties']
        
        # Critical formula for dual-game format
        weeks_completed = (wins + losses + ties) / 2
        weeks_completed_list.append(weeks_completed)
    
    # Validate all teams match
    if len(set(weeks_completed_list)) == 1:
        validated_week = int(weeks_completed_list[0])
        
        # Compare to Sleeper's leg
        if validated_week == sleeper_leg:
            return validated_week  # Week finalized
        elif validated_week == sleeper_leg - 1:
            return validated_week  # Tuesday morning case
        else:
            return validated_week  # Use records as truth
    else:
        # Inconsistent - use minimum as safe fallback
        return int(min(weeks_completed_list))
```

### week_config.py Utility

```python
def get_current_week_from_config() -> int:
    """
    Read validated week from config file.
    Raises FileNotFoundError if config doesn't exist.
    """
    config_file = Path(__file__).parent.parent / "config" / "current_week.json"
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"Week config file not found: {config_file}\n"
            f"Please run: python3 scripts/detect_current_week.py"
        )
    
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    return int(config_data['current_week'])
```

---

## Related Documentation

- [DATA_ARCHITECTURE.md](./DATA_ARCHITECTURE.md#week-detection-architecture) - How week detection fits into overall architecture
- [PIPELINE_DOCUMENTATION.md](./PIPELINE_DOCUMENTATION.md) - Full pipeline stages including Stage 0

---

## Summary

The centralized week detection system:

1. **🛡️ Protects against Tuesday timing bugs** using roster record validation
2. **📐 Uses mathematical formula** `(wins + losses + ties) / 2` for accuracy
3. **📝 Single source of truth** in `current_week.json` for all scripts
4. **⚡ Runs as Stage 0** before all other pipeline stages
5. **🔄 Eliminates inconsistencies** across 4+ scripts that need week info

**The key insight:** Don't trust Sleeper's `leg` field blindly - validate using actual game results stored in roster records. This makes our pipeline robust to timing issues during waiver processing.