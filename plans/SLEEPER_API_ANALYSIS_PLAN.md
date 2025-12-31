# Sleeper API Analysis Plan

**Date:** December 29, 2024
**Status:** ✅ Analysis Complete
**Purpose:** Validate design assumptions against actual Sleeper API capabilities

> **Note:** Analysis complete. Results documented in [`SLEEPER_API_CAPABILITIES.md`](SLEEPER_API_CAPABILITIES.md). Implementation integrated into pipeline.

---

## Objective

Before implementing the draft order system, we need to verify:
1. ✅ What week information does Sleeper provide?
2. ✅ What playoff data is available during playoffs?
3. ✅ How are matchup results structured?
4. ✅ Does Sleeper track playoff bracket state?
5. ✅ What do we need to calculate ourselves?

---

## Known Sleeper API Endpoints

### Currently Used in Pipeline

From [`pipeline/utils/api_client.py`](../pipeline/utils/api_client.py) and existing scripts:

| Endpoint | Purpose | Used By |
|----------|---------|---------|
| `/v1/state/nfl` | NFL state (week, season) | [`validators.py`](../pipeline/utils/validators.py) |
| `/v1/league/{league_id}` | League metadata | [`fetch_standings.py`](../pipeline/scripts/fetch_standings.py) |
| `/v1/league/{league_id}/rosters` | Team rosters and records | [`fetch_standings.py`](../pipeline/scripts/fetch_standings.py) |
| `/v1/league/{league_id}/users` | User/team names | [`fetch_standings.py`](../pipeline/scripts/fetch_standings.py) |
| `/v1/league/{league_id}/matchups/{week}` | Weekly matchups | [`fetch_lineup_data.py`](../pipeline/scripts/fetch_lineup_data.py) |
| `/v1/stats/nfl/{season_type}/{season}/{week}` | Player stats | [`fetch_player_stats.py`](../pipeline/scripts/fetch_player_stats.py) |
| `/v1/players/nfl` | All NFL players | [`generate_waiver_wire_dashboard_json.py`](../pipeline/scripts/generate_waiver_wire_dashboard_json.py) |

---

## Analysis Tasks

### Task 1: Investigate NFL State Endpoint

**Endpoint:** `GET https://api.sleeper.app/v1/state/nfl`

**Questions to Answer:**
1. What is the current week number returned?
2. Does it distinguish between regular season and playoff weeks?
3. What is the `season_type` field? (regular, playoff, postseason?)
4. Is there a `display_week` vs `leg` (week number)?
5. What happens after Week 18 / during offseason?

**Expected Response Structure:**
```json
{
  "week": ???,
  "season_type": ???,
  "season": "2024",
  "leg": ???,
  "display_week": ???,
  "season_start_date": ???,
  "previous_season": ???
}
```

**Script to Run:**
```python
# pipeline/scripts/analyze_sleeper_nfl_state.py
import requests
import json

response = requests.get("https://api.sleeper.app/v1/state/nfl")
data = response.json()

print("=== NFL State Endpoint ===")
print(json.dumps(data, indent=2))
print("\nKey Fields:")
print(f"  Week: {data.get('week')}")
print(f"  Season Type: {data.get('season_type')}")
print(f"  Season: {data.get('season')}")
```

---

### Task 2: Investigate League Metadata

**Endpoint:** `GET https://api.sleeper.app/v1/league/{league_id}`

**Questions to Answer:**
1. Does `settings` include playoff bracket info?
2. Is there a `playoff_week_start` field?
3. Does it track current bracket state?
4. What's in the `metadata` object?

**Expected Fields:**
```json
{
  "league_id": "...",
  "name": "Dynasuiiii",
  "season": "2024",
  "settings": {
    "playoff_week_start": ???,
    "playoff_round_type": ???,
    "playoff_type": ???,
    "playoff_teams": 6,
    "playoff_seed_type": ???
  },
  "metadata": {
    ...
  }
}
```

**Script to Run:**
```python
# Extend analyze_sleeper_api.py
league_response = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}")
league_data = league_response.json()

print("\n=== League Metadata ===")
print("Settings:")
print(json.dumps(league_data.get('settings', {}), indent=2))
print("\nMetadata:")
print(json.dumps(league_data.get('metadata', {}), indent=2))
```

---

### Task 3: Analyze Rosters During Playoffs

**Endpoint:** `GET https://api.sleeper.app/v1/league/{league_id}/rosters`

