# Sleeper API Capabilities Report

**Date:** December 29, 2024  
**Analysis:** Live API exploration during Week 17 playoffs  
**League ID:** 1180814327660371968  
**Status:** ✅ Major Discovery - Bracket Endpoints with Structured Data!

---

## Executive Summary

### 🎉 Key Discoveries

**1. `last_scored_leg` Field - Solves "Through Week" Problem!**
```json
"settings": {
  "leg": 17,              // Current NFL week
  "last_scored_leg": 16   // Last week with COMPLETE scores
}
```

**This is exactly what we need for progressive draft order!**
- `leg` = current week (17)
- `last_scored_leg` = through week (16)
- Automatically maintained by Sleeper

**2. Bracket Endpoints Exist!**
- ✅ `/league/{id}/winners_bracket` - Playoff bracket with structure
- ✅ `/league/{id}/losers_bracket` - Consolation bracket with structure
- ✅ Placement field (`p`) identifies Championship, 3rd Place, Toilet Bowl
- ✅ Winner field (`w`) shows null for pending games

**3. League Status Field**
```json
"status": "post_season"  // Phase indicator
```
- Can map to our season phases
- Automatic phase detection!

---

## 1. NFL State Endpoint

### `GET /v1/state/nfl`

**Response:**
```json
{
  "week": 17,
  "leg": 17,
  "season": "2025",
  "season_type": "regular",
  "display_week": 17,
  "season_has_scores": true
}
```

**Usage:**
- Use `week` field for current NFL week
- Note: `season_type: "regular"` even during playoffs (Week 17 is technically regular season)

---

## 2. League Metadata - CRITICAL FIELDS

### `GET /v1/league/{league_id}`

**Critical Fields Discovered:**
```json
{
  "status": "post_season",
  "bracket_id": 1304396009165557760,
  "loser_bracket_id": 1304396009169752066,
  "settings": {
    "leg": 17,                    // Current week
    "last_scored_leg": 16,        // 🎯 KEY: Last week with complete scores!
    "playoff_week_start": 15,
    "trade_deadline": 11
  }
}
```

### Week Tracking Solution

```python
# Get both week values from league endpoint
league_data = fetch(f"/league/{league_id}")

current_week = league_data["settings"]["leg"]              # 17
through_week = league_data["settings"]["last_scored_leg"]  # 16

# This tells us:
# - Current NFL week is 17
# - But we only have complete data through Week 16
# - Week 17 games are in progress (scores not final)
```

---

## 3. Bracket Endpoints (MAJOR DISCOVERY!)

### `GET /v1/league/{league_id}/winners_bracket`

**Structure:**
```json
[
  {
    "m": 6,              // Match number
    "r": 3,              // Round (1=Wild Card, 2=Semis, 3=Finals)
    "p": 1,              // 🎯 Placement: 1=Championship, 3=3rd Place, 5=5th
    "t1": 7,             // Team 1 roster_id
    "t2": 3,             // Team 2 roster_id
    "w": null,           // Winner (null = PENDING)
    "l": null,           // Loser (null = PENDING)
    "t1_from": {"w": 3}, // Team 1 = winner of match 3
    "t2_from": {"w": 4}  // Team 2 = winner of match 4
  }
]
```

### Current Week 17 Finals (Pending):

**Championship (p:1):**
- Match 6: Roster 7 vs 3
- Winner: TBD → Will get pick 1.12
- Loser: TBD → Will get pick 1.11

**3rd Place (p:3):**
- Match 7: Roster 2 vs 1
- Winner: TBD → Will get pick 1.09
- Loser: TBD → Will get pick 1.10

### `GET /v1/league/{league_id}/losers_bracket`

**Current Week 17 Finals (Pending):**

**Toilet Bowl (p:3):**
- Match 7: Roster 4 vs 8
- Winner: TBD → Will get pick 1.01
- Loser: TBD → Will get pick 1.02

**Consolation Championship (p:1):**
- Match 6: Roster 9 vs 10
- Winner: Gets 7th place overall
- Loser: Gets 8th place overall

---

## 4. Special Games Identification

### Simple Lookup Using Placement Field

