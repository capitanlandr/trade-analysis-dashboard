# Metrics: Stored vs Calculated On-Demand

## Your Question: Should metrics be pre-computed or calculated in real-time?

**Short Answer:** **Hybrid approach** - Store raw data, calculate simple metrics on-demand, cache complex metrics.

---

## The Two Approaches

### Approach 1: Pre-Computed Metrics (Current Pipeline)

**How it works:**
```
Pipeline runs → Calculates all metrics → Stores in JSON → Frontend reads
```

**Stored values:**
- Manager win rate: 0.73
- Total value gained: 5420
- Trade count: 15
- League average: 997

**Pros:**
- ✅ Fast reads (just return stored number)
- ✅ Consistent (everyone sees same calc)
- ✅ Simple frontend (just display)
- ✅ Low Lambda cost (no computation)

**Cons:**
- ❌ Stale until recalculated
- ❌ Can't filter dynamically (e.g., "show trades since October")
- ❌ Storage overhead (storing derived data)
- ❌ Need to recalc when anything changes

### Approach 2: Calculate On-Demand (Real-Time)

**How it works:**
```
Frontend requests → Lambda queries raw data → Calculates metrics → Returns
```

**Calculated each request:**
```python
def get_manager_stats(manager, trades):
    # Calculate on every API call
    total_trades = len([t for t in trades if manager in trade])
    wins = len([t for t in trades if t['winner'] == manager])
    win_rate = wins / total_trades if total_trades > 0 else 0
    total_value = sum(t['value_gained'] for t in trades if t['manager'] == manager)
    return {'win_rate': win_rate, 'total_value': total_value}
```

**Pros:**
- ✅ Always accurate (calculated from source)
- ✅ Dynamic filtering (e.g., "last 30 days" calculated on demand)
- ✅ Flexible (change calculations without reprocessing)
- ✅ No stale data

**Cons:**
- ❌ Slower (compute on every request)
- ❌ More Lambda cost (longer execution)
- ❌ Complex calculations slow (hit rates, Monte Carlo)
- ❌ Inconsistent if data changes mid-calculation

---

## The Right Answer: **Hybrid Approach**

### Store in DynamoDB (Source of Truth)
```
Trades (raw)
├─ tradeId
├─ date
├─ teamA, teamB
├─ assets (with values)
└─ season

Transactions (raw)
├─ transactionId
├─ type (waiver, free_agent)
├─ players
└─ manager
```

### Calculate Simple Metrics On-Demand
```python
# Fast calculations (< 10ms)
def get_manager_stats(manager, trades):
    manager_trades = [t for t in trades if manager in [t['teamA'], t['teamB']]]
    
    return {
        'trade_count': len(manager_trades),  # Simple count
        'total_value_gained': sum(t['margin'] for t in manager_trades),  # Simple sum
        'win_rate': calculate_wins(manager_trades) / len(manager_trades)  # Simple division
    }
```

### Pre-Compute & Cache Complex Metrics
```python
# Expensive calculations (stored in DynamoDB)
def calculate_waiver_hit_rate(transactions):
    # This is complex - analyze starter thresholds, usage patterns
    # Takes 500ms to compute
    # Store result in DynamoDB, recalc only when data changes
    pass

def run_playoff_monte_carlo(standings):
    # 10,000 simulations - takes 5 seconds
    # Store results, update weekly
    pass
```

---

## Recommended Hybrid Design

### DynamoDB Structure

#### 1. Raw Data (Always Store)
```
PK: SEASON#season_3   SK: TRADE#2025-11-18#123...
Data: {raw trade with assets and values}

PK: SEASON#season_3   SK: WAIVER#2025-11-20#456...
Data: {raw waiver transaction}

PK: SEASON#season_3   SK: STANDINGS#WEEK#14
Data: {wins, losses, points for 12 teams}
```

#### 2. Simple Aggregations (Calculate On-Demand)
**Don't store these, calculate from raw data:**
- Trade counts per manager
- Total value gained/lost
- Win rates
- League averages

**Why:** Fast to calculate (<10ms), always accurate

#### 3. Complex Metrics (Pre-Compute & Cache)
**Store these with TTL:**
```
PK: SEASON#season_3   SK: METRICS#WAIVER#CURRENT
Data: {hit_rates, churn, efficiency - pre-computed}
TTL: 3600 (expires after 1 hour)

PK: SEASON#season_3   SK: METRICS#PLAYOFFS#WEEK#14
Data: {Monte Carlo results - 10K simulations}
TTL: 86400 (expires after 24 hours)
```

**Why:** Expensive to calculate, rarely changes, cache with expiration

---

## Implementation Example

### Lambda Endpoint: GET /api/managers

```python
def handle_managers(season='season_3'):
    # 1. Fetch raw trades from DynamoDB
    trades = query_trades(season)  # 50ms
    
    # 2. Calculate simple metrics on-demand
    managers = {}
    for trade in trades:
        for manager in [trade['teamA'], trade['teamB']]:
            if manager not in managers:
                managers[manager] = {
                    'trades': [],
                    'value_gained': 0,
                    'wins': 0
                }
            
            managers[manager]['trades'].append(trade)
            if trade['winner'] == manager:
                managers[manager]['wins'] += 1
                managers[manager]['value_gained'] += trade['margin']
    
    # 3. Format results (calculated fresh!)
    results = []
    for manager, data in managers.items():
        results.append({
            'manager': manager,
            'trade_count': len(data['trades']),  # Calculated
            'win_rate': data['wins'] / len(data['trades']),  # Calculated
            'total_value': data['value_gained']  # Calculated
        })
    
    # Total compute time: ~10-20ms
    return results
```

### Lambda Endpoint: GET /api/waivers

```python
def handle_waivers(season='season_3'):
    # 1. Check cache first
    cached = dynamodb.get_item(
        PK=f"SEASON#{season}",
        SK="METRICS#WAIVER#CURRENT"
    )
    
    if cached and not_expired(cached):
        return cached['Data']  # Return cached (fast!)
    
    # 2. Cache miss or expired - recalculate
    transactions = query_waivers(season)
    
    # 3. Complex calculation (500ms)
    metrics = calculate_waiver_metrics(transactions)
    
    # 4. Store in cache
    dynamodb.put_item(Item={
        'PK': f"SEASON#{season}",
        'SK': "METRICS#WAIVER#CURRENT",
        'Data': metrics,
        'TTL': now() + 3600  # Expire in 1 hour
    })
    
    return metrics
```

---

## Metrics Classification

### Calculate On-Demand (Simple, Fast)
✅ **Trade counts** - `len(trades)` (instant)
✅ **Value sums** - `sum(values)` (instant)
✅ **Win rates** - `wins / total` (instant)
✅ **Averages** - `sum / count` (instant)
✅ **Current standings** - Already from API (instant)

**Store:** Raw trades only
**Compute:** When requested (~10-20ms)
**Result:** Always fresh, minimal storage

### Pre-Compute & Cache (Complex, Slow)
❌ **Waiver hit rates** - Threshold analysis, complex logic (500ms)
❌ **Playoff Monte Carlo** - 10,000 simulations (5 seconds!)
❌ **Efficiency scores** - Multi-factor weighted calculations (200ms)
❌ **Timing analysis** - Statistical analysis over time (300ms)

**Store:** Pre-computed results with TTL
**Recalc:** Hourly or when data changes
**Result:** Fast reads, acceptable staleness (1 hour)

---

## My Recommendation

### The Optimal Pattern

**Tier 1: Store Raw (Source of Truth)**
```
DynamoDB stores:
- Raw trades (with all details)
- Raw waiver transactions
- Raw standings per week
```

**Tier 2: Calculate Simple (On-Demand)**
```
API calculates when requested:
- Manager trade counts
- Value totals
- Win percentages
- League averages
- Current rankings
```

**Tier 3: Cache Complex (Pre-Compute with TTL)**
```
DynamoDB caches (1 hour expiry):
- Waiver wire hit rates
- Efficiency scores
- Timing analysis

DynamoDB caches (24 hour expiry):
- Playoff Monte Carlo
- Draft order projections
```

**Why this works:**
- ✅ Fast responses (<100ms total)
- ✅ Always fresh for simple metrics
- ✅ Acceptable staleness for complex (1 hour)
- ✅ Low cost (minimal recomputation)
- ✅ Flexible (can change calculations easily)

---

## Performance Comparison

### All Pre-Computed (Current)
```
Load dashboard → Read JSON → Done
Time: 50ms
Freshness: Up to 24 hours old
Cost: $0.00
```

### All On-Demand (Pure Calculation)
```
Load dashboard → Query DynamoDB → Calculate ALL metrics → Return
Time: 500-5000ms (slow!)
Freshness: Real-time
Cost: Higher (more Lambda time)
```

### Hybrid (Recommended)
```
Load dashboard → Query DynamoDB → Calculate simple → Return cached complex
Time: 100-150ms
Freshness: Simple = real-time, Complex = 1 hour old
Cost: $0.00 (still free tier)
```

---

## Implementation Strategy

### Phase 1: Store Raw + Calculate Simple
```python
# DynamoDB stores ONLY:
- Raw trades
- Raw transactions
- Raw standings

# Lambda calculates EVERY request:
- Trade counts
- Value sums
- Win rates
- All "simple math"
```

**Benefit:** Start simple, test performance

### Phase 2: Add Caching for Complex
```python
# Lambda checks cache first:
if cached_waiver_metrics and age < 1hour:
    return cached
else:
    calculate_waiver_metrics()  # Expensive
    store_in_dynamodb()
    return fresh_calculation
```

**Benefit:** Optimize only what's slow

---

## My Professional Opinion

**Your instinct is good!** Calculating on-demand from raw data is:
- ✅ More flexible
- ✅ Always accurate
- ✅ Easier to modify calculations
- ✅ Less storage

**But:** Not everything should be calculated on-demand.

**The Rule:**
- **O(n) operations** where n < 100 → Calculate on-demand (your trades, managers)
- **O(n²) or expensive** → Pre-compute and cache (Monte Carlo, complex metrics)

**For your dashboard:**
- ✅ Trade counts, win rates, value sums → Calculate on-demand
- ✅ Current standings → Direct from API
- ✅ Waiver hit rates → **Cache** (complex threshold logic)
- ✅ Playoff scenarios → **Cache** (10K simulations!)

---

## Recommended Final Architecture

### DynamoDB Schema (Revised)

**Store ONLY:**
1. Raw trades (with values)
2. Raw transactions (waivers, free agents)
3. Raw standings (by week)
4. **Cached metrics** (complex only, with TTL)

**Calculate On-Demand:**
1. Manager statistics (simple aggregations)
2. Trade summaries (counts, averages)
3. League-wide stats (totals, averages)

**Pre-Compute & Cache (1-24 hour TTL):**
1. Waiver wire metrics (hit rates, efficiency)
2. Playoff Monte Carlo (10K simulations)
3. Historical trend analysis

---

## Decision Matrix

| Metric | Complexity | Store or Calculate? | Reasoning |
|--------|-----------|---------------------|-----------|
| Trade count | O(n) | **Calculate** | Fast, always fresh |
| Win rate | O(n) | **Calculate** | Simple division |
| Value sums | O(n) | **Calculate** | Fast aggregation |
| Waiver hit rate | O(n²) + logic | **Cache** | Complex thresholds |
| Monte Carlo | O(n × 10K) | **Cache** | Very expensive |
| Current standings | External API | **Pass-through** | Already real-time |

---

**Should we proceed with this hybrid approach?** Store raw data, calculate simple metrics, cache complex ones?