**Questions to Answer:**
1. Does `settings` include playoff position/seed?
2. Is there a `playoff_seed` or `bracket_position` field?
3. Does it track elimination status?
4. What's the difference between regular season stats and current stats during playoffs?

**Expected Response (per roster):**
```json
{
  "roster_id": 7,
  "owner_id": "...",
  "settings": {
    "wins": 22,
    "losses": 6,
    "ties": 0,
    "fpts": 200006,
    "fpts_decimal": 0,
    "fpts_against": 180290,
    "division": 3,
    
    // Playoff fields?
    "playoff_seed": ???,
    "playoff_status": ???,
    "bracket_id": ???
  },
  "metadata": {
    ...
  }
}
```

**Script to Run:**
```python
rosters = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters")
rosters_data = rosters.json()

print("\n=== Roster Data (First Team) ===")
print(json.dumps(rosters_data[0], indent=2))

print("\n=== All Settings Fields ===")
for key in rosters_data[0].get('settings', {}).keys():
    print(f"  - {key}")
```

---

### Task 4: Analyze Matchups During Playoffs

**Endpoint:** `GET https://api.sleeper.app/v1/league/{league_id}/matchups/{week}`

**Questions to Answer:**
1. How are playoff matchups structured differently from regular season?
2. Is there a `bracket_id` or `playoff_tier` field?
3. Can we identify Championship vs 3rd Place vs Toilet Bowl?
4. Is there a `matchup_type` field?

**Expected Response (per matchup):**
```json
{
  "matchup_id": 1,
  "roster_id": 7,
  "points": 127.42,
  "players": [...],
  "starters": [...],
  
  // Playoff fields?
  "bracket_id": ???,
  "playoff_tier": ???,
  "matchup_type": ???,
  "round": ???
}
```

**Script to Run:**
```python
# Check multiple weeks
for week in [14, 15, 16, 17]:
    matchups = requests.get(
        f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{week}"
    )
    if matchups.status_code == 200:
        data = matchups.json()
        print(f"\n=== Week {week} Matchups ===")
        print(f"Number of matchups: {len(data)}")
        
        if data:
            print("First matchup structure:")
            print(json.dumps(data[0], indent=2))
            
            # Check for special fields
            unique_matchup_ids = set(m.get('matchup_id') for m in data)
            print(f"Unique matchup_ids: {unique_matchup_ids}")
```

---

### Task 5: Check Bracket/Winners Endpoint

**Question:** Does Sleeper have a `/winners_bracket` or `/losers_bracket` endpoint?

**Potential Endpoints to Try:**
```
/v1/league/{league_id}/winners_bracket
/v1/league/{league_id}/winners_bracket/{round}
/v1/league/{league_id}/losers_bracket
/v1/league/{league_id}/playoff_bracket
/v1/league/{league_id}/brackets
```

**Script to Run:**
```python
endpoints_to_try = [
    f"/v1/league/{LEAGUE_ID}/winners_bracket",
    f"/v1/league/{LEAGUE_ID}/losers_bracket",
    f"/v1/league/{LEAGUE_ID}/playoff_bracket",
    f"/v1/league/{LEAGUE_ID}/brackets",
]

print("\n=== Testing Bracket Endpoints ===")
for endpoint in endpoints_to_try:
    url = f"https://api.sleeper.app{endpoint}"
    response = requests.get(url)
    print(f"\n{endpoint}")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        print(f"  Data: {json.dumps(response.json(), indent=2)}")
```

---

## Analysis Script Template

**File:** [`pipeline/scripts/analyze_sleeper_api.py`](../pipeline/scripts/analyze_sleeper_api.py) (NEW)

```python
#!/usr/bin/env python3
"""
Analyze Sleeper API capabilities for draft order system.

Investigates:
1. NFL state and week tracking
2. League metadata and playoff settings
3. Roster data during playoffs
4. Matchup structure in playoff weeks
5. Bracket/winners endpoints

Usage:
    python pipeline/scripts/analyze_sleeper_api.py <league_id>
"""

import requests
import json
import sys
from typing import Dict, Any

def fetch_and_display(url: str, title: str) -> Dict[str, Any]:
    """Fetch from URL and display formatted"""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}")
    print(f"URL: {url}\n")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nResponse ({len(json.dumps(data))} bytes):")
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Exception: {e}")
        return None

def analyze_nfl_state():
    """Analyze NFL state endpoint"""
    url = "https://api.sleeper.app/v1/state/nfl"
    data = fetch_and_display(url, "1. NFL STATE ENDPOINT")
    
    if data:
        print("\n--- Key Observations ---")
        print(f"Current Week: {data.get('week')}")
        print(f"Season Type: {data.get('season_type')}")
        print(f"Season: {data.get('season')}")
        
        # Check all fields
        print("\nAll Available Fields:")
        for key, value in data.items():
            print(f"  - {key}: {value}")

def analyze_league(league_id: str):
    """Analyze league metadata"""
    url = f"https://api.sleeper.app/v1/league/{league_id}"
    data = fetch_and_display(url, "2. LEAGUE METADATA")
    
    if data:
        print("\n--- Playoff Settings ---")
        settings = data.get('settings', {})
        playoff_keys = [k for k in settings.keys() if 'playoff' in k.lower()]
        for key in playoff_keys:
            print(f"  - {key}: {settings[key]}")

def analyze_rosters(league_id: str):
    """Analyze roster data structure"""
    url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    data = fetch_and_display(url, "3. ROSTERS DATA")
    
    if data and len(data) > 0:
        print("\n--- First Roster Settings ---")
        settings = data[0].get('settings', {})
        for key, value in settings.items():
            print(f"  - {key}: {value}")

def analyze_matchups(league_id: str, weeks: list):
    """Analyze matchup data for multiple weeks"""
    for week in weeks:
        url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
        data = fetch_and_display(url, f"4. MATCHUPS - WEEK {week}")
        
        if data:
            print(f"\n--- Week {week} Observations ---")
            print(f"Total matchups: {len(data)}")
            
            # Unique matchup IDs
            matchup_ids = set(m.get('matchup_id') for m in data)
            print(f"Unique matchup_ids: {sorted(matchup_ids)}")
            
            # Check for playoff-specific fields
            if len(data) > 0:
                print("\nFirst matchup fields:")
                for key in data[0].keys():
                    print(f"  - {key}")

def try_bracket_endpoints(league_id: str):
    """Try various bracket-related endpoints"""
    endpoints = [
        f"/v1/league/{league_id}/winners_bracket",
        f"/v1/league/{league_id}/winners_bracket/1",
        f"/v1/league/{league_id}/losers_bracket",
        f"/v1/league/{league_id}/losers_bracket/1",
        f"/v1/league/{league_id}/playoff_bracket",
        f"/v1/league/{league_id}/brackets",
    ]
    
    print(f"\n{'=' * 80}")
    print("5. TESTING BRACKET ENDPOINTS")
    print(f"{'=' * 80}\n")
    
    for endpoint in endpoints:
        url = f"https://api.sleeper.app{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            status = "✅ EXISTS" if response.status_code == 200 else f"❌ {response.status_code}"
            print(f"{status} - {endpoint}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"         Data: {json.dumps(data, indent=2)[:200]}...")
        except Exception as e:
            print(f"❌ ERROR - {endpoint}: {e}")

def main():
    """Run full analysis"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_sleeper_api.py <league_id>")
        print("\nExample: python analyze_sleeper_api.py 1050048277552975872")
        sys.exit(1)
    
    league_id = sys.argv[1]
    
    print("=" * 80)
    print("SLEEPER API ANALYSIS")
    print("=" * 80)
    print(f"League ID: {league_id}")
    print(f"Current Date: 2024-12-29 (Week 17 NFL)")
    print("=" * 80)
    
    # Run analyses
    analyze_nfl_state()
    analyze_league(league_id)
    analyze_rosters(league_id)
    analyze_matchups(league_id, weeks=[14, 15, 16, 17])
    try_bracket_endpoints(league_id)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Review output to understand API capabilities")
    print("2. Identify gaps between API data and design requirements")
    print("3. Update design documents with API constraints")
    print("4. Determine what needs to be calculated vs fetched")

if __name__ == "__main__":
    main()
```

---

## Specific Questions to Investigate

### Week Tracking

**Current Assumption:** We need to track `through_week` separately from `current_week`

**Questions:**
1. ✅ Does `/state/nfl` give us a single "current week" or multiple values?
2. ✅ If single value, does it update immediately when week starts or after it completes?
3. ✅ How do we know when Week 16 matchup results are complete vs Week 17 just starting?

**Test Approach:**
```python
# Compare NFL state week vs matchup data availability
nfl_state = fetch("https://api.sleeper.app/v1/state/nfl")
current_week = nfl_state['week']

# Try to fetch matchups for current week - 1, current week, current week + 1
for week in [current_week - 1, current_week, current_week + 1]:
    matchups = fetch(f".../matchups/{week}")
    if matchups:
        print(f"Week {week}: {len(matchups)} matchups returned")
        # Check if scores are populated (0 = not played yet)
        has_scores = any(m.get('points', 0) > 0 for m in matchups)
        print(f"  Has scores: {has_scores}")
```

---

### Playoff Bracket Identification

**Current Assumption:** We need to manually identify which matchup is championship vs 3rd place vs toilet bowl

**Questions:**
1. ✅ Does Sleeper differentiate playoff bracket types in matchup data?
2. ✅ Can we identify consolation vs playoff matchups?
3. ✅ Is there a `bracket_id` field (1=winners, 2=losers)?
4. ✅ Does `matchup_id` have special meaning during playoffs?

**Test Approach:**
```python
# Fetch Week 17 matchups (should have Championship, 3rd Place, Consolation)
week_17_matchups = fetch(f".../matchups/17")

# Group by matchup_id
from collections import defaultdict
grouped = defaultdict(list)
for m in week_17_matchups:
    grouped[m['matchup_id']].append(m)

print(f"Week 17 has {len(grouped)} total matchups")

# Analyze structure
for matchup_id, teams in grouped.items():
    print(f"\nMatchup ID {matchup_id}:")
    for team in teams:
        print(f"  Roster {team['roster_id']}: {team.get('points', 0)} pts")
        # Check for bracket indicators
        print(f"    Fields: {list(team.keys())}")
```

---

### Expected Findings vs Current Design

| Design Assumption | If Sleeper Provides | If Sleeper Doesn't Provide |
|-------------------|---------------------|----------------------------|
| Week tracking needs dual values | Use Sleeper's fields directly | ✅ Implement `through_week` ourselves |
| Playoff bracket identification | Use `bracket_id` or similar | ✅ Derive from playoff bracket logic |
| Championship game identification | Use `matchup_type` field | ✅ Infer from playoff seeds in matchup |
| Consolation bracket structure | Use Sleeper's bracket data | ✅ Calculate based on seeding |
| Draft order calculation | Sleeper might provide | ✅ Calculate ourselves (likely) |

---

## Deliverables

After running analysis script, create:

### 1. API Capability Report

**File:** [`plans/SLEEPER_API_CAPABILITIES.md`](SLEEPER_API_CAPABILITIES.md)

**Contents:**
- What Sleeper provides out-of-the-box
- What needs to be calculated/derived
- Gaps between API and design requirements
- Recommended adjustments to design

### 2. Updated Design Documents

**Adjustments needed based on findings:**
- Update data source assumptions
- Revise implementation approach if Sleeper provides more than expected
- Simplify if Sleeper provides bracket tracking
- Add complexity if we need more derivation than expected

### 3. API Integration Specification

**File:** Updated [`plans/DRAFT_ORDER_SPECIFICATION.md`](DRAFT_ORDER_SPECIFICATION.md) Section 4.2

**Add:**
- Confirmed API endpoints with actual response structures
- Field mapping (Sleeper fields → our data model)
- Transformation logic needed
- Error handling for missing data

---

## Execution Plan

1. **Run Analysis Script** (Code mode)
   ```bash
   cd pipeline/scripts
   python analyze_sleeper_api.py <league_id>
   ```

2. **Review Output** (Architect mode)
   - Compare actual API response vs assumptions
   - Identify discrepancies
   - Note any pleasant surprises (Sleeper provides more than expected)
   - Note any gaps (Sleeper provides less than expected)

3. **Update Designs** (Architect mode)
   - Revise data requirement sections
   - Update implementation approaches
   - Adjust complexity estimates

4. **Validate Against Current State** (Code mode)
   - Verify we can fetch Week 16 results
   - Confirm we can identify Toilet Bowl participants
   - Test progressive determination with real data

---

## Success Criteria

Analysis complete when we can answer:

- ✅ **Week Tracking:** How do we know what week it is vs what data is available?
- ✅ **Bracket ID:** Can we programmatically identify Championship/3rd Place/Toilet Bowl games?
- ✅ **Result Availability:** Can we detect when a week's results are complete?
- ✅ **Playoff State:** Does Sleeper track any playoff state we can leverage?
- ✅ **Data Gaps:** What do we absolutely need to calculate ourselves?

Once answered, we can:
- Finalize implementation approach
- Write accurate API integration code
- Avoid over-engineering solutions Sleeper already provides
- Add necessary complexity only where Sleeper doesn't help

---

**Next Action:** Switch to Code mode and run the analysis script with your league ID.
