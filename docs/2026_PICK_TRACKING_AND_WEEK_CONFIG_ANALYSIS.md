# 2026 Draft Pick Tracking and Week Configuration Analysis

**Date:** December 29, 2024  
**Status:** Analysis Documentation  
**Purpose:** Comprehensive documentation of the 2026 draft pick tracking system, weekly projections process, and week configuration architecture

---

## Table of Contents

1. [Current Pick Ownership System](#1-current-pick-ownership-system)
2. [Draft Order Rules Status](#2-draft-order-rules-status)
3. [Weekly Projections Update Process](#3-weekly-projections-update-process)
4. [Week Configuration Analysis](#4-week-configuration-analysis)
5. [Week Tracking Enhancement Options](#5-week-tracking-enhancement-options)
6. [Next Steps](#6-next-steps)

---

## 1. Current Pick Ownership System

### How the System Works

The 2026 draft pick tracking system uses **transaction-based ownership tracking**. Rather than maintaining a static snapshot, the system:

- Processes all historical trades involving 2026 draft picks
- Applies transactions chronologically to determine current ownership
- Tracks pick movements from original owners to current holders
- Maintains complete audit trail of pick transfers

### Algorithm Description

The core algorithm is implemented in [`pipeline/analyze_2026_pick_ownership.py`](../pipeline/analyze_2026_pick_ownership.py):

```python
# Transaction Processing Algorithm:
# 1. Initialize picks with original owners (12 teams × 4 rounds = 48 picks)
# 2. Fetch all trades from league history
# 3. Filter trades containing 2026 draft picks
# 4. Sort trades chronologically by transaction timestamp
# 5. For each trade:
#    - Identify picks being transferred
#    - Update ownership mapping
#    - Record transfer details (from/to, timestamp, trade context)
# 6. Generate ownership reports and metrics
```

**Key Features:**
- Handles multi-team trades (2 or 3+ teams)
- Tracks conditional pick swaps
- Identifies pick concentrations (teams with multiple picks in same round)
- Validates ownership integrity (all 48 picks accounted for)

### Pipeline Integration

**Stage:** 6 (Post-Processing Analytics)  
**Execution:** Daily (part of automated pipeline refresh)  
**Dependencies:** 
- [`pipeline/stage1_fetch_trades.py`](../pipeline/stage1_fetch_trades.py) - Raw trade data
- [`pipeline/trades_raw.json`](../pipeline/trades_raw.json) - Trade history source

### Current Ownership Highlights

Based on latest analysis:

| Manager | 1st Round Picks | Notable Holdings |
|---------|----------------|------------------|
| mgaeta23 | 4 | Owns 33% of all 1st round picks |
| Others | TBD | Analysis in [`pipeline/2026_pick_ownership_analysis.md`](../pipeline/2026_pick_ownership_analysis.md) |

**Pick Concentration Risk:**
- Multiple managers holding 2+ picks in same round
- Some teams have traded away all picks in certain rounds
- Creates strategic imbalances for draft day

### Outputs Generated

The script generates three key outputs:

1. **Detailed JSON** ([`pipeline/2026_pick_ownership_detailed.json`](../pipeline/2026_pick_ownership_detailed.json))
   - Complete pick-by-pick ownership
   - Transaction history per pick
   - Transfer chains

2. **Metrics CSV** ([`pipeline/2026_pick_ownership_metrics.csv`](../pipeline/2026_pick_ownership_metrics.csv))
   - Team-by-team pick counts
   - Round distribution
   - Asset strength metrics

3. **Analysis Report** ([`pipeline/2026_pick_ownership_analysis.md`](../pipeline/2026_pick_ownership_analysis.md))
   - Human-readable summary
   - Strategic insights
   - Ownership patterns

---

## 2. Draft Order Rules Status

### What IS Defined

The system currently has well-defined components:

#### Draft Pick Tiers
```
Tier 1: Early (Picks 1-4)   - Highest value
Tier 2: Mid (Picks 5-8)      - High value  
Tier 3: Late (Picks 9-12)    - Medium value
```

#### Dynasty Values
- Each tier has assigned point values in dynasty valuation system
- Used for trade analysis and roster construction metrics
- Integrated into [`pipeline/stage3_cache_values.py`](../pipeline/stage3_cache_values.py)

#### Playoff Structure
- 6 teams make playoffs (seeds 1-6)
- Bottom 6 teams miss playoffs (seeds 7-12)
- Playoff weeks: 15, 16, 17
- Regular season: Weeks 1-14

### What is MISSING

**Critical Gap:** No automated draft order determination rules

The system lacks:
- Automated tier assignment based on final standings
- Draft order calculation logic for non-playoff teams (picks 7-12)
- Draft order calculation logic for playoff teams (picks 1-6)
- Handling of regular season tiebreakers
- Integration of playoff performance into pick order

**Current State:** Draft order tiers are assigned manually or remain generic placeholders.

### Current Manual Tier Assignment Process

Without automated rules, tier assignment requires:

1. Manual review of final standings after Week 17
2. Application of tiebreaker rules (Points For as tiebreaker)
3. Manual assignment of each pick to Tier 1/2/3
4. Manual update of [`pipeline/weekly_2026_pick_projections_expanded.csv`](../pipeline/weekly_2026_pick_projections_expanded.csv)

**Issues:**
- Prone to human error
- Not reproducible
- Requires manual intervention
- Cannot project future scenarios accurately

### Gap Analysis

| Component | Status | Impact |
|-----------|--------|--------|
| Pick ownership tracking | ✅ Complete | Working well |
| Pick valuation tiers | ✅ Defined | Values established |
| Weekly projections (2nd-4th) | ✅ Automated | Updates work |
| **Draft order rules** | ❌ Missing | **Blocking accurate projections** |
| 1st round tier assignment | ❌ Manual | Cannot automate updates |
| Playoff integration | ❌ None | 1st round picks inaccurate |

---

## 3. Weekly Projections Update Process

### How It Works

The [`pipeline/scripts/update_weekly_projections.py`](../pipeline/scripts/update_weekly_projections.py) script automates weekly projection updates:

```python
# Update Process:
# 1. Fetch current week standings data
# 2. Sort teams by win-loss record
# 3. Apply tiebreaker (Points For)
# 4. Reverse standings to get draft order
# 5. Update CSV for rounds 2, 3, and 4 ONLY
# 6. Preserve existing 1st round tier assignments
```

**Key Point:** This is a **projection** system that updates weekly as standings change, not final draft order determination.

### What It Updates

**Scope of Updates:**
- ✅ 2nd round picks (Tier 2) - Based on current standings
- ✅ 3rd round picks (Tier 2/3 boundary) - Based on current standings  
- ✅ 4th round picks (Tier 3) - Based on current standings

**Columns Updated in CSV:**
- `projected_pick_number_week_N` (where N = current week)
- `projected_tier_week_N`
- Separate columns for each week (Week 1 through Week 17)

### What It Doesn't Do

**Explicitly Excluded:**
- ❌ Does NOT update 1st round picks
- ❌ Does NOT modify existing tier assignments
- ❌ Does NOT overwrite manual corrections
- ❌ Does NOT incorporate playoff results (no access to bracket data)

**Reasoning:**
- 1st round picks depend on playoff outcomes (unknown until Week 17)
- Preserves manual overrides when needed
- Respects existing tier assignments made by other processes

### Issue Identified: Inline Week Calculation

**Problem:** The script calculates current week inline:

```python
# Current implementation (problematic):
current_week = calculate_week_inline(nfl_season_start)

def calculate_week_inline(season_start):
    # Logic embedded in script
    # Not using centralized config
    # May conflict with other scripts
```

**Impact:**
- Different scripts may calculate week differently
- No single source of truth for "current week"
- Difficult to override for manual testing
- Inconsistent with [`pipeline/config/current_week.json`](../pipeline/config/current_week.json)

**Contrast with Other Scripts:**
- [`pipeline/scripts/detect_current_week.py`](../pipeline/scripts/detect_current_week.py) - Writes to config
- Other scripts - Read from config
- `update_weekly_projections.py` - Ignores config ❌

---

## 4. Week Configuration Analysis

### Current State

**Config File:** [`pipeline/config/current_week.json`](../pipeline/config/current_week.json)

```json
{
  "current_week": 16,
  "last_updated": "2024-12-28T10:30:00Z",
  "season_year": 2024
}
```

**Purpose:**
- Central source of truth for current NFL week
- Used by multiple pipeline scripts
- Enables manual override during testing
- Supports rollback scenarios

### How Detection Works

The [`pipeline/scripts/detect_current_week.py`](../pipeline/scripts/detect_current_week.py) script:

```python
# Detection Algorithm:
# 1. Define NFL season start date (hardcoded or configurable)
# 2. Calculate days since season start
# 3. Convert to NFL week: week = (days_elapsed // 7) + 1
# 4. Apply bounds: min=1, max=18 (includes Week 18)
# 5. Write result to current_week.json
# 6. Add timestamp and season_year
```

**Execution:**
- Can be run manually: `python pipeline/scripts/detect_current_week.py`
- Can be scheduled (cron, GitHub Actions)
- Idempotent - safe to run multiple times

### Scripts Using Week Config

Four scripts currently read from [`pipeline/config/current_week.json`](../pipeline/config/current_week.json):

| Script | Usage | Week Type |
|--------|-------|-----------|
| [`pipeline/scripts/fetch_standings.py`](../pipeline/scripts/fetch_standings.py) | Label standings data | Regular season week |
| [`pipeline/scripts/calculate_playoff_scenarios.py`](../pipeline/scripts/calculate_playoff_scenarios.py) | Simulate remaining weeks | Regular season week |
| [`pipeline/scripts/simulate_playoff_scenarios.py`](../pipeline/scripts/simulate_playoff_scenarios.py) | Playoff bracket sims | Playoff week (15-17) |
| [`pipeline/scripts/generate_dashboard_json.py`](../pipeline/scripts/generate_dashboard_json.py) | Data labeling | Context-dependent |

**Utility Module:** [`pipeline/utils/week_config.py`](../pipeline/utils/week_config.py)
- Provides `get_current_week()` function
- Reads from config file
- Used by scripts above

### The Dual-Week Problem

**Critical Issue:** Week 14 confusion during playoffs

**Scenario:**
- Regular season: Week 1-14 (14 weeks)
- Playoff rounds: Week 15-17 (3 weeks)
- **NFL Calendar Week:** Can be Week 15, 16, 17 (actual NFL week)
- **Fantasy Season Week:** Week 14 (last reg. season) vs Week 16 (playoff week 2)

**Example Confusion:**
```
NFL Week 16 = Fantasy Regular Season Week 14 (final week)
BUT ALSO
NFL Week 16 = Fantasy Playoff Week 2 (divisional round)
```

**Impact:**
- [`pipeline/scripts/simulate_playoff_scenarios.py`](../pipeline/scripts/simulate_playoff_scenarios.py) needs **playoff week** (15-17)
- [`pipeline/scripts/calculate_playoff_scenarios.py`](../pipeline/scripts/calculate_playoff_scenarios.py) needs **regular season week** (1-14)
- Single config value cannot serve both needs simultaneously

**Current Workaround:** Scripts make assumptions, but no explicit handling

---

## 5. Week Tracking Enhancement Options

To resolve the week configuration issues, four options were identified:

### Option A: Dual-Value Config

**Approach:** Store both regular season week and playoff week in config

```json
{
  "regular_season_week": 14,
  "playoff_week": 2,
  "nfl_calendar_week": 16,
  "last_updated": "2024-12-28T10:30:00Z"
}
```

**Pros:**
- Explicit separation of contexts
- Scripts pick appropriate value
- Clear semantics

**Cons:**
- More complex config
- Scripts must choose correctly
- Requires updating multiple fields

---

### Option B: Week Type Parameter

**Approach:** Scripts specify what type of week they need

```python
week = get_current_week(week_type="regular_season")  # Returns 1-14
week = get_current_week(week_type="playoff")          # Returns 15-17
week = get_current_week(week_type="nfl_calendar")    # Returns actual NFL week
```

**Pros:**
- Single config value (NFL week)
- Logic in utility function
- Scripts declare intent

**Cons:**
- Requires conversion logic
- Scripts must know which type to request
- Potential for misconfiguration

---

### Option C: Phase-Based Config

**Approach:** Config indicates current season phase

```json
{
  "season_phase": "playoffs",  // or "regular_season"
  "nfl_week": 16,
  "regular_season_week": 14,
  "playoff_round": 2,
  "last_updated": "2024-12-28T10:30:00Z"
}
```

**Pros:**
- Context-aware
- Scripts adapt to phase
- Explicit state machine

**Cons:**
- Most complex option
- Requires phase transitions
- Overhead for simple cases

---

### Option D: Separate Config Files

**Approach:** Different configs for different purposes

```
pipeline/config/regular_season_week.json
pipeline/config/playoff_week.json
pipeline/config/nfl_calendar_week.json
```

**Pros:**
- Complete separation
- No ambiguity
- Independent updates

**Cons:**
- Multiple files to manage
- Synchronization issues
- Harder to maintain

---

### Key Decision Questions

To choose the right option, consider:

1. **How often do scripts need both values?**
   - If rarely: Option B (parameter-based)
   - If frequently: Option A (dual-value)

2. **Do we need historical phase tracking?**
   - If yes: Option C (phase-based)
   - If no: Option A or B

3. **Is configuration simplicity critical?**
   - If yes: Option B (single source, smart utility)
   - If no: Option A or C

4. **Do we need independent update schedules?**
   - If yes: Option D (separate files)
   - If no: Option A, B, or C

### Recommendation Framework

**For Most Projects:** **Option B (Week Type Parameter)**
- Balance of simplicity and explicitness
- Backward compatible (can add optional parameter)
- Clear intent in script code
- Single source of truth

**For Complex Needs:** **Option C (Phase-Based)**
- If need to track season transitions
- If many phase-dependent behaviors
- If building historical analytics

**Avoid:** **Option D (Separate Files)**
- Added complexity without clear benefits
- Synchronization burden
- Better handled by Option A or C

---

## 6. Next Steps

### Decisions Required

1. **Draft Order Rules:**
   - Define exact rules for Tier 1 (picks 1-6) based on playoff results
   - Define exact rules for Tier 2/3 (picks 7-12) based on regular season
   - Document tiebreaker application
   - Create implementation specification

2. **Week Configuration:**
   - Choose enhancement option (A, B, C, or D)
   - Define transition points (when does playoff phase start?)
   - Specify behavior during Week 15-17
   - Plan backward compatibility

3. **Weekly Projections:**
   - Decide if `update_weekly_projections.py` should use centralized config
   - Define behavior during playoff weeks
   - Clarify relationship to final draft order determination

### Implementation Approach

**Phase 1: Draft Order Rules (Priority 1)**
1. Document draft order determination rules
2. Create `calculate_draft_order.py` script
3. Integrate with playoff bracket data
4. Test with historical seasons
5. Update weekly projections to handle 1st round

**Phase 2: Week Config Enhancement (Priority 2)**
1. Choose option (recommend Option B)
2. Update [`pipeline/utils/week_config.py`](../pipeline/utils/week_config.py)
3. Add `week_type` parameter to `get_current_week()`
4. Update all scripts using week config
5. Add unit tests
6. Update documentation in [`docs/guides/WEEK_DETECTION.md`](../docs/guides/WEEK_DETECTION.md)

**Phase 3: Integration (Priority 3)**
1. Connect draft order calculation to weekly projections
2. Ensure 1st round tier assignments automated
3. Add validation checks
4. Create end-to-end test for full season flow

**Phase 4: Documentation (Ongoing)**
1. Update [`docs/guides/PIPELINE_DOCUMENTATION.md`](../docs/guides/PIPELINE_DOCUMENTATION.md)
2. Add draft order rules to documentation
3. Create examples and test cases
4. Document manual override procedures

---

## Appendix: Related Files

### Core Implementation Files
- [`pipeline/analyze_2026_pick_ownership.py`](../pipeline/analyze_2026_pick_ownership.py) - Pick tracking algorithm
- [`pipeline/scripts/update_weekly_projections.py`](../pipeline/scripts/update_weekly_projections.py) - Weekly projection updates
- [`pipeline/scripts/detect_current_week.py`](../pipeline/scripts/detect_current_week.py) - Week detection
- [`pipeline/utils/week_config.py`](../pipeline/utils/week_config.py) - Week config utility

### Configuration Files
- [`pipeline/config/current_week.json`](../pipeline/config/current_week.json) - Current week config
- [`pipeline/config/default.yaml`](../pipeline/config/default.yaml) - Pipeline defaults

### Data Files
- [`pipeline/weekly_2026_pick_projections_expanded.csv`](../pipeline/weekly_2026_pick_projections_expanded.csv) - Weekly projections
- [`pipeline/2026_pick_ownership_detailed.json`](../pipeline/2026_pick_ownership_detailed.json) - Pick ownership details
- [`pipeline/2026_pick_ownership_metrics.csv`](../pipeline/2026_pick_ownership_metrics.csv) - Ownership metrics

### Documentation
- [`docs/guides/PIPELINE_DOCUMENTATION.md`](../docs/guides/PIPELINE_DOCUMENTATION.md) - Pipeline guide
- [`docs/guides/WEEK_DETECTION.md`](../docs/guides/WEEK_DETECTION.md) - Week detection guide
- [`docs/guides/DATA_ARCHITECTURE.md`](../docs/guides/DATA_ARCHITECTURE.md) - Data architecture

---

**Document Status:** Analysis Complete - Awaiting Implementation Decisions  
**Next Review:** After draft order rules are defined  
**Owner:** Pipeline Development Team