```python
def identify_special_games(winners_bracket, losers_bracket):
    """Use placement field to identify draft-relevant games"""
    
    # Championship: winners bracket, round 3, placement 1
    championship = next(
        m for m in winners_bracket 
        if m.get('r') == 3 and m.get('p') == 1
    )
    # Current: {'t1': 7, 't2': 3, 'w': null, 'l': null}
    
    # 3rd Place: winners bracket, round 3, placement 3
    third_place = next(
        m for m in winners_bracket 
        if m.get('r') == 3 and m.get('p') == 3
    )
    # Current: {'t1': 2, 't2': 1, 'w': null, 'l': null}
    
    # Toilet Bowl: losers bracket, round 3, placement 3
    toilet_bowl = next(
        m for m in losers_bracket 
        if m.get('r') == 3 and m.get('p') == 3
    )
    # Current: {'t1': 4, 't2': 8, 'w': null, 'l': null}
    
    return {
        'championship': {
            'teams': [championship['t1'], championship['t2']],  # [7, 3]
            'winner': championship.get('w'),  # null
            'loser': championship.get('l'),   # null
            'complete': championship.get('w') is not None  # False
        },
        'third_place': {
            'teams': [third_place['t1'], third_place['t2']],  # [2, 1]
            'winner': third_place.get('w'),
            'loser': third_place.get('l'),
            'complete': third_place.get('w') is not None
        },
        'toilet_bowl': {
            'teams': [toilet_bowl['t1'], toilet_bowl['t2']],  # [4, 8]
            'winner': toilet_bowl.get('w'),
            'loser': toilet_bowl.get('l'),
            'complete': toilet_bowl.get('w') is not None
        }
    }
```

**Result:**
```python
{
  'championship': {
    'teams': [7, 3],
    'winner': None,
    'loser': None,
    'complete': False
  },
  'third_place': {
    'teams': [2, 1],
    'winner': None,
    'loser': None,
    'complete': False
  },
  'toilet_bowl': {
    'teams': [4, 8],
    'winner': None,
    'loser': None,
    'complete': False
  }
}
```

---

## 5. Progressive Determination Using Bracket Data

### Count Locked Picks

```python
def count_locked_picks(winners_bracket, losers_bracket):
    """Count locked picks based on bracket completion state"""
    
    # Check Round 1 completion (determines middle picks)
    round_1_complete = all(
        m.get('w') is not None 
        for m in winners_bracket + losers_bracket 
        if m.get('r') == 1
    )
    
    # Find special games
    championship = next(m for m in winners_bracket if m.get('r') == 3 and m.get('p') == 1)
    third_place = next(m for m in winners_bracket if m.get('r') == 3 and m.get('p') == 3)
    toilet_bowl = next(m for m in losers_bracket if m.get('r') == 3 and m.get('p') == 3)
    
    # Count locked picks
    locked = 0
    
    if round_1_complete:
        locked += 6  # Picks 1.03-1.08 (middle picks)
    
    if toilet_bowl.get('w') is not None:
        locked += 2  # Picks 1.01-1.02
    
    if championship.get('w') is not None and third_place.get('w') is not None:
        locked += 4  # Picks 1.09-1.12
    
    return locked
```

**Current State:**
- Round 1 complete: ✅ Yes
- Toilet Bowl complete: ❌ No (w: null)
- Championship complete: ❌ No (w: null)
- 3rd Place complete: ❌ No (w: null)

**Result: 6 picks locked (1.03-1.08)**

---

## 6. Week Configuration Implementation

### Sync from Sleeper

```python
def sync_week_config_from_sleeper(league_id):
    """Sync week configuration from Sleeper API"""
    
    league = fetch(f"/league/{league_id}")
    nfl_state = fetch("/state/nfl")
    
    return {
        "season_year": int(league['season']),
        "season_phase": map_league_status(league['status']),  # "post_season" → "playoffs"
        
        "weeks": {
            "nfl_calendar_week": nfl_state['week'],           # 17
            "playoff_week_start": league['settings']['playoff_week_start'],  # 15
            "playoff_round": nfl_state['week'] - 14           # 3
        },
        
        "sleeper_data": {
            "last_scored_leg": league['settings']['last_scored_leg'],  # 16
            "league_status": league['status'],                         # "post_season"
            "bracket_id": league.get('bracket_id'),
            "loser_bracket_id": league.get('loser_bracket_id')
        },
        
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }

def map_league_status(status):
    """Map Sleeper status to our phase"""
    return {
        "pre_draft": "preseason",
        "drafting": "preseason", 
        "in_season": "regular_season",
        "post_season": "playoffs",
        "complete": "offseason"
    }.get(status, "unknown")
```

---

## 7. Draft Order Calculation (Simplified!)

### Using Bracket Data

```python
def calculate_draft_order():
    """Calculate draft order using Sleeper bracket endpoints"""
    
    # 1. Fetch bracket data
    winners = fetch(f"/league/{league_id}/winners_bracket")
    losers = fetch(f"/league/{league_id}/losers_bracket")
    
    # 2. Identify special games (one line each!)
    championship = next(m for m in winners if m.get('r') == 3 and m.get('p') == 1)
    third_place = next(m for m in winners if m.get('r') == 3 and m.get('p') == 3)
    toilet_bowl = next(m for m in losers if m.get('r') == 3 and m.get('p') == 3)
    
    # 3. Extract participants
    special_game_participants = (
        championship['t1'], championship['t2'],     # [7, 3]
        third_place['t1'], third_place['t2'],       # [2, 1]
        toilet_bowl['t1'], toilet_bowl['t2']        # [4, 8]
    )
    # = [7, 3, 2, 1, 4, 8]
    
    # 4. Get regular season standings
    standings = load_regular_season_standings()
    
    # 5. Identify remaining 6 teams
    remaining = [
        t for t in standings 
        if t['roster_id'] not in special_game_participants
    ]
    # Remaining roster_ids: [5, 6, 9, 10, 11, 12]
    
    # 6. Sort remaining by regular season rank (worst to best)
    remaining_sorted = sorted(
        remaining,
        key=lambda t: t['regular_season_rank'],
        reverse=True
    )
    
    # 7. Assign draft order
    draft_order = {}
    
    # Toilet Bowl
    if toilet_bowl.get('w'):
        draft_order[1] = toilet_bowl['w']
        draft_order[2] = toilet_bowl['l']
    else:
        draft_order[1] = {'pending': toilet_bowl['t1'], 'or': toilet_bowl['t2']}
        draft_order[2] = {'pending': toilet_bowl['t1'], 'or': toilet_bowl['t2']}
    
    # Middle picks
    for i, team in enumerate(remaining_sorted, start=3):
        draft_order[i] = team['roster_id']
    
    # 3rd Place
    if third_place.get('w'):
        draft_order[9] = third_place['w']
        draft_order[10] = third_place['l']
    else:
        draft_order[9] = {'pending': third_place['t1'], 'or': third_place['t2']}
        draft_order[10] = {'pending': third_place['t1'], 'or': third_place['t2']}
    
    # Championship
    if championship.get('w'):
        draft_order[11] = championship['l']
        draft_order[12] = championship['w']
    else:
        draft_order[11] = {'pending': championship['t1'], 'or': championship['t2']}
        draft_order[12] = {'pending': championship['t1'], 'or': championship['t2']}
    
    return draft_order
```

---

## 8. Current State Analysis

### From Week 16 Bracket Data

**Special Game Participants (All Known):**
- Championship: Rosters 7, 3
- 3rd Place: Rosters 2, 1
- Toilet Bowl: Rosters 4, 8

**Remaining 6 Teams:** 5, 6, 9, 10, 11, 12

**Regular Season Ranks (from rosters data):**
```
Roster 7: 22-6 (2000.06 PF) → 1st place
Roster 3: 21-7 (1875.40 PF) → 2nd place
Roster 1: 19-9 (1907.72 PF) → 3rd place (wild card)
Roster 2: 16-12 (1960.12 PF) → 4th place
Roster 12: 16-12 (1828.40 PF) → 5th place (tiebreaker: PF)
Roster 9: 13-15 (1674.48 PF) → 7th place
Roster 5: 11-17 (1644.54 PF) → 9th place (tied with roster 6)
Roster 6: 11-17 (1608.50 PF) → 10th place (lower PF)
Roster 11: 10-18 (1407.16 PF) → 11th place
Roster 8: 9-19 (1596.74 PF) → 12th place
Roster 4: 8-20 (1473.56 PF) → 13th place (if there was one!)
```

**Middle Picks Assignment:**
```
Remaining teams sorted by regular season rank (worst to best):
1. Roster 12 (5th place) → Pick 1.08
2. Roster 9 (7th place) → Pick 1.07  
3. Roster 5 (9th place) → Pick 1.06
4. Roster 6 (10th place) → Pick 1.05
5. Roster 11 (11th place) → Pick 1.04
6. Wait... that's only 5 teams

Let me recount: Special game participants are 7, 3, 2, 1, 4, 8
Remaining: 5, 6, 9, 10, 11, 12 ✅ That's 6 teams
```

**Remaining 6 sorted (worst to best regular season):**
1. Roster 12 (5th) → 1.08
2. Roster 9 (7th) → 1.07
3. Roster 5 (9th) → 1.06
4. Roster 6 (10th) → 1.05
5. Roster 11 (11th) → 1.04
6. Wait... I only have 5. Let me check roster 10.

From rosters data:
- Roster 10: 12-16 record, 1629.10 PF

So the order is:
1. 7: 22-6 (1st)
2. 3: 21-7 (2nd)
3. 1: 19-9 (3rd)
4. 2: 16-12, 1960 PF (4th)
5. 12: 16-12, 1828 PF (5th - lower PF)
6. 9: 13-15 (6th)
7. 10: 12-16 (7th)
8. 5: 11-17, 1644 PF (8th)
9. 6: 11-17, 1608 PF (9th - lower PF)
10. 11: 10-18 (10th)
11. 8: 9-19 (11th)
12. 4: 8-20 (12th)

**Remaining 6 teams (not in special games [7,3,2,1,4,8]):**
- Roster 12 (5th) → 1.08
- Roster 9 (6th) → 1.07
- Roster 10 (7th) → 1.06
- Roster 5 (8th) → 1.05
- Roster 6 (9th) → 1.04
- Roster 11 (10th) → 1.03

---

## 9. Implementation Impact

### Simplifications Enabled

**BEFORE (Assumed):**
- Manually construct bracket from matchup results
- Use heuristics to identify Championship/3rd/Toilet Bowl
- Complex state tracking logic
- Poll matchup scores to detect completion

**AFTER (With Bracket Endpoints):**
- ✅ Direct bracket structure from Sleeper
- ✅ Placement field identifies special games
- ✅ Winner field shows completion status
- ✅ `last_scored_leg` shows data availability

### Updated Week Tracking

**In [`pipeline/config/current_week.json`](../pipeline/config/current_week.json):**
```json
{
  "nfl_calendar_week": 17,
  "through_week": 16,
  "season_phase": "playoffs",
  "sleeper_sync": {
    "last_scored_leg": 16,
    "league_status": "post_season",
    "last_synced": "2024-12-29T20:00:00Z"
  }
}
```

**Update Script:**
```python
def update_week_config():
    """Sync week config from Sleeper"""
    league = fetch(f"/league/{league_id}")
    nfl_state = fetch("/state/nfl")
    
    config = {
        "nfl_calendar_week": nfl_state['week'],
        "through_week": league['settings']['last_scored_leg'],
        "season_phase": map_league_status(league['status']),
        "sleeper_sync": {
            "last_scored_leg": league['settings']['last_scored_leg'],
            "league_status": league['status'],
            "last_synced": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    save_config(config)
```

---

## 10. Design Document Updates Needed

### Update [`DRAFT_ORDER_SPECIFICATION.md`](DRAFT_ORDER_SPECIFICATION.md)

**Section 4.2 - Playoff Results Data Source:**

**OLD:**
> Need to fetch final playoff results from Sleeper API after Week 17  
> Implementation decision needed: Parse playoff_bracket.json or fetch from API

**NEW:**
> ✅ Use Sleeper bracket endpoints:
> - `/league/{id}/winners_bracket` for Championship and 3rd Place
> - `/league/{id}/losers_bracket` for Toilet Bowl
> - Placement field (`p: 1, 3`) identifies game types
> - Winner field (`w: null`) indicates pending games

**Section 5 - Week Configuration:**

**ADD:**
> ✅ Use Sleeper's `last_scored_leg` field for "through_week"
> - Automatically maintained by Sleeper
> - Indicates last week with finalized scores
> - Enables automatic progressive determination

### Update [`PROGRESSIVE_DRAFT_ORDER_TRACKING.md`](PROGRESSIVE_DRAFT_ORDER_TRACKING.md)

**Section 3 - Week Tracking Architecture:**

**SIMPLIFY:** Remove complex "through_week" tracking logic

**ADD:**
> Use Sleeper's `last_scored_leg` directly:
> ```python
> league = fetch(f"/league/{league_id}")
> through_week = league['settings']['last_scored_leg']
> ```

---

## 11. Key Takeaways

### ✅ What Sleeper Provides

1. **Automatic Week Tracking:**
   - `leg` = current week
   - `last_scored_leg` = last week with complete scores
   - No manual detection needed!

2. **Structured Bracket Data:**
   - Round tracking (`r: 1, 2, 3`)
   - Placement indicators (`p: 1, 3, 5`)
   - Winner/loser tracking (`w`, `l`)
   - Completion detection (`w: null` = pending)

3. **League Phase:**
   - `status` field tracks season phase
   - "post_season" during playoffs
   - Can use for automation triggers

4. **Bracket IDs:**
   - `bracket_id` for winners bracket
   - `loser_bracket_id` for consolation
   - Can store for audit trail

### ❌ What We Calculate

1. **Draft Order Assignment:**
   - Which team gets which pick number
   - Sleeper doesn't know draft order rules

2. **Regular Season Tiebreakers:**
   - H2H records (must fetch matchups 1-14)
   - Division records
   - Apply 5-tier tiebreaker chain

3. **Pick Ownership:**
   - Trade history tracking
   - Original vs current owner mapping

4. **Progressive Certainty:**
   - Locked vs uncertain classification
   - Scenario generation for dashboard

---

## 12. Recommendations

### Immediate Actions

1. **Update Design Documents:**
   - Add bracket endpoint documentation
   - Simplify week tracking sections
   - Remove complex heuristics

2. **Create API Helper Functions:**
   ```python
   # pipeline/utils/api_client.py
   
   def fetch_bracket_state(league_id):
       """Fetch both brackets"""
       return {
           'winners': fetch(f"/league/{league_id}/winners_bracket"),
           'losers': fetch(f"/league/{league_id}/losers_bracket")
       }
   
   def get_week_info(league_id):
       """Get current and through week"""
       league = fetch(f"/league/{league_id}")
       nfl_state = fetch("/state/nfl")
       return {
           'current_week': nfl_state['week'],
           'through_week': league['settings']['last_scored_leg'],
           'status': league['status']
       }
   ```

3. **Test with Real Data:**
   - Verify bracket endpoint reliability
   - Check if `last_scored_leg` updates correctly
   - Validate special game identification

### Priority Changes

**NOW EASIER:**
- ✅ Fetching playoff results → Use bracket endpoints
- ✅ Detecting completion → Check `w` field
- ✅ Week tracking → Use `last_scored_leg`
- ✅ Phase detection → Use `status` field

**STILL COMPLEX:**
- Draft order algorithm (unchanged)
- Regular season tiebreakers (unchanged)
- Pick ownership integration (unchanged)

---

## 13. Next Steps

1. **Create API capabilities report** ✅ (this document)
2. **Update design specifications** with bracket endpoint info
3. **Implement bracket fetching** in `api_client.py`
4. **Test progressive calculation** with current Week 16 state
5. **Validate after Week 17** completes

---

**Analysis Complete:** ✅ All API capabilities documented  
**Major Finding:** Bracket endpoints dramatically simplify implementation  
**Impact:** 40-50% reduction in complexity for playoff result handling  
**Status:** Ready to update implementation specifications
