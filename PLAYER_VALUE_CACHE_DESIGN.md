# Player Value Cache: CSV → DynamoDB Migration

## Your Question: Replace CSV cache with DynamoDB?

**Answer: YES! DynamoDB is perfect for this.**

---

## Current Pipeline Cache (CSV)

### How It Works Now

**File:** `pipeline/asset_values_cache.csv`

**Structure:**
```csv
player_id,player_name,value,last_updated
4018,Saquon Barkley,3813,2026-01-20T10:15:00Z
138,Justin Jefferson,8301,2026-01-20T10:15:00Z
...
```

**Pipeline Stage 3 Logic:**
```python
def cache_values(player_ids):
    # 1. Load CSV cache
    cache = pd.read_csv('asset_values_cache.csv')
    
    # 2. Check which players need updates
    missing = [p for p in player_ids if p not in cache or is_stale(cache[p])]
    
    # 3. Call KeepTradeCut for missing/stale players
    new_values = call_keep_trade_cut(missing)
    
    # 4. Update CSV file
    cache.update(new_values)
    cache.to_csv('asset_values_cache.csv')
    
    # 5. Return all values
    return cache
```

**Problems with CSV:**
- ❌ File locking issues (concurrent access)
- ❌ Not accessible from Lambda (unless uploaded)
- ❌ Slow for large datasets
- ❌ No TTL or automatic expiration
- ❌ Hard to query (must load entire file)

---

## DynamoDB Replacement (Better!)

### Schema Design

**Table:** `fantasy-dashboard-data` (same single table!)

**Key Pattern:**
```
PK: CACHE#PLAYER_VALUE
SK: PLAYER#{player_id}
```

**Item Structure:**
```json
{
  "PK": "CACHE#PLAYER_VALUE",
  "SK": "PLAYER#4018",
  "PlayerID": "4018",
  "PlayerName": "Saquon Barkley",
  "Value": 3813,
  "Source": "KeepTradeCut",
  "LastUpdated": "2026-01-20T10:15:00Z",
  "TTL": 1737468900,  // Auto-delete after 7 days
  "GSI1PK": "PLAYER_VALUE",
  "GSI1SK": "2026-01-20T10:15:00Z"
}
```

---

## Lambda Implementation

### Get Player Value (With Auto-Cache)

```python
def get_player_value(player_id: str, max_age_hours: int = 24) -> dict:
    """
    Get player value from DynamoDB cache or fetch from KeepTradeCut
    
    Args:
        player_id: Sleeper player ID
        max_age_hours: Maximum cache age before refresh
    
    Returns:
        {player_id, player_name, value, last_updated}
    """
    
    # 1. Check DynamoDB cache
    try:
        response = dynamodb.get_item(
            Key={
                'PK': 'CACHE#PLAYER_VALUE',
                'SK': f'PLAYER#{player_id}'
            }
        )
        
        if 'Item' in response:
            cached = response['Item']
            cache_age = now() - parse_timestamp(cached['LastUpdated'])
            
            # Return if fresh enough
            if cache_age < timedelta(hours=max_age_hours):
                print(f"Cache HIT for player {player_id} (age: {cache_age})")
                return cached
            else:
                print(f"Cache EXPIRED for player {player_id}")
        else:
            print(f"Cache MISS for player {player_id}")
    
    except Exception as e:
        print(f"Cache read error: {e}")
    
    # 2. Cache miss or expired - fetch from KeepTradeCut
    try:
        value_data = call_keep_trade_cut_api(player_id)
        
        # 3. Store in DynamoDB cache
        item = {
            'PK': 'CACHE#PLAYER_VALUE',
            'SK': f'PLAYER#{player_id}',
            'PlayerID': player_id,
            'PlayerName': value_data['player_name'],
            'Value': value_data['value'],
            'Source': 'KeepTradeCut',
            'LastUpdated': now().isoformat(),
            'TTL': int(now().timestamp()) + (7 * 24 * 3600),  # 7 days
            'GSI1PK': 'PLAYER_VALUE',
            'GSI1SK': now().isoformat()
        }
        
        dynamodb.put_item(Item=item)
        print(f"Cached value for player {player_id}: {value_data['value']}")
        
        return item
        
    except Exception as e:
        print(f"Failed to fetch value for player {player_id}: {e}")
        # Return stale cache or default value
        return cached if cached else {'PlayerID': player_id, 'Value': 0}
```

### Batch Get Values (Efficient)

```python
def get_player_values_batch(player_ids: List[str]) -> Dict[str, dict]:
    """
    Get multiple player values efficiently
    Uses DynamoDB BatchGetItem for up to 100 players at once
    """
    
    # 1. Batch query DynamoDB (1 request for 100 players!)
    keys = [
        {'PK': 'CACHE#PLAYER_VALUE', 'SK': f'PLAYER#{pid}'}
        for pid in player_ids
    ]
    
    response = dynamodb.batch_get_item(
        RequestItems={
            'fantasy-dashboard-data': {'Keys': keys}
        }
    )
    
    cached_values = {item['PlayerID']: item for item in response['Responses']['fantasy-dashboard-data']}
    
    # 2. Identify missing or stale
    missing = []
    for player_id in player_ids:
        if player_id not in cached_values:
            missing.append(player_id)
        elif is_stale(cached_values[player_id], hours=24):
            missing.append(player_id)
    
    # 3. Fetch missing from KeepTradeCut (batch API if available)
    if missing:
        print(f"Fetching {len(missing)} missing/stale values from KeepTradeCut")
        new_values = call_keep_trade_cut_batch(missing)
        
        # 4. Store in DynamoDB
        with dynamodb.batch_writer() as batch:
            for player_id, value_data in new_values.items():
                item = {
                    'PK': 'CACHE#PLAYER_VALUE',
                    'SK': f'PLAYER#{player_id}',
                    'PlayerID': player_id,
                    'PlayerName': value_data['name'],
                    'Value': value_data['value'],
                    'LastUpdated': now().isoformat(),
                    'TTL': int(now().timestamp()) + (7 * 24 * 3600)
                }
                batch.put_item(Item=item)
                cached_values[player_id] = item
    
    return cached_values
```

---

## Advantages Over CSV

### Performance
- ✅ **Fast lookups:** O(1) by player_id (CSV is O(n) scan)
- ✅ **Batch operations:** Get 100 players in 1 request
- ✅ **Concurrent access:** No file locking issues
- ✅ **Accessible from Lambda:** No file uploads needed

### Reliability
- ✅ **Atomic writes:** No corruption
- ✅ **Automatic backups:** Point-in-time recovery
- ✅ **No file I/O:** Cloud-native

### Features
- ✅ **TTL:** Auto-delete old values (7 days)
- ✅ **Versioning:** Track value changes over time
- ✅ **Queries:** "Get all values updated today"
- ✅ **Scalability:** Millions of players, no problem

---

## Migration Path

### Current (Pipeline CSV)
```
Stage 3:
  1. Load CSV → 2. Check cache → 3. Call KeepTradeCut → 4. Update CSV
```

### Future (Lambda + DynamoDB)
```
Ingestion Lambda:
  1. Query DynamoDB → 2. Check freshness → 3. Call KeepTradeCut → 4. Write DynamoDB

Read Lambda:
  1. Query DynamoDB cache → 2. Use values → 3. Calculate trade analysis
```

---

## DynamoDB Cache Schema

### Access Pattern 1: Get Single Player Value

**Query:**
```python
dynamodb.get_item(
    Key={'PK': 'CACHE#PLAYER_VALUE', 'SK': 'PLAYER#4018'}
)
```

**Response Time:** ~10ms

### Access Pattern 2: Get Batch of Player Values

**Query:**
```python
dynamodb.batch_get_item(
    RequestItems={
        'fantasy-dashboard-data': {
            'Keys': [
                {'PK': 'CACHE#PLAYER_VALUE', 'SK': 'PLAYER#4018'},
                {'PK': 'CACHE#PLAYER_VALUE', 'SK': 'PLAYER#138'},
                ...  # Up to 100 at once
            ]
        }
    }
)
```

**Response Time:** ~15ms for 100 players

### Access Pattern 3: Get All Cached Values

**Query:**
```python
dynamodb.query(
    KeyConditionExpression='PK = :pk',
    ExpressionAttributeValues={':pk': 'CACHE#PLAYER_VALUE'}
)
```

**Returns:** All cached player values (paginated if >1MB)

### Access Pattern 4: Get Recently Updated Values (via GSI)

**Query GSI1:**
```python
dynamodb.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk AND GSI1SK > :since',
    ExpressionAttributeValues={
        ':pk': 'PLAYER_VALUE',
        ':since': '2026-01-20T00:00:00Z'
    }
)
```

**Use case:** "Show me values updated today"

---

## Cache Refresh Strategy

### Option A: TTL-Based (Recommended)

**Set TTL on each item:**
```python
item['TTL'] = now_seconds + (24 * 3600)  # 24 hours
```

**DynamoDB automatically:**
- Deletes expired items (within 48 hours)
- No manual cleanup needed
- Cache naturally refreshes

**When Lambda queries:**
- If item exists → Use it
- If item missing (expired) → Fetch from KeepTradeCut
- Store new value with new TTL

### Option B: Timestamp-Based

**Check age on read:**
```python
cached = dynamodb.get_item(...)
if cached:
    age = now() - cached['LastUpdated']
    if age < timedelta(hours=24):
        return cached['Value']  # Fresh enough
    else:
        # Refresh from KeepTradeCut
        new_value = call_keep_trade_cut(player_id)
        update_cache(player_id, new_value)
        return new_value
```

---

## Example: Trade Analysis with DynamoDB Cache

```python
def analyze_trade(trade_data):
    """
    Analyze trade using DynamoDB-cached player values
    """
    
    # 1. Extract all player IDs from trade
    player_ids = extract_player_ids(trade_data)
    
    # 2. Get values from DynamoDB cache (batch request)
    values = get_player_values_batch(player_ids)
    # Returns immediately if cached (10ms)
    # Or fetches missing from KeepTradeCut (500ms)
    
    # 3. Calculate trade values
    team_a_value = sum(values[pid]['Value'] for pid in trade_data['teamA_players'])
    team_b_value = sum(values[pid]['Value'] for pid in trade_data['teamB_players'])
    
    # 4. Determine winner
    margin = team_a_value - team_b_value
    winner = 'teamA' if margin > 0 else 'teamB'
    
    return {
        'trade_id': trade_data['id'],
        'team_a_value': team_a_value,
        'team_b_value': team_b_value,
        'winner': winner,
        'margin': abs(margin),
        'values_used': values  # Include source data
    }
```

---

## Storage Comparison

### Current CSV Cache
```
File: asset_values_cache.csv (500 KB)
Players: ~1000 cached
Queries: O(n) scan through file
Concurrent access: File locking issues
```

### DynamoDB Cache
```
Table: fantasy-dashboard-data
Partition: CACHE#PLAYER_VALUE (dedicated partition)
Players: Unlimited
Queries: O(1) by player_id, O(n) for batch
Concurrent access: No issues (cloud-native)
```

---

## CSV to DynamoDB Migration

### One-Time Migration Script

```python
def migrate_csv_to_dynamodb():
    """
    One-time migration of CSV cache to DynamoDB
    """
    import pandas as pd
    
    # 1. Load existing CSV
    df = pd.read_csv('pipeline/asset_values_cache.csv')
    
    # 2. Write to DynamoDB
    with dynamodb.batch_writer() as batch:
        for _, row in df.iterrows():
            batch.put_item(Item={
                'PK': 'CACHE#PLAYER_VALUE',
                'SK': f"PLAYER#{row['player_id']}",
                'PlayerID': str(row['player_id']),
                'PlayerName': row['player_name'],
                'Value': int(row['value']),
                'LastUpdated': row['last_updated'],
                'Source': 'KeepTradeCut',
                'TTL': int(now().timestamp()) + (7 * 24 * 3600)
            })
    
    print(f"Migrated {len(df)} players to DynamoDB")
```

**Run once, then delete CSV file!**

---

## Pipeline Refactoring

### Current Stage 3 (CSV-based)
```python
# pipeline/stage3_cache_values.py

def cache_player_values(player_ids):
    # Load CSV
    cache_df = pd.read_csv('asset_values_cache.csv')
    
    # Check cache
    missing = [p for p in player_ids if p not in cache_df]
    
    # Fetch missing
    new_values = call_keep_trade_cut(missing)
    
    # Update CSV
    cache_df = cache_df.append(new_values)
    cache_df.to_csv('asset_values_cache.csv')
    
    return cache_df
```

### Future Stage 3 (DynamoDB-based)
```python
# backend-api/utils/value_cache.py

def get_player_values(player_ids: List[str]) -> Dict[str, int]:
    """
    Get player values from DynamoDB cache
    Falls back to KeepTradeCut if missing/stale
    """
    
    # 1. Batch query DynamoDB
    keys = [{'PK': 'CACHE#PLAYER_VALUE', 'SK': f'PLAYER#{pid}'} for pid in player_ids]
    response = dynamodb.batch_get_item(RequestItems={'fantasy-dashboard-data': {'Keys': keys}})
    
    cached = {item['PlayerID']: item for item in response['Responses']['fantasy-dashboard-data']}
    
    # 2. Identify stale/missing
    stale_threshold = now() - timedelta(hours=24)
    needs_refresh = [
        pid for pid in player_ids
        if pid not in cached or parse_time(cached[pid]['LastUpdated']) < stale_threshold
    ]
    
    # 3. Fetch from KeepTradeCut
    if needs_refresh:
        fresh_values = call_keep_trade_cut_batch(needs_refresh)
        
        # 4. Update DynamoDB cache
        with dynamodb.batch_writer() as batch:
            for pid, value_data in fresh_values.items():
                item = {
                    'PK': 'CACHE#PLAYER_VALUE',
                    'SK': f'PLAYER#{pid}',
                    'PlayerID': pid,
                    'PlayerName': value_data['name'],
                    'Value': value_data['value'],
                    'LastUpdated': now().isoformat(),
                    'TTL': int(now().timestamp()) + (7 * 24 * 3600)
                }
                batch.put_item(Item=item)
                cached[pid] = item
    
    # 5. Return all values
    return {pid: cached[pid]['Value'] for pid in player_ids}
```

---

## Benefits of DynamoDB Cache

### 1. Shared Across Pipeline & Lambda
```
Pipeline (daily) ──┐
                   ├──> DynamoDB Cache <──┐
Lambda (hourly) ───┘                      │
                                          │
                            KeepTradeCut API
```

**Both can read/write same cache!**

### 2. Automatic Expiration (TTL)
```python
# Set TTL when caching
item['TTL'] = now_seconds + (7 * 24 * 3600)

# DynamoDB automatically deletes after 7 days
# No manual cleanup needed!
```

### 3. Query Capabilities
```python
# Find all values updated today (CSV can't do this!)
dynamodb.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk AND GSI1SK > :today',
    ExpressionAttributeValues={
        ':pk': 'PLAYER_VALUE',
        ':today': today_start.isoformat()
    }
)
```

### 4. Historical Tracking (Optional)
```python
# Store value history
PK: PLAYER#4018  SK: VALUE#2026-01-20
PK: PLAYER#4018  SK: VALUE#2026-01-19
PK: PLAYER#4018  SK: VALUE#2026-01-18

# Query: "How has Saquon's value changed over time?"
```

---

## Migration Plan

### Step 1: Add Cache to DynamoDB Schema ✅
- Already in single-table design
- PK: `CACHE#PLAYER_VALUE`
- SK: `PLAYER#{player_id}`

### Step 2: Migrate Existing CSV Data
```bash
python3 migrate_csv_to_dynamodb.py
# One-time script to transfer existing cache
```

### Step 3: Update Pipeline (Backward Compatible)
```python
# New: Check DynamoDB first
# Fallback: Use CSV if DynamoDB unavailable
# Transition period: Both work
```

### Step 4: Remove CSV Dependency
```python
# Delete asset_values_cache.csv
# Use only DynamoDB
```

---

## Cost of Player Value Cache

**Storage:**
- 1000 players × 200 bytes = 200 KB
- **Cost:** $0.00 (free tier: 25GB)

**Reads (Lambda):**
- 1000 player lookups/day
- **Cost:** $0.00 (free tier: 25 RCU)

**Writes (KeepTradeCut updates):**
- 100 players updated/day
- **Cost:** $0.00 (free tier: 25 WCU)

**Total:** $0.00/month (within free tier!)

---

## Answer to Your Question

**YES - Replace CSV with DynamoDB!**

**Benefits:**
- ✅ Shared cache (pipeline + Lambda)
- ✅ Fast lookups (10ms vs 100ms)
- ✅ Automatic expiration (TTL)
- ✅ No file management
- ✅ Cloud-native
- ✅ Query capabilities
- ✅ Concurrent access safe

**Implementation:**
1. Use same single-table design
2. Partition key: `CACHE#PLAYER_VALUE`
3. Sort key: `PLAYER#{player_id}`
4. TTL: 7 days auto-expiry
5. Migrate existing CSV once
6. Both pipeline and Lambda use it

**This is the right architecture!** DynamoDB cache is superior to CSV in every way for your use case.

Ready to implement?