# Lambda Architecture Options

## Your Question: One Big Lambda or Many Small Ones?

Great question! There are two common patterns:

---

## Option 1: Monolithic Lambda (Recommended for Learning)

### Structure
```
One Lambda Function
    ├── GET /trades       → Fetch trades
    ├── GET /standings    → Fetch standings  
    ├── GET /waivers      → Fetch waiver wire
    ├── GET /playoffs     → Monte Carlo simulations
    └── GET /draft-order  → Draft projections
```

### Pros
- ✅ Simpler to manage (one deployment)
- ✅ Easier to understand starting out
- ✅ Share code between endpoints
- ✅ One Lambda = one place to look

### Cons
- ❌ All features deploy together
- ❌ Larger code package
- ❌ One error can affect all endpoints

### Code Structure
```python
def lambda_handler(event, context):
    path = event['path']
    
    if path == '/trades':
        return get_trades()
    elif path == '/standings':
        return get_standings()
    elif path == '/waivers':
        return get_waivers()
    # etc...
```

---

## Option 2: Microservices (Best Practice, More Complex)

### Structure
```
Multiple Lambda Functions
    ├── TradesFunction     → GET /trades
    ├── StandingsFunction  → GET /standings
    ├── WaiversFunction    → GET /waivers
    ├── PlayoffsFunction   → GET /playoffs
    └── DraftFunction      → GET /draft-order
```

### Pros
- ✅ Independent deployment (update trades without touching waivers)
- ✅ Isolated failures (trades breaks, standings still works)
- ✅ Easier to scale individual endpoints
- ✅ Best practice for production

### Cons
- ❌ More complex to set up
- ❌ More files to manage
- ❌ Duplicate code between functions

---

## My Recommendation for You

### Start with **Monolithic** (Option 1)

**Why:**
1. **Learning:** Easier to understand one Lambda
2. **Iteration:** Deploy all changes at once
3. **Simplicity:** One file to edit
4. **Your Use Case:** All endpoints serve similar purpose (fantasy data)

**You can always split later** when you're comfortable!

---

## Proposed Architecture for Your Dashboard

### Single Lambda with Multiple Routes

```
API Gateway: https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com
    ├── GET /api/trades        → Real-time Sleeper trades
    ├── GET /api/standings     → Current standings
    ├── GET /api/waivers       → Waiver wire data
    ├── GET /api/playoffs      → Playoff scenarios
    └── GET /api/draft-order   → Draft projections
```

**All handled by ONE Lambda function**

---

## What Should Be in Lambda vs Static?

### Keep in Lambda (Real-Time Data)
✅ Trades (change frequently)
✅ Standings (update weekly)
✅ Waiver wire (changes often)

### Keep Static (Computed Data)
✅ Playoff Monte Carlo (takes time to compute, run daily)
✅ Historical analysis (doesn't change)
✅ Manager statistics (computed once daily)

---

## Hybrid Approach (Best of Both Worlds)

### My Recommendation:

```
Frontend
    ├── Static Data (S3)
    │   ├── Playoff scenarios (pre-computed)
    │   ├── Historical trends
    │   └── Manager stats
    │
    └── Dynamic Data (Lambda)
        ├── Current standings (real-time)
        ├── Latest trades (real-time)
        └── Waiver wire (real-time)
```

**Why:**
- Use Lambda for data that changes frequently
- Use static JSON for heavy computations
- Best performance + best cost

---

## Proposed Lambda Function Structure

```python
def lambda_handler(event, context):
    """
    Single Lambda handling multiple endpoints
    """
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
    # Route to appropriate handler
    if path == '/api/trades':
        return get_trades()
    elif path == '/api/standings':
        return get_standings()
    elif path == '/api/waivers':
        return get_waivers()
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Not found'})
        }

def get_trades():
    # Fetch from Sleeper API
    # Return formatted trades
    pass

def get_standings():
    # Fetch from Sleeper API
    # Return current standings
    pass

def get_waivers():
    # Fetch from Sleeper API
    # Return waiver data
    pass
```

---

## What Should We Build First?

### Phase 1: One Simple Endpoint (Start Small)

**Build:** `/api/trades` endpoint only
**Test:** Make sure it works
**Learn:** Understand Lambda + API Gateway

### Phase 2: Add More Endpoints

**Add:** `/api/standings`
**Add:** `/api/waivers`
**Gradually** expand functionality

### Phase 3: Connect to Frontend

**Update:** React to call Lambda instead of static JSON
**Test:** Real-time data loading

---

## My Recommendation

**Let's build ONE endpoint first** - `/api/trades`

**Steps:**
1. Finish the trades endpoint (I already wrote it!)
2. Deploy to AWS
3. Test it works
4. Connect frontend to use it
5. Then add more endpoints one by one

**This way you learn incrementally!**

---

Want to proceed with deploying the trades endpoint I just wrote?