# Pipeline vs Lambda: Sleeper API Audit

## Complete Analysis of All Sleeper API Calls

Based on analysis of `update_dashboard.py` which runs 12 stages, here's every Sleeper API call made:

---

## Stage-by-Stage Sleeper API Analysis

### Stage 0: detect_current_week.py
**Sleeper API Calls:**
```
GET /v1/league/{league_id}
```
**Purpose:** Get current week number
**Lambda Status:** ✅ IMPLEMENTED (in `ingest_league_info`)

---

### Stage 1: stage1_fetch_trades.py  
**Sleeper API Calls:**
```
GET /v1/league/{league_id}           # League info
GET /v1/league/{league_id}/users     # All users
GET /v1/league/{league_id}/rosters   # All rosters
GET /v1/league/{league_id}/transactions/{week}  # For weeks 1-18
```
**Purpose:** Fetch all trade transactions
**Lambda Status:** ✅ IMPLEMENTED (in `ingest_trades`)

---

### Stage 2: stage2_extract_assets.py
**Sleeper API Calls:** NONE (processing only)
**Lambda Status:** ❌ NOT NEEDED (extraction logic, not data fetching)

---

### Stage 3: stage3_cache_values.py
**Sleeper API Calls:** NONE (calls DynastyProcess/KeepTradeCut instead)
**Lambda Status:** ❌ NOT YET IMPLEMENTED (value lookups)

---

### Stage 4: stage4_final.py
**Sleeper API Calls:** NONE (processing only)
**Lambda Status:** ❌ NOT NEEDED (calculation logic)

---

### Stage 5: stage5_waiver_wire.py
**Sleeper API Calls:**
```
GET /v1/league/{league_id}/transactions/{week}  # For all weeks
```
**Purpose:** Fetch waiver and free agent transactions
**Lambda Status:** ✅ IMPLEMENTED (in `ingest_waivers`)

---

### Stage 5a: fetch_player_stats.py
**Sleeper API Calls:**
```
GET /v1/league/{league_id}/rosters
GET /v1/stats/nfl/{season_type}/{season}/{week}
```
**Purpose:** Fetch NFL player stats for each week
**Lambda Status:** ❌ NOT YET IMPLEMENTED

---

### Stage 5b: fetch_lineup_data.py
**Sleeper API Calls:**
```
GET /v1/league/{league_id}/matchups/{week}
```
**Purpose:** Fetch weekly matchup data (lineups, scores)
**Lambda Status:** ❌ NOT YET IMPLEMENTED

---

### Stage 6: analyze_2026_pick_ownership.py
**Sleeper API Calls:** NONE (processing only)
**Lambda Status:** ❌ NOT NEEDED

---

### Stage 7: generate_playoff_bracket.py
**Sleeper API Calls:** NONE (processing only)
**Lambda Status:** ❌ NOT NEEDED

---

### Stage 7a: calculate_progressive_draft_order.py
**Sleeper API Calls:** NONE (processing only)
**Lambda Status:** ❌ NOT NEEDED

---

### Stage 8-9: generate_dashboard_json scripts
**Sleeper API Calls:** NONE (formatting only)
**Lambda Status:** ❌ NOT NEEDED

---

### Stage 10: fetch_standings.py
**Sleeper API Calls:**
```
GET /v1/league/{league_id}
GET /v1/league/{league_id}/rosters
GET /v1/league/{league_id}/users
```
**Purpose:** Fetch current standings
**Lambda Status:** ✅ IMPLEMENTED (in `ingest_standings`)

---

### Stage 11: simulate_playoff_scenarios.py
**Sleeper API Calls:** NONE (uses standings data, runs simulations)
**Lambda Status:** ❌ NOT NEEDED (computation, not data fetching)

---

### Stage 12: Final dashboard JSON generation
**Sleeper API Calls:** NONE (formatting only)
**Lambda Status:** ❌ NOT NEEDED

---

## Complete Sleeper API Inventory

### All Unique Sleeper API Endpoints Used:

| Endpoint | Purpose | Used By | Lambda Status |
|----------|---------|---------|---------------|
| `/v1/league/{id}` | League metadata, current week | Stages 0,1,10 | ✅ IMPLEMENTED |
| `/v1/league/{id}/users` | User profiles | Stages 1,10 | ✅ IMPLEMENTED |
| `/v1/league/{id}/rosters` | Team rosters, standings | Stages 1,5a,10 | ✅ IMPLEMENTED |
| `/v1/league/{id}/transactions/{week}` | Trades, waivers, FA | Stages 1,5 | ✅ IMPLEMENTED |
| `/v1/league/{id}/matchups/{week}` | Weekly matchups, lineups | Stage 5b | ❌ MISSING |
| `/v1/stats/nfl/{type}/{season}/{week}` | NFL player stats | Stage 5a | ❌ MISSING |

---

## Summary: Lambda Coverage

### ✅ IMPLEMENTED in Lambda (4 of 6):

1. **League Info** (`/v1/league/{id}`)
   - Fetches league metadata
   - Used for current week detection
   - ✅ In `ingest_league_info()`

2. **Users** (`/v1/league/{id}/users`)
   - Fetches all league members
   - Used for standings display
   - ✅ In `ingest_standings()`

3. **Rosters** (`/v1/league/{id}/rosters`)
   - Fetches team rosters and records
   - Used for standings
   - ✅ In `ingest_standings()`

4. **Transactions** (`/v1/league/{id}/transactions/{week}`)
   - Fetches trades, waivers, free agents
   - Loop through all weeks
   - ✅ In `ingest_trades()` and `ingest_waivers()`

### ❌ MISSING from Lambda (2 of 6):

5. **Matchups** (`/v1/league/{id}/matchups/{week}`)
   - **Purpose:** Weekly head-to-head matchups, lineups, scores
   - **Used By:** Stage 5b (fetch_lineup_data.py)
   - **Used For:** Waiver wire analysis (which players were started)
   - **Lambda:** NOT YET IMPLEMENTED

6. **NFL Stats** (`/v1/stats/nfl/{season_type}/{season}/{week}`)
   - **Purpose:** NFL-wide player statistics
   - **Used By:** Stage 5a (fetch_player_stats.py)
   - **Used For:** Performance analysis
   - **Lambda:** NOT YET IMPLEMENTED

---

## Impact Assessment

### What's Currently Working in Lambda:
- ✅ Trades (all weeks, all seasons)
- ✅ Waivers (all weeks, all seasons)
- ✅ Standings (current snapshot)
- ✅ League info (metadata)

### What's Missing:
- ❌ Weekly matchup data (needed for lineup analysis)
- ❌ NFL player stats (needed for performance metrics)

### Does This Matter?

**For basic dashboard:** NO - You have all core data
- Trades ✅
- Waivers ✅
- Standings ✅

**For advanced features:** YES - Missing data for:
- Lineup analysis
- "Which players were started" for waiver hit rate
- NFL-wide performance comparisons

---

## Should We Add Missing Endpoints?

### Option A: Add Now (30 min)
```python
def ingest_matchups(season_id, league_id):
    # Fetch weekly matchups
    # Store in DynamoDB
    pass

def ingest_player_stats(season, week):
    # Fetch NFL stats
    # Store in DynamoDB
    pass
```

### Option B: Add Later
- Your dashboard works without them
- Add when you need lineup/performance features
- Focus on getting basic real-time working first

---

## My Recommendation

**Your Lambda currently has 4 of 6 Sleeper endpoints - that's 67% coverage!**

**The 4 you have are the CORE ones:**
- Trades ✅
- Waivers ✅
- Standings ✅
- League info ✅

**The 2 missing are for ADVANCED features:**
- Matchups (for lineup analysis)
- NFL stats (for performance metrics)

**Recommend:** Keep current implementation, add matchups/stats later when needed!

---

## Want to Add Matchups & Stats Now?

I can add both endpoints (30 minutes total). Or proceed with connecting frontend to existing data?

Your call!