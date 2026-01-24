# DynamoDB Schema Design - Fantasy Dashboard

## Executive Summary

Based on analysis of your 7 JSON data types (trades, standings, waivers, playoffs, draft order, manager stats, league info) across multiple seasons, I recommend a **Single-Table Design** with composite keys for optimal performance and cost.

---

## Data Types Analysis

### 1. Trades (api-trades.json)
- **Volume:** 80+ trades per season
- **Complexity:** HIGH - nested assets with values
- **Updates:** Hourly (values change)
- **Queries:** By season, by manager, by date range, all trades
- **Size:** ~120KB per season

### 2. Manager Stats (api-teams.json)
- **Volume:** 12 managers
- **Complexity:** MEDIUM - aggregated statistics
- **Updates:** Hourly (after trade analysis)
- **Queries:** All managers, by manager, leaderboard
- **Size:** ~5KB per season

### 3. Standings (api-standings.json)
- **Volume:** 12 teams × 1 per week
- **Complexity:** LOW - wins/losses/points
- **Updates:** Weekly (after games)
- **Queries:** Current week, historical weeks
- **Size:** ~2KB per week

### 4. Waiver Wire (waiver-wire-page.json)
- **Volume:** 12 managers' metrics
- **Complexity:** MEDIUM - calculated metrics
- **Updates:** Weekly (after waivers clear)
- **Queries:** All managers, by manager
- **Size:** ~5KB per season

### 5. Playoff Scenarios (api-playoff-scenarios.json)
- **Volume:** 12 teams × 1 per week
- **Complexity:** HIGH - simulation results
- **Updates:** Weekly (10K Monte Carlo runs)
- **Queries:** Current week scenarios
- **Size:** ~7KB per week

### 6. Draft Order (api-draft-order.json)
- **Volume:** 12 picks × ~18 weeks
- **Complexity:** MEDIUM - progressive tracking
- **Updates:** Weekly (after standings)
- **Queries:** Current projections, by week
- **Size:** ~20KB per season

### 7. League Info
- **Volume:** 1 per season
- **Complexity:** LOW - metadata only
- **Updates:** Rarely
- **Queries:** By season
- **Size:** <1KB

---

## Recommended Schema: Single-Table Design

### Why Single Table?

✅ **DynamoDB Best Practice** - AWS recommends single-table for most use cases
✅ **Performance** - All queries are 1-request operations
✅ **Cost** - Fewer read capacity units
✅ **Scalability** - Handles infinite seasons
✅ **Flexibility** - Easy to add new data types

---

## Table Design

### Table Name: `fantasy-dashboard-data`

### Primary Key Structure

**Partition Key (PK):** `string` - Entity type + identifier
**Sort Key (SK):** `string` - Sub-entity or timestamp

**GSI 1 (Global Secondary Index):**
- **GSI1PK:** Season identifier
- **GSI1SK:** Entity type + timestamp

---

## Access Patterns & Key Design

### Pattern 1: Get All Trades for a Season

**Query:**
```python
PK = "SEASON#season_2"
SK begins_with "TRADE#"
```

**Items:**
```
PK: "SEASON#season_2"  SK: "TRADE#2025-11-18#1296312256438497280"
PK: "SEASON#season_2"  SK: "TRADE#2025-11-17#1296287239650684928"
...
```

**Attributes:**
```json
{
  "PK": "SEASON#season_2",
  "SK": "TRADE#2025-11-18#1296312256438497280",
  "EntityType": "trade",
  "Season": "season_2",
  "TradeId": "1296312256438497280",
  "TradeDate": "2025-11-18",
  "TeamA": "gnewman4",
  "TeamB": "wkerwin",
  "TeamAAssets": [...],  // Full nested structure
  "TeamBAssets": [...],
  "TeamAValueThen": 40.0,
  "TeamAValueNow": 39.0,
  "WinnerCurrent": "wkerwin",
  "SwingMargin": 80.0,
  "GSI1PK": "TRADE",
  "GSI1SK": "2025-11-18#season_2",
  "CreatedAt": "2025-11-18T10:30:00Z",
  "UpdatedAt": "2026-01-20T14:28:00Z"
}
```

---

### Pattern 2: Get Current Standings

**Query:**
```python
PK = "SEASON#season_3"
SK = "STANDINGS#CURRENT"
```

**Item:**
```json
{
  "PK": "SEASON#season_3",
  "SK": "STANDINGS#CURRENT",
  "EntityType": "standings",
  "Season": "season_3",
  "CurrentWeek": 1,
  "Standings": [
    {
      "team_name": "lndahayo",
      "wins": 0,
      "losses": 0,
      "points_for": 0.0,
      "division": "East"
    },
    ...
  ],
  "UpdatedAt": "2026-01-21T08:00:00Z"
}
```

---

### Pattern 3: Get Historical Standings by Week

**Query:**
```python
PK = "SEASON#season_3"
SK begins_with "STANDINGS#WEEK#"
```

**Items:**
```
PK: "SEASON#season_3"  SK: "STANDINGS#WEEK#01"
PK: "SEASON#season_3"  SK: "STANDINGS#WEEK#02"
...
```

---

### Pattern 4: Get Manager Stats for a Season

**Query:**
```python
PK = "SEASON#season_2"
SK begins_with "MANAGER#"
```

**Items:**
```
PK: "SEASON#season_2"  SK: "MANAGER#gnewman4"
PK: "SEASON#season_2"  SK: "MANAGER#lndahayo"
...
```

**Attributes:**
```json
{
  "PK": "SEASON#season_2",
  "SK": "MANAGER#gnewman4",
  "EntityType": "manager_stats",
  "Season": "season_2",
  "ManagerName": "gnewman4",
  "RealName": "Grant Newman",
  "TeamName": "Like a Good Naber",
  "TradeCount": 15,
  "WinRate": 0.73,
  "TotalValueGained": 5420,
  "UpdatedAt": "2026-01-20T14:28:00Z"
}
```

---

### Pattern 5: Get Waiver Wire Data

**Query:**
```python
PK = "SEASON#season_3"
SK = "WAIVERS#SUMMARY"
```

**Item:**
```json
{
  "PK": "SEASON#season_3",
  "SK": "WAIVERS#SUMMARY",
  "EntityType": "waiver_summary",
  "Season": "season_3",
  "Managers": [
    {
      "manager_name": "lndahayo",
      "hit_rate": 0.45,
      "churn_index": 1.2,
      "efficiency_score": 78
    },
    ...
  ],
  "LeagueAverages": {...},
  "UpdatedAt": "2026-01-21T08:00:00Z"
}
```

---

### Pattern 6: Get Playoff Scenarios

**Query:**
```python
PK = "SEASON#season_3"
SK = "PLAYOFFS#CURRENT" or "PLAYOFFS#WEEK#{week}"
```

---

### Pattern 7: Get Draft Order Projections

**Query:**
```python
PK = "SEASON#season_3"
SK = "DRAFT#2026"
```

---

### Pattern 8: Get ALL Data for a Season (Dashboard Load)

**Query:**
```python
PK = "SEASON#season_3"
SK begins_with ""  (all items)
```

**Single query returns:**
- Current standings
- All trades
- All manager stats
- Waiver summary
- Playoff scenarios
- Draft order

**Result:** One API call to load entire dashboard!

---

### Pattern 9: Cross-Season Queries (via GSI1)

**Query GSI1:**
```python
GSI1PK = "TRADE"
GSI1SK begins_with "2025-"
```

**Returns:** All trades across ALL seasons for a date range

---

## Complete Schema Definition

### Primary Table Structure

```
Table: fantasy-dashboard-data

Primary Key:
  - PK (Partition Key): String
  - SK (Sort Key): String

GSI1 (Global Secondary Index):
  - GSI1PK (Partition Key): String
  - GSI1SK (Sort Key): String

Attributes:
  - EntityType: String (trade, standings, manager_stats, etc.)
  - Season: String (season_2, season_3, etc.)
  - Data: Map (the actual entity data)
  - CreatedAt: String (ISO timestamp)
  - UpdatedAt: String (ISO timestamp)
  - TTL: Number (optional - for auto-cleanup of old data)
```

---

## Key Patterns

### For Trades:
```
PK: SEASON#{season_id}
SK: TRADE#{date}#{trade_id}
GSI1PK: TRADE
GSI1SK: {date}#{season_id}
```

### For Standings:
```
PK: SEASON#{season_id}
SK: STANDINGS#CURRENT  (latest)
SK: STANDINGS#WEEK#{week_number}  (historical)
```

### For Manager Stats:
```
PK: SEASON#{season_id}
SK: MANAGER#{manager_name}
GSI1PK: MANAGER
GSI1SK: {manager_name}#{season_id}
```

### For Waiver Wire:
```
PK: SEASON#{season_id}
SK: WAIVERS#SUMMARY
```

### For Playoffs:
```
PK: SEASON#{season_id}
SK: PLAYOFFS#CURRENT
SK: PLAYOFFS#WEEK#{week_number}
```

### For Draft Order:
```
PK: SEASON#{season_id}
SK: DRAFT#{year}
```

### For League Info:
```
PK: SEASON#{season_id}
SK: METADATA
```

---

## Example Items in Table

```
┌─────────────────────────┬───────────────────────────────────┬──────────────────┐
│ PK                      │ SK                                │ EntityType       │
├─────────────────────────┼───────────────────────────────────┼──────────────────┤
│ SEASON#season_2         │ TRADE#2025-11-18#129631225...     │ trade            │
│ SEASON#season_2         │ TRADE#2025-11-17#129628723...     │ trade            │
│ SEASON#season_2         │ MANAGER#gnewman4                  │ manager_stats    │
│ SEASON#season_2         │ MANAGER#lndahayo                  │ manager_stats    │
│ SEASON#season_2         │ STANDINGS#CURRENT                 │ standings        │
│ SEASON#season_2         │ STANDINGS#WEEK#14                 │ standings        │
│ SEASON#season_2         │ WAIVERS#SUMMARY                   │ waiver_summary   │
│ SEASON#season_2         │ PLAYOFFS#CURRENT                  │ playoff_scenario │
│ SEASON#season_2         │ DRAFT#2026                        │ draft_order      │
│ SEASON#season_2         │ METADATA                          │ league_info      │
│ SEASON#season_3         │ TRADE#2025-12-01#...              │ trade            │
│ SEASON#season_3         │ STANDINGS#CURRENT                 │ standings        │
│ ...                     │ ...                               │ ...              │
└─────────────────────────┴───────────────────────────────────┴──────────────────┘
```

---

## Query Examples

### Frontend: Load Dashboard for Season 3

```python
response = dynamodb.query(
    KeyConditionExpression="PK = :pk",
    ExpressionAttributeValues={":pk": "SEASON#season_3"}
)
# Returns ALL data for season 3 in one query!
```

### Frontend: Get Just Trades for Season 2

```python
response = dynamodb.query(
    KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
    ExpressionAttributeValues={
        ":pk": "SEASON#season_2",
        ":sk": "TRADE#"
    }
)
```

### Backend: Get All Trades Across All Seasons (GSI)

```python
response = dynamodb.query(
    IndexName="GSI1",
    KeyConditionExpression="GSI1PK = :pk",
    ExpressionAttributeValues={":pk": "TRADE"}
)
```

---

## Write Patterns (Ingestion Lambda)

### Upsert Trade

```python
dynamodb.put_item(Item={
    'PK': f"SEASON#{season_id}",
    'SK': f"TRADE#{trade_date}#{trade_id}",
    'EntityType': 'trade',
    'Season': season_id,
    'Data': {
        # Full trade object from your JSON
    },
    'GSI1PK': 'TRADE',
    'GSI1SK': f"{trade_date}#{season_id}",
    'CreatedAt': now(),
    'UpdatedAt': now()
})
```

### Batch Write All Trades

```python
with dynamodb.batch_writer() as batch:
    for trade in trades:
        batch.put_item(Item={
            'PK': f"SEASON#{trade['season']}",
            'SK': f"TRADE#{trade['tradeDate']}#{trade['tradeId']}",
            'EntityType': 'trade',
            'Data': trade,
            'UpdatedAt': now()
        })
```

---

## Cost Analysis

### Storage Cost

**Data size per season:**
- Trades: 120KB
- Standings: 2KB × 18 weeks = 36KB
- Manager stats: 5KB
- Waivers: 5KB
- Playoffs: 7KB × 18 weeks = 126KB
- Draft: 20KB
- **Total per season:** ~312KB

**For 5 seasons:** ~1.6MB = $0.00/month (free tier: 25GB)

### Read/Write Cost

**Daily ingestion (1x/day):**
- Write 100 items = 100 WCU
- Monthly: 3,000 WCU = $0.00 (free tier: 25 WCU)

**User requests (100 users/day):**
- Read 1 season = 1 RCU
- Monthly: 3,000 RCU = $0.00 (free tier: 25 RCU)

**Total DynamoDB cost:** $0.00/month (within free tier!)

---

##Schema Advantages

### 1. Scalability
- ✅ Add season_4, season_5, ... infinity
- ✅ No schema changes needed
- ✅ Partition key naturally distributes data

### 2. Performance
- ✅ Single query loads entire dashboard
- ✅ Sub-100ms response times
- ✅ No joins needed

### 3. Flexibility
- ✅ Each entity can have different attributes
- ✅ Easy to add new data types
- ✅ Version schema within items

### 4. Cost
- ✅ Free tier covers years of usage
- ✅ On-demand pricing (pay per request)
- ✅ No idle costs

---

## Implementation: SAM Template

### DynamoDB Table Definition

```yaml
# backend-api/fantasy-backend/template.yaml

Resources:
  DashboardDataTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: fantasy-dashboard-data
      BillingMode: PAY_PER_REQUEST  # On-demand pricing
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: GSI1PK
          AttributeType: S
        - AttributeName: GSI1SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: GSI1
          KeySchema:
            - AttributeName: GSI1PK
              KeyType: HASH
            - AttributeName: GSI1SK
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES  # For future analytics
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      Tags:
        - Key: Environment
          Value: production
        - Key: Application
          Value: fantasy-dashboard
```

---

## Lambda Functions

### Function 1: Ingestion (Scheduled)

**Trigger:** EventBridge (hourly)

**Purpose:** Fetch from Sleeper, process, write to DynamoDB

```python
def ingestion_handler(event, context):
    # 1. Fetch from Sleeper API (all weeks)
    trades = fetch_all_trades_for_season('season_3')
    
    # 2. Call KeepTradeCut for values
    values = fetch_player_values(extract_player_ids(trades))
    
    # 3. Calculate analysis (winners, margins, etc.)
    analyzed_trades = analyze_trades(trades, values)
    
    # 4. Write to DynamoDB
    with dynamodb.batch_writer() as batch:
        for trade in analyzed_trades:
            batch.put_item(Item={
                'PK': f"SEASON#{trade['season']}",
                'SK': f"TRADE#{trade['tradeDate']}#{trade['tradeId']}",
                'EntityType': 'trade',
                **trade  # Full trade data
            })
    
    # 5. Update manager stats
    stats = calculate_manager_stats(analyzed_trades)
    for manager, stats_data in stats.items():
        dynamodb.put_item(Item={
            'PK': f"SEASON#season_3",
            'SK': f"MANAGER#{manager}",
            'EntityType': 'manager_stats',
            **stats_data
        })
    
    return {'statusCode': 200, 'processed': len(analyzed_trades)}
```

### Function 2: Read API (On-Demand)

**Trigger:** API Gateway

**Purpose:** Query DynamoDB, return to frontend

```python
def read_handler(event, context):
    path = event['path']
    season = event['queryStringParameters'].get('season', 'season_3')
    
    if path == '/api/trades':
        response = dynamodb.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
            ExpressionAttributeValues={
                ":pk": f"SEASON#{season}",
                ":sk": "TRADE#"
            }
        )
        return format_response(response['Items'])
    
    elif path == '/api/dashboard':
        # Load EVERYTHING for a season
        response = dynamodb.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": f"SEASON#{season}"}
        )
        return format_dashboard(response['Items'])
```

---

## Migration Strategy

### Phase 1: Create Table ✅ NEXT
1. Add DynamoDB to SAM template
2. Deploy (creates table automatically)
3. Verify table created

### Phase 2: Ingestion Lambda
1. Port pipeline logic to Lambda
2. Schedule hourly (EventBridge)
3. Test writes to DynamoDB

### Phase 3: Read Lambda  
1. Update existing Lambda to read from DynamoDB
2. Test all endpoints
3. Verify performance

### Phase 4: Frontend Integration
1. Update React to call Lambda
2. Deploy frontend
3. Real-time dashboard live!

---

## Alternative: Multi-Table Design (Not Recommended)

### Structure
```
Table 1: trades-table (PK: season+tradeId)
Table 2: standings-table (PK: season+week)
Table 3: managers-table (PK: season+manager)
...
```

### Why Not?
- ❌ Multiple queries to load dashboard (slower)
- ❌ More complex code
- ❌ Higher costs (more RCUs)
- ❌ Harder to maintain

**Single-table is superior for your use case.**

---

## Next Steps

1. **Add DynamoDB table to SAM template** (5 min)
2. **Deploy to create table** (2 min)
3. **Write ingestion Lambda** (1-2 hours)
4. **Test end-to-end** (30 min)
5. **Connect frontend** (30 min)

Ready to add DynamoDB to your SAM template?
