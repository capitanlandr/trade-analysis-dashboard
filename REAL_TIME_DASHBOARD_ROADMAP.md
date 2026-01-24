# Roadmap: Static → Fully Real-Time Dashboard

## Your Vision (Perfectly Clear!)

### Current State (Static)
```
Website loads → Static JSON files → Shows yesterday's data
```
**Updates:** Once daily at 9 AM EST

### Target State (Real-Time)
```
User visits website → Calls Lambda API → Lambda fetches Sleeper → Shows NOW data
```
**Updates:** Every time someone loads the page!

---

## The Incremental Path Forward

### Phase 1: Match Pipeline's Raw Fetch ✅ NEXT STEP

**Goal:** Lambda fetches exact same RAW data as pipeline stage 1

**What to add to Lambda:**
```python
def handle_trades():
    # Get current week
    league = fetch_sleeper_api(f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}")
    current_week = league['settings']['leg']
    
    # Loop through ALL weeks (like pipeline!)
    all_trades = []
    for week in range(1, current_week + 6):
        transactions = fetch_sleeper_api(f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}/transactions/{week}")
        trades = [t for t in transactions if t.get('type') == 'trade']
        all_trades.extend(trades)
    
    return all_trades  # Same raw data as pipeline stage 1!
```

**Time:** 15 minutes
**Result:** Lambda returns ALL trades (not just week 1)

---

### Phase 2: Add Value Calculations (Like Pipeline Stage 3)

**Goal:** Lambda calls KeepTradeCut API for player values

**What to add:**
```python
def get_player_values(player_ids):
    """Call KeepTradeCut API for dynasty values"""
    # Cache results in DynamoDB to avoid repeated API calls
    pass

def handle_trades():
    # Fetch raw trades (Phase 1)
    all_trades = fetch_all_trades()
    
    # Extract player IDs
    player_ids = extract_player_ids(all_trades)
    
    # Get values from KeepTradeCut
    values = get_player_values(player_ids)
    
    # Calculate trade winners/losers
    analyzed_trades = analyze_trades(all_trades, values)
    
    return analyzed_trades  # Now with VALUE ANALYSIS!
```

**Time:** 1-2 hours
**Challenge:** Need to handle KeepTradeCut API (external)
**Result:** Lambda returns trades with value analysis

---

### Phase 3: Add Caching Layer

**Goal:** Don't call external APIs every time (too slow + expensive)

**Options:**

**Option A: DynamoDB (AWS Database)**
```python
# Cache KeepTradeCut values in DynamoDB
def get_player_values(player_ids):
    # Check cache first
    cached = dynamodb.get_items(player_ids)
    
    # Only fetch missing values from KeepTradeCut
    missing = [p for p in player_ids if p not in cached]
    if missing:
        new_values = call_keep_trade_cut(missing)
        dynamodb.save(new_values)
    
    return cached + new_values
```

**Option B: Lambda Layer (In-Memory Cache)**
```python
# Store values in Lambda /tmp directory (survives ~15 min)
CACHE_FILE = '/tmp/player_values.json'

def get_cached_values():
    if os.path.exists(CACHE_FILE):
        age = time.time() - os.path.getmtime(CACHE_FILE)
        if age < 3600:  # 1 hour cache
            return json.load(open(CACHE_FILE))
    return {}
```

**Time:** 1-2 hours
**Result:** Fast responses (cached data) + occasional external API calls

---

### Phase 4: Connect Frontend to Lambda

**Goal:** React calls Lambda instead of static JSON

**Update frontend:**
```typescript
// dashboard/frontend/src/services/api.ts
const API_BASE = 'https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod';

export const fetchTrades = async () => {
  const response = await fetch(`${API_BASE}/api/trades`);
  return response.json();
};

export const fetchStandings = async () => {
  const response = await fetch(`${API_BASE}/api/standings`);
  return response.json();
};
```

**Time:** 30 minutes
**Result:** Dashboard shows real-time data on every load!

---

### Phase 5: Add Playoff Simulations to Lambda

**Challenge:** Monte Carlo takes time (10,000 simulations)

**Solution Options:**

**Option A: Pre-compute and cache**
```python
# Lambda triggered by schedule (daily)
# Runs simulations, stores in DynamoDB
# Frontend Lambda just returns cached results
```

**Option B: Async processing**
```python
# Frontend calls /api/playoffs
# Lambda checks cache
# If stale, triggers async SQS job to recompute
# Returns cached data immediately
```

**Time:** 2-3 hours
**Result:** Real-time playoffs with cached simulations

---

## The Complete Real-Time Stack (End Goal)

```
User loads page
    ↓
React Frontend (S3 + CloudFront)
    ↓ (API calls)
API Gateway
    ↓ (triggers)
Lambda Function
    ├─→ Check DynamoDB cache
    ├─→ Call Sleeper API if needed
    ├─→ Call KeepTradeCut if needed
    ├─→ Calculate analysis
    └─→ Return JSON
    ↓
Frontend displays REAL-TIME data
```

**Updates:** Every page load!
**Latency:** 200-500ms per request
**Cost:** ~$0.50-2.00/month (still cheap!)

---

## Incremental Implementation Plan

### Week 1: Raw Fetch (15 min) ← START HERE
- Update Lambda to fetch ALL weeks (not just week 1)
- Match pipeline's stage 1 raw fetch exactly
- Test: Lambda returns complete trade history

### Week 2: Add Value Calculations (2-3 hours)
- Port pipeline stage 3 logic to Lambda
- Call KeepTradeCut API
- Calculate trade values

### Week 3: Add Caching (2-3 hours)
- Set up DynamoDB table
- Cache player values
- Optimize performance

### Week 4: Frontend Integration (1 hour)
- Update React to call Lambda
- Remove static JSON dependency
- Test real-time updates

### Week 5: Add Complex Features (3-4 hours)
- Playoff simulations (with caching)
- Historical analysis
- Advanced metrics

---

## Current Status

**Lambda Fetch Level:**
- ✅ Can call Sleeper API
- ❌ Only fetches week 1 (not all weeks)
- ❌ No value calculations
- ❌ No processing

**To match pipeline stage 1 raw fetch:**
- Need to add week looping
- Need to fetch ALL trades (not just week 1)

---

## Ready to Start?

**Let's begin with Phase 1:**

Update Lambda to fetch ALL weeks of trades (matching pipeline's raw fetch).

I'll modify the `handle_trades()` function to loop through weeks like your pipeline does.

Want me to make that change now?