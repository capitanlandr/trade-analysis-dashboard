# AWS Migration Sprint Plan v2 -- Path A: Backend Enrichment (Pre-Computed)

**Status:** REVISED -- Addressing SDM Conditions
**Author:** TPM (Technical Program Manager)
**Date:** 2026-02-12
**SDM Review Result:** APPROVED WITH CONDITIONS (v1) -- this document is the v2 response
**Architecture Alignment:** Pre-computed enrichment (daily cron writes to DynamoDB, API reads)

---

## Table of Contents

1. [Changes from v1](#changes-from-v1)
2. [Architecture Overview](#architecture-overview)
3. [Phase Structure](#phase-structure)
4. [Complete Task List](#complete-task-list)
5. [Dependency Graph](#dependency-graph)
6. [Team Allocation](#team-allocation)
7. [DynamoDB Schema (Enriched Data)](#dynamodb-schema-enriched-data)
8. [Risk Register](#risk-register)
9. [Cost Model](#cost-model)

---

## Changes from v1

### Condition 1 (BLOCKING) -- Architecture Alignment: RESOLVED

| Aspect | v1 (Request-Time) | v2 (Pre-Computed) |
|--------|--------------------|--------------------|
| Enrichment trigger | Every API call runs enrichment | Daily cron Lambda writes enriched data to DynamoDB |
| Dashboard API Lambda | Heavy -- runs pipeline logic per request | Thin read layer -- single DynamoDB query + JSON format |
| Endpoint complexity | XL per endpoint (each reimplements enrichment) | S per endpoint (DynamoDB GetItem + serialize) |
| New major task | None | Task 2.1: Build Enrichment Lambda (XL) |
| Latency | 5-15s per request (Sleeper + DynastyProcess calls) | <100ms per request (DynamoDB read) |

**Impact:** Phase 2-3 endpoint tasks drop from M/L to S complexity. A single XL Enrichment Lambda task replaces per-endpoint enrichment logic. This is architecturally correct for a 12-user dashboard with daily data updates.

### Condition 2 (BLOCKING) -- Missing Dependencies: RESOLVED

Three new tasks added to Phase 1:

| New Task | Why It Was Missing | Owner | Complexity |
|----------|--------------------|-------|------------|
| 1.3: DynastyProcess Valuation Ingestion | Ingestion Lambda only ingests raw Sleeper data. Enrichment needs player values to calculate trade margins. | sde-infra | M |
| 1.4: Team Identity Mapping Upload | Pipeline uses `team_identity_mapping.csv` for roster_id-to-username resolution. Enrichment Lambda needs it at runtime. | sde-infra | S |
| 1.5: Pick Origin Mapping Upload | `pick_origin_mapping.py` and `draft_order_2026_progressive.json` contain pick ownership data. Enrichment Lambda needs them. | sde-infra | S |

### Condition 3 (BLOCKING) -- Team Rebalancing: RESOLVED

| Engineer | v1 Tasks | v2 Tasks | Change |
|----------|----------|----------|--------|
| sde-pipeline | 9 tasks (overloaded) | 5 tasks (enrichment Lambda + JSON gen) | -4 tasks |
| sde-frontend | 0 tasks for 8 weeks (idle) | 5 tasks (API client + endpoint work + frontend cutover) | +5 tasks |
| sde-infra | 3 tasks | 5 tasks (infra + data ingestion + draft order endpoint) | +2 tasks |

No engineer is idle for more than 1 sprint. sde-frontend starts API client work with mock responses in Phase 2, running parallel with backend development.

### Condition 4 (REQUIRED) -- Scope Cuts: RESOLVED

| Removed | Replacement |
|---------|-------------|
| Task 6.2: Lambda@Edge canary release | Simple `USE_LAMBDA_API` env var toggle in `api.ts` (12 users, not Netflix) |
| Task 5.3: Load testing with Locust | Manual smoke testing via `curl` against each endpoint |
| PE progressive enrichment checksumming | Full enrichment every run (estimated $0/month on free tier) |
| PE 7-day version history | Overwrite enriched data in place. Static JSON in `dashboard/frontend/public/` is the rollback. |
| PE in-memory Lambda cache tier | DynamoDB-only caching. Lambda cold starts make in-memory caching useless for daily cron runs. |

### Condition 5 (REQUIRED) -- DynamoDB Schema: RESOLVED

Using EXISTING `SEASON#{season_id}` PK pattern with new SK prefixes:

```
PK: SEASON#{season_id}    SK: ENRICHED_TRADES#LATEST
PK: SEASON#{season_id}    SK: ENRICHED_TEAMS#LATEST
PK: SEASON#{season_id}    SK: ENRICHED_STATS#LATEST
PK: SEASON#{season_id}    SK: ENRICHED_STANDINGS#LATEST
PK: SEASON#{season_id}    SK: ENRICHED_PLAYOFF#LATEST
PK: SEASON#{season_id}    SK: ENRICHED_DRAFTORDER#LATEST
PK: SEASON#{season_id}    SK: ENRICHED_WAIVERS#LATEST
```

No new `ENRICHED#{season_id}` PK pattern introduced. All enriched data lives alongside raw data under the same partition key.

### Condition 6 (ADVISORY) -- Pandas/NumPy Lambda Packaging: RESOLVED

New Task 1.6 added: "Build Lambda Layer or Container Image for Python Dependencies." Decision: use a Lambda Layer for pandas/numpy (recommended for this project size). Container image is the fallback if the layer exceeds 250MB unzipped.

---

## Architecture Overview

```
                         WRITE PATH (Daily Cron)
                         =======================

  Sleeper API ──> Ingestion Lambda ──> DynamoDB (raw data)
                       (hourly)           SEASON#{id} / TRADE#...
                                          SEASON#{id} / WAIVER#...
                                          SEASON#{id} / STANDINGS#CURRENT
                                          SEASON#{id} / MATCHUPS#WEEK#...

  DynastyProcess ──> Valuation Ingestion ──> DynamoDB (valuations)
  GitHub CSV            (daily)                SEASON#{id} / VALUATIONS#LATEST

  Enrichment Lambda (daily cron, triggered after ingestion)
       │
       ├── Reads: raw trades, raw waivers, standings, matchups, valuations
       ├── Reads: team_identity_mapping.csv (from S3 or bundled)
       ├── Reads: pick_origin_mapping + draft_order_2026_progressive.json
       ├── Runs: pipeline stages 2-4 logic (extract assets, cache values, analyze)
       ├── Runs: waiver wire enrichment (stage 5 logic)
       ├── Runs: standings/playoff/draft order enrichment
       │
       └── Writes: ENRICHED_TRADES#LATEST, ENRICHED_TEAMS#LATEST, etc.

                         READ PATH (On Request)
                         ======================

  Frontend ──> API Gateway ──> Dashboard API Lambda
                                    │
                                    ├── GET /api/trades     ──> GetItem(SEASON#s3, ENRICHED_TRADES#LATEST)
                                    ├── GET /api/teams      ──> GetItem(SEASON#s3, ENRICHED_TEAMS#LATEST)
                                    ├── GET /api/stats      ──> GetItem(SEASON#s3, ENRICHED_STATS#LATEST)
                                    ├── GET /api/standings  ──> GetItem(SEASON#s3, ENRICHED_STANDINGS#LATEST)
                                    ├── GET /api/playoffs   ──> GetItem(SEASON#s3, ENRICHED_PLAYOFF#LATEST)
                                    ├── GET /api/draft-order──> GetItem(SEASON#s3, ENRICHED_DRAFTORDER#LATEST)
                                    └── GET /api/waivers    ──> GetItem(SEASON#s3, ENRICHED_WAIVERS#LATEST)
                                    │
                                    └── Returns: JSON (same shape as current static files)
```

---

## Phase Structure

### Phase 1: Foundation (Sprints 1-2, Weeks 1-4)
**Theme:** Get all data into DynamoDB. Build the dependency layer.

### Phase 2: Enrichment + Endpoint Build (Sprints 3-4, Weeks 5-8)
**Theme:** Build the Enrichment Lambda. Build thin API endpoints. Start frontend API client with mocks.

### Phase 3: Remaining Endpoints + Integration (Sprints 5-6, Weeks 9-12)
**Theme:** Complete all endpoints. Wire frontend to Lambda API. Smoke test. Cut over.

---

## Complete Task List

### Phase 1: Foundation (Weeks 1-4)

#### Task 1.1: Switch DynamoDB to Provisioned Free Tier
- **Owner:** sde-infra
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** None
- **Sprint:** 1

**Files affected:**
- `/backend-api/fantasy-backend/template.yaml`

**Description:**
Change DynamoDB `BillingMode` from `PAY_PER_REQUEST` to `PROVISIONED` with free-tier capacity (25 RCU, 25 WCU). This ensures the project stays at $0/month. Also disable `PointInTimeRecoverySpecification` (costs extra, not needed for a hobby project -- static JSON is the backup).

**Acceptance criteria:**
- `template.yaml` updated with `BillingMode: PROVISIONED`, `ReadCapacityUnits: 25`, `WriteCapacityUnits: 25`
- `PointInTimeRecoveryEnabled: false`
- `sam deploy` succeeds
- DynamoDB console shows provisioned mode with 25/25 RCU/WCU
- Verify no cost change in AWS Cost Explorer after 24h

---

#### Task 1.2: Validate Existing Ingestion Lambda Writes Correct Raw Data
- **Owner:** sde-infra
- **Complexity:** S
- **Priority:** P0
- **Dependencies:** Task 1.1
- **Sprint:** 1

**Files affected:**
- `/backend-api/fantasy-backend/ingestion_lambda/app.py` (read-only validation)

**Description:**
Verify the existing ingestion Lambda (`ingestion_lambda/app.py`) correctly writes raw Sleeper data to DynamoDB. Run a backfill (`{'backfill': true}`) and confirm all 6 data types are present: trades (SK=`TRADE#*`), waivers (SK=`WAIVER#*`), matchups (SK=`MATCHUPS#WEEK#*`), NFL stats (PK=`NFL_STATS#*`), standings (SK=`STANDINGS#CURRENT`), and league metadata (SK=`METADATA`).

**Acceptance criteria:**
- Invoke Lambda with `{"backfill": true}` via AWS Console or CLI
- DynamoDB table scan shows items for both `season_2` and `season_3`
- At least 80 trade items for season_2, 60+ for season_3
- Standings, metadata, matchups, and waivers present for both seasons
- Document any missing data types in a comment on this task

---

#### Task 1.3: DynastyProcess Valuation Data Ingestion
- **Owner:** sde-infra
- **Complexity:** M
- **Priority:** P0 (blocks enrichment Lambda and every endpoint)
- **Dependencies:** Task 1.1
- **Sprint:** 1-2

**Files affected:**
- `/backend-api/fantasy-backend/ingestion_lambda/app.py` (add `ingest_valuations()`)
- `/backend-api/fantasy-backend/template.yaml` (no changes needed -- Lambda already has DynamoDB write permissions)

**Description:**
The current ingestion Lambda does NOT ingest player valuation data. It only ingests raw Sleeper API data. The enrichment library (pipeline stages 3-4) needs DynastyProcess player values (`value_2qb` column) to calculate trade margins, winner determination, and value swing.

Add a new `ingest_valuations()` function that:
1. Fetches the DynastyProcess values CSV from `https://github.com/dynastyprocess/data/raw/master/files/values.csv`
2. Parses the CSV (player name, position, value_2qb, scrape_date)
3. Writes to DynamoDB with: `PK=SEASON#{season_id}`, `SK=VALUATIONS#LATEST`
4. Stores the full values list as a JSON-serialized attribute (the CSV is ~2,500 rows, ~300KB -- within DynamoDB's 400KB item limit)
5. Also stores `ValuationDate` (scrape_date from CSV) and `PlayerCount` for observability

Call `ingest_valuations()` from `ingest_season()` for each season.

**Acceptance criteria:**
- After Lambda invocation, DynamoDB has item `PK=SEASON#season_3, SK=VALUATIONS#LATEST`
- Item contains a `Players` list with 2000+ entries
- Each entry has `player`, `position`, `value_2qb` fields
- `ValuationDate` attribute matches the DynastyProcess CSV's `scrape_date`
- Existing ingestion functions (trades, waivers, etc.) still work unchanged

---

#### Task 1.4: Upload Team Identity Mapping to S3/DynamoDB
- **Owner:** sde-infra
- **Complexity:** S
- **Priority:** P1 (blocks enrichment Lambda)
- **Dependencies:** Task 1.1
- **Sprint:** 2

**Files affected:**
- `/backend-api/fantasy-backend/ingestion_lambda/app.py` (add `ingest_team_mappings()`)
- Source data: `/team_identity_mapping.csv` (12 rows)

**Description:**
The pipeline uses `team_identity_mapping.csv` for roster_id-to-sleeper_username resolution. The Enrichment Lambda needs this mapping at runtime. Store it in DynamoDB as a reference data item.

Add `ingest_team_mappings()`:
1. Read `team_identity_mapping.csv` (bundled with the Lambda or fetched from S3)
2. Write to DynamoDB: `PK=REFERENCE`, `SK=TEAM_IDENTITY_MAPPING`
3. Store as a list of 12 team objects with `roster_id`, `sleeper_username`, `real_name`, `current_team_name`

Since this data rarely changes (only when a manager changes their Sleeper display name), it can be a manual upload step or included in the ingestion cron.

**Acceptance criteria:**
- DynamoDB has item `PK=REFERENCE, SK=TEAM_IDENTITY_MAPPING`
- Item contains 12 team entries with correct roster_id/username pairs matching `/team_identity_mapping.csv`
- Data matches current file at repo root: `team_identity_mapping.csv`

---

#### Task 1.5: Upload Pick Origin Mapping and Draft Order to DynamoDB
- **Owner:** sde-infra
- **Complexity:** S
- **Priority:** P1 (blocks enrichment Lambda)
- **Dependencies:** Task 1.1
- **Sprint:** 2

**Files affected:**
- `/backend-api/fantasy-backend/ingestion_lambda/app.py` (add `ingest_pick_mappings()`)
- Source data: `/pipeline/pick_origin_mapping.py` (EXPLICIT_ORIGINS dict)
- Source data: `/pipeline/draft_order_2026_progressive.json`

**Description:**
The pipeline's `pick_origin_mapping.py` contains `EXPLICIT_ORIGINS` -- a static dict mapping (round, pick) to origin owner. The `draft_order_2026_progressive.json` contains the 2026 draft order for exact pick valuations. The Enrichment Lambda needs both for pick valuation logic.

Add `ingest_pick_mappings()`:
1. Bundle the pick origin data (hardcode the EXPLICIT_ORIGINS dict or read from a JSON file)
2. Bundle the 2026 draft order JSON
3. Write to DynamoDB:
   - `PK=REFERENCE`, `SK=PICK_ORIGIN_MAPPING_2025` -- the 48-pick origin mapping
   - `PK=REFERENCE`, `SK=DRAFT_ORDER_2026` -- the full draft order JSON

**Acceptance criteria:**
- DynamoDB has both reference items
- `PICK_ORIGIN_MAPPING_2025` contains 48 entries (4 rounds x 12 picks)
- `DRAFT_ORDER_2026` contains draft_order object matching `/pipeline/draft_order_2026_progressive.json`
- Enrichment Lambda (Task 2.1) can read these items successfully

---

#### Task 1.6: Build Lambda Layer for Python Dependencies (pandas, numpy)
- **Owner:** sde-infra
- **Complexity:** M
- **Priority:** P0 (blocks enrichment Lambda)
- **Dependencies:** None (can start immediately)
- **Sprint:** 1-2

**Files affected:**
- `/backend-api/fantasy-backend/template.yaml` (add Layer resource)
- NEW: `/backend-api/fantasy-backend/enrichment_lambda/requirements.txt`
- NEW: `/backend-api/fantasy-backend/build-layer.sh` (build script)

**Description:**
The enrichment Lambda needs pandas and numpy for the pipeline's valuation logic (stage 3 uses pandas DataFrames extensively for player lookups, CSV parsing, and value calculations). These are large dependencies (~70MB for numpy, ~50MB for pandas) that exceed Lambda's default 50MB deployment package limit.

**Approach: Lambda Layer (preferred)**
1. Create a build script that installs pandas + numpy into a layer-compatible directory structure
2. Target `python3.11` + `arm64` (matching existing Lambda architecture in template.yaml)
3. Use `pip install --platform manylinux2014_aarch64 --target python/lib/python3.11/site-packages --only-binary=:all: pandas numpy`
4. Package into a ZIP and deploy as a Lambda Layer
5. Reference the Layer in the Enrichment Lambda's SAM config

If the layer exceeds 250MB unzipped (unlikely with arm64 binaries), fall back to container image deployment using a Dockerfile with `public.ecr.aws/lambda/python:3.11` base.

**Acceptance criteria:**
- Lambda Layer deploys successfully via `sam deploy`
- Layer contains pandas and numpy importable by Python 3.11
- Enrichment Lambda can `import pandas as pd` and `import numpy as np` without error
- Layer size is under 250MB unzipped
- `build-layer.sh` script is documented and reproducible

---

### Phase 2: Enrichment + Endpoint Build (Weeks 5-8)

#### Task 2.1: Build Enrichment Lambda
- **Owner:** sde-pipeline
- **Complexity:** XL
- **Priority:** P0 (core of the entire migration)
- **Dependencies:** Tasks 1.2, 1.3, 1.4, 1.5, 1.6
- **Sprint:** 3-4

**Files affected:**
- NEW: `/backend-api/fantasy-backend/enrichment_lambda/app.py`
- NEW: `/backend-api/fantasy-backend/enrichment_lambda/enrichment_engine.py`
- NEW: `/backend-api/fantasy-backend/enrichment_lambda/requirements.txt`
- `/backend-api/fantasy-backend/template.yaml` (add EnrichmentFunction resource + EventBridge schedule)

**Description:**
This is the centerpiece of the pre-computed architecture. The Enrichment Lambda runs daily (after ingestion), reads raw data + valuations + reference data from DynamoDB, runs the pipeline's enrichment logic, and writes 7 enriched JSON documents back to DynamoDB.

**What it does (maps to existing pipeline stages):**

1. **Read inputs from DynamoDB:**
   - Raw trades: `PK=SEASON#{id}, SK begins_with TRADE#`
   - Raw waivers: `PK=SEASON#{id}, SK begins_with WAIVER#`
   - Standings: `PK=SEASON#{id}, SK=STANDINGS#CURRENT`
   - Matchups: `PK=SEASON#{id}, SK begins_with MATCHUPS#`
   - NFL stats: `PK=NFL_STATS#{year}, SK begins_with WEEK#`
   - Valuations: `PK=SEASON#{id}, SK=VALUATIONS#LATEST`
   - Team mapping: `PK=REFERENCE, SK=TEAM_IDENTITY_MAPPING`
   - Pick mappings: `PK=REFERENCE, SK=PICK_ORIGIN_MAPPING_2025`
   - Draft order: `PK=REFERENCE, SK=DRAFT_ORDER_2026`

2. **Run enrichment logic (ported from pipeline):**
   - Extract trade assets (stage 2 logic from `stage2_extract_assets.py`)
   - Cache player/pick values using DynastyProcess data (stage 3 logic from `stage3_cache_values.py`)
   - Analyze trades: calculate margins, winners, value swings (stage 4 logic from `stage4_final.py`)
   - Process waiver wire analysis (stage 5 logic from `stage5_waiver_wire.py`)
   - Calculate team/manager aggregate stats (from `generate_dashboard_json.py`)
   - Format standings with enrichment
   - Calculate playoff scenarios (simplified from `simulate_playoff_scenarios.py`)
   - Calculate draft order projections (from `calculate_progressive_draft_order.py`)

3. **Write enriched outputs to DynamoDB:**
   - `PK=SEASON#{id}, SK=ENRICHED_TRADES#LATEST` -- full api-trades.json equivalent
   - `PK=SEASON#{id}, SK=ENRICHED_TEAMS#LATEST` -- full api-teams.json equivalent
   - `PK=SEASON#{id}, SK=ENRICHED_STATS#LATEST` -- full api-stats-summary.json equivalent
   - `PK=SEASON#{id}, SK=ENRICHED_STANDINGS#LATEST` -- full api-standings.json equivalent
   - `PK=SEASON#{id}, SK=ENRICHED_PLAYOFF#LATEST` -- full api-playoff-scenarios.json equivalent
   - `PK=SEASON#{id}, SK=ENRICHED_DRAFTORDER#LATEST` -- full api-draft-order.json equivalent
   - `PK=SEASON#{id}, SK=ENRICHED_WAIVERS#LATEST` -- full waiver-wire-page.json equivalent

4. **No progressive checksumming.** Run full enrichment every time. At $0/month on free tier, optimization is waste.

5. **No version history.** Overwrite `#LATEST` items in place. Static JSON files in `dashboard/frontend/public/` serve as the rollback.

6. **No in-memory cache tier.** DynamoDB reads only. Lambda cold starts make in-memory caching pointless for a daily cron.

**SAM template addition:**
```yaml
EnrichmentFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: enrichment_lambda/
    Handler: app.lambda_handler
    Runtime: python3.11
    Architectures:
      - arm64
    Timeout: 900
    MemorySize: 1024
    Layers:
      - !Ref PandasNumpyLayer
    Environment:
      Variables:
        TABLE_NAME: !Ref DashboardDataTable
    Policies:
      - DynamoDBCrudPolicy:
          TableName: !Ref DashboardDataTable
    Events:
      DailyEnrichment:
        Type: Schedule
        Properties:
          Schedule: cron(0 10 * * ? *)  # 10 AM UTC daily (after ingestion)
          Description: Run enrichment pipeline daily
          Enabled: true
```

**Acceptance criteria:**
- Lambda invocation produces all 7 ENRICHED_*#LATEST items in DynamoDB
- ENRICHED_TRADES#LATEST JSON structure matches current `/dashboard/frontend/public/api-trades.json` schema
- ENRICHED_TEAMS#LATEST JSON structure matches current `api-teams.json` schema
- All 7 enriched items have valid JSON with correct data
- Trade margin calculations match existing pipeline output (spot-check 5 trades)
- Lambda completes within 15 minutes (900s timeout)
- CloudWatch logs show successful completion with item counts

---

#### Task 2.2: Build Trades Endpoint (DynamoDB Read)
- **Owner:** sde-pipeline
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** Task 2.1
- **Sprint:** 4

**Files affected:**
- `/backend-api/fantasy-backend/dashboard_api/app.py`

**Description:**
Rewrite `handle_trades()` in the Dashboard API Lambda to read from DynamoDB instead of calling Sleeper API live. This is now a simple GetItem call.

**Implementation:**
```python
def handle_trades():
    season = get_season_param(event)  # default: season_3
    result = table.get_item(Key={'PK': f'SEASON#{season}', 'SK': 'ENRICHED_TRADES#LATEST'})
    item = result.get('Item')
    if not item:
        return cors_response(404, {'error': 'No enriched trade data found'})
    return cors_response(200, json.loads(item['Data']))
```

**Acceptance criteria:**
- `GET /api/trades` returns enriched trade data from DynamoDB
- Response JSON matches the schema of current `api-trades.json`
- Response time < 500ms (DynamoDB single-item read)
- Returns 404 with clear error if enriched data not yet populated
- `curl` smoke test passes

---

#### Task 2.3: Build Teams Endpoint (DynamoDB Read)
- **Owner:** sde-frontend
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** Task 2.1
- **Sprint:** 4

**Files affected:**
- `/backend-api/fantasy-backend/dashboard_api/app.py`

**Description:**
Add `handle_teams()` route to Dashboard API. Same pattern as trades: single DynamoDB GetItem for `ENRICHED_TEAMS#LATEST`.

**Acceptance criteria:**
- `GET /api/teams` returns enriched team/manager data from DynamoDB
- Response JSON matches the schema of current `api-teams.json`
- Response time < 500ms
- `curl` smoke test passes

---

#### Task 2.4: Build Stats Endpoint (DynamoDB Read)
- **Owner:** sde-frontend
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** Task 2.1
- **Sprint:** 4

**Files affected:**
- `/backend-api/fantasy-backend/dashboard_api/app.py`

**Description:**
Add `handle_stats()` route to Dashboard API. Single DynamoDB GetItem for `ENRICHED_STATS#LATEST`.

**Acceptance criteria:**
- `GET /api/stats` returns enriched stats summary from DynamoDB
- Response JSON matches the schema of current `api-stats-summary.json`
- Response time < 500ms
- `curl` smoke test passes

---

#### Task 2.5: Frontend API Client -- Mock Mode
- **Owner:** sde-frontend
- **Complexity:** M
- **Priority:** P1
- **Dependencies:** None (uses mock responses based on existing static JSON schemas)
- **Sprint:** 3-4 (parallel with backend work)

**Files affected:**
- `/dashboard/frontend/src/services/api.ts`
- NEW: `/dashboard/frontend/src/services/api-client.ts` (new Lambda API client)

**Description:**
Build the Lambda API client in parallel with backend development. Start with mock mode that returns the same data as the static JSON files, then switch to real Lambda URLs when endpoints are ready.

**Implementation approach:**
1. Create `api-client.ts` with functions for each endpoint: `fetchTrades()`, `fetchTeams()`, `fetchStats()`, `fetchStandings()`, `fetchPlayoffs()`, `fetchDraftOrder()`, `fetchWaivers()`
2. Each function accepts a `baseUrl` parameter (API Gateway URL)
3. Add `USE_LAMBDA_API` environment variable toggle (simple boolean, not Lambda@Edge canary)
4. In mock mode, functions return data from existing static JSON files
5. In live mode, functions call the API Gateway endpoints
6. Update existing React Query hooks to use the new client

**Acceptance criteria:**
- `api-client.ts` exports 7 fetch functions matching the 7 endpoints
- `USE_LAMBDA_API=false` (default): all functions return static JSON data (existing behavior)
- `USE_LAMBDA_API=true`: all functions call API Gateway URLs
- Existing dashboard pages work identically in mock mode
- No breaking changes to React components

---

### Phase 3: Remaining Endpoints + Integration (Weeks 9-12)

#### Task 3.1: Build Standings Endpoint (DynamoDB Read)
- **Owner:** sde-frontend
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** Task 2.1
- **Sprint:** 5

**Files affected:**
- `/backend-api/fantasy-backend/dashboard_api/app.py`

**Description:**
Rewrite `handle_standings()` to read from `ENRICHED_STANDINGS#LATEST` instead of calling Sleeper API live.

**Acceptance criteria:**
- `GET /api/standings` returns enriched standings from DynamoDB
- Response JSON matches the schema of current `api-standings.json`
- Response time < 500ms
- `curl` smoke test passes

---

#### Task 3.2: Build Playoff Scenarios Endpoint (DynamoDB Read)
- **Owner:** sde-frontend
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** Task 2.1
- **Sprint:** 5

**Files affected:**
- `/backend-api/fantasy-backend/dashboard_api/app.py`

**Description:**
Add `handle_playoffs()` route. Single DynamoDB GetItem for `ENRICHED_PLAYOFF#LATEST`.

**Acceptance criteria:**
- `GET /api/playoffs` returns enriched playoff scenario data from DynamoDB
- Response JSON matches the schema of current `api-playoff-scenarios.json`
- Response time < 500ms
- `curl` smoke test passes

---

#### Task 3.3: Build Draft Order Endpoint (DynamoDB Read)
- **Owner:** sde-infra
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** Task 2.1
- **Sprint:** 5

**Files affected:**
- `/backend-api/fantasy-backend/dashboard_api/app.py`

**Description:**
Add `handle_draft_order()` route. Single DynamoDB GetItem for `ENRICHED_DRAFTORDER#LATEST`.

**Acceptance criteria:**
- `GET /api/draft-order` returns enriched draft order data from DynamoDB
- Response JSON matches the schema of current `api-draft-order.json`
- Response time < 500ms
- `curl` smoke test passes

---

#### Task 3.4: Build Waivers Endpoint (DynamoDB Read)
- **Owner:** sde-infra
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** Task 2.1
- **Sprint:** 5

**Files affected:**
- `/backend-api/fantasy-backend/dashboard_api/app.py`

**Description:**
Rewrite `handle_waivers()` to read from `ENRICHED_WAIVERS#LATEST` instead of calling Sleeper API live.

**Acceptance criteria:**
- `GET /api/waivers` returns enriched waiver wire data from DynamoDB
- Response JSON matches the schema of current `waiver-wire-page.json`
- Response time < 500ms
- `curl` smoke test passes

---

#### Task 3.5: Frontend Cutover -- Wire to Lambda API
- **Owner:** sde-frontend
- **Complexity:** M
- **Priority:** P0
- **Dependencies:** Tasks 2.2-2.4, 3.1-3.4 (all endpoints must be live)
- **Sprint:** 6

**Files affected:**
- `/dashboard/frontend/src/services/api.ts`
- `/dashboard/frontend/src/services/api-client.ts`
- `/dashboard/frontend/.env` (or `.env.production`)

**Description:**
Switch the frontend from static JSON to the Lambda API. This is a simple env var toggle, not a canary release.

**Implementation:**
1. Set `VITE_USE_LAMBDA_API=true` in environment
2. Set `VITE_API_BASE_URL=https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod` in environment
3. Deploy frontend
4. Verify all 6 dashboard pages load correctly from Lambda API
5. If anything breaks, set `VITE_USE_LAMBDA_API=false` and redeploy (instant rollback to static JSON)

**Acceptance criteria:**
- All 6 dashboard pages load correctly with `USE_LAMBDA_API=true`
- Overview page: trades table, stats summary, team cards all render
- Standings page: division tables render with correct data
- Playoff Scenarios page: Monte Carlo results render
- Draft Order page: projections render
- Waiver Wire page: all 4 metric cards render
- Rollback test: setting `USE_LAMBDA_API=false` restores static JSON behavior within one deploy

---

#### Task 3.6: Smoke Testing via curl
- **Owner:** sde-pipeline
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** All endpoint tasks (2.2-2.4, 3.1-3.4)
- **Sprint:** 6

**Files affected:**
- NEW: `/backend-api/fantasy-backend/smoke-test.sh`

**Description:**
Manual smoke testing script that curls each endpoint and validates the response. Replaces the removed Locust load testing task. This is a 12-user hobby project -- a shell script is appropriate.

**Implementation:**
```bash
#!/bin/bash
BASE_URL="${1:-https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod}"
ENDPOINTS=("trades" "teams" "stats" "standings" "playoffs" "draft-order" "waivers")

for endpoint in "${ENDPOINTS[@]}"; do
  echo -n "Testing /api/$endpoint... "
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/$endpoint")
  if [ "$STATUS" = "200" ]; then
    echo "OK (${STATUS})"
  else
    echo "FAIL (${STATUS})"
  fi
done
```

**Acceptance criteria:**
- `smoke-test.sh` curls all 7 endpoints
- All return HTTP 200
- Each response is valid JSON (pipe through `jq .` without error)
- Script runs in < 30 seconds total

---

#### Task 3.7: Update Dashboard API Router for All Endpoints
- **Owner:** sde-pipeline
- **Complexity:** S
- **Priority:** P1
- **Dependencies:** Tasks 2.2-2.4, 3.1-3.4
- **Sprint:** 5

**Files affected:**
- `/backend-api/fantasy-backend/dashboard_api/app.py`

**Description:**
Update the `lambda_handler` router in `app.py` to include all 7 enriched endpoints. Remove the old Sleeper-API-direct code paths. Add proper error handling and the health endpoint.

**New route table:**
```python
ROUTES = {
    '/api/trades':      ('ENRICHED_TRADES#LATEST',      'api-trades'),
    '/api/teams':       ('ENRICHED_TEAMS#LATEST',        'api-teams'),
    '/api/stats':       ('ENRICHED_STATS#LATEST',        'api-stats'),
    '/api/standings':   ('ENRICHED_STANDINGS#LATEST',    'api-standings'),
    '/api/playoffs':    ('ENRICHED_PLAYOFF#LATEST',      'api-playoffs'),
    '/api/draft-order': ('ENRICHED_DRAFTORDER#LATEST',   'api-draft-order'),
    '/api/waivers':     ('ENRICHED_WAIVERS#LATEST',      'api-waivers'),
}
```

**Acceptance criteria:**
- All 7 routes return enriched data from DynamoDB
- `/api/health` endpoint still works
- Old Sleeper-API-direct code removed from `app.py`
- 404 response for unknown paths lists available endpoints
- CORS headers present on all responses

---

## Dependency Graph

```
Phase 1 (Foundation)
====================

  1.1 DynamoDB Provisioned ──┐
                              ├──> 1.2 Validate Ingestion
                              ├──> 1.3 Valuation Ingestion ──────┐
                              ├──> 1.4 Team Mapping Upload ──────┤
                              └──> 1.5 Pick Mapping Upload ──────┤
                                                                  │
  1.6 Lambda Layer (pandas) ─────────────────────────────────────┤
                                                                  │
                                                                  v
Phase 2 (Enrichment + Endpoints)                                  │
====================================                              │
                                                                  │
  2.1 Enrichment Lambda (XL) <═══════════════════════════════════╝
       │
       ├──> 2.2 Trades Endpoint (sde-pipeline)
       ├──> 2.3 Teams Endpoint (sde-frontend)
       ├──> 2.4 Stats Endpoint (sde-frontend)
       │
       │    2.5 Frontend API Client (mock) ── runs parallel, no dependency on 2.1
       │
       v
Phase 3 (Remaining Endpoints + Integration)
============================================

  2.1 ──> 3.1 Standings Endpoint (sde-frontend)
  2.1 ──> 3.2 Playoff Endpoint (sde-frontend)
  2.1 ──> 3.3 Draft Order Endpoint (sde-infra)
  2.1 ──> 3.4 Waivers Endpoint (sde-infra)

  All endpoints ──> 3.5 Frontend Cutover
  All endpoints ──> 3.6 Smoke Testing
  2.2-3.4       ──> 3.7 Router Update
```

**Critical path:** 1.1 --> 1.3 --> 2.1 --> 2.2 --> 3.5

The Enrichment Lambda (2.1) is the single highest-risk item. It blocks all 7 endpoints. All Phase 1 data ingestion tasks must complete before 2.1 can start.

---

## Team Allocation

### Sprint-by-Sprint Breakdown

#### Sprint 1 (Weeks 1-2)

| Engineer | Task | Complexity | Notes |
|----------|------|------------|-------|
| sde-infra | 1.1 DynamoDB Provisioned Switch | S | Day 1 task |
| sde-infra | 1.2 Validate Ingestion | S | Depends on 1.1 |
| sde-infra | 1.3 Valuation Ingestion (start) | M | Critical path, start immediately after 1.1 |
| sde-infra | 1.6 Lambda Layer Build | M | Can run parallel with 1.3 |
| sde-pipeline | Research: Map pipeline stages to Lambda | -- | Prep work for Task 2.1. Read stages 2-5, identify what to port. |
| sde-frontend | Research: Audit static JSON schemas | -- | Document exact JSON shapes for all 7 files in `public/`. Needed for API client. |

#### Sprint 2 (Weeks 3-4)

| Engineer | Task | Complexity | Notes |
|----------|------|------------|-------|
| sde-infra | 1.3 Valuation Ingestion (finish) | M | Complete and test |
| sde-infra | 1.4 Team Mapping Upload | S | Quick task |
| sde-infra | 1.5 Pick Mapping Upload | S | Quick task |
| sde-pipeline | 2.1 Enrichment Lambda (start) | XL | Begin with trade enrichment (stages 2-4) |
| sde-frontend | 2.5 Frontend API Client (start) | M | Build client with mock mode |

#### Sprint 3 (Weeks 5-6)

| Engineer | Task | Complexity | Notes |
|----------|------|------------|-------|
| sde-pipeline | 2.1 Enrichment Lambda (continue) | XL | Add waiver, standings, playoff, draft order enrichment |
| sde-frontend | 2.5 Frontend API Client (finish) | M | Complete mock mode, test all pages |
| sde-infra | Support: Lambda Layer debugging | -- | Available to help with packaging issues |

#### Sprint 4 (Weeks 7-8)

| Engineer | Task | Complexity | Notes |
|----------|------|------------|-------|
| sde-pipeline | 2.1 Enrichment Lambda (finish) | XL | Final testing, all 7 enriched items |
| sde-pipeline | 2.2 Trades Endpoint | S | First endpoint, template for others |
| sde-frontend | 2.3 Teams Endpoint | S | Follow trades pattern |
| sde-frontend | 2.4 Stats Endpoint | S | Follow trades pattern |
| sde-infra | Testing support | -- | Help validate DynamoDB data |

#### Sprint 5 (Weeks 9-10)

| Engineer | Task | Complexity | Notes |
|----------|------|------------|-------|
| sde-frontend | 3.1 Standings Endpoint | S | |
| sde-frontend | 3.2 Playoff Endpoint | S | |
| sde-infra | 3.3 Draft Order Endpoint | S | |
| sde-infra | 3.4 Waivers Endpoint | S | |
| sde-pipeline | 3.7 Router Update | S | Consolidate all routes |

#### Sprint 6 (Weeks 11-12)

| Engineer | Task | Complexity | Notes |
|----------|------|------------|-------|
| sde-frontend | 3.5 Frontend Cutover | M | The big toggle flip |
| sde-pipeline | 3.6 Smoke Testing | S | curl all endpoints |
| sde-infra | Production monitoring | -- | Watch CloudWatch during cutover |

### Workload Summary

| Engineer | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 | Sprint 5 | Sprint 6 | Total Tasks |
|----------|----------|----------|----------|----------|----------|----------|-------------|
| sde-infra | 1.1, 1.2, 1.3(s), 1.6 | 1.3(f), 1.4, 1.5 | Support | Support | 3.3, 3.4 | Monitor | 7 tasks |
| sde-pipeline | Research | 2.1(s) | 2.1(c) | 2.1(f), 2.2 | 3.7 | 3.6 | 5 tasks |
| sde-frontend | Research | 2.5(s) | 2.5(f) | 2.3, 2.4 | 3.1, 3.2 | 3.5 | 7 tasks |

**(s)=start, (c)=continue, (f)=finish*

No engineer is idle for more than 1 sprint. sde-frontend is productive from Sprint 1 (research) through Sprint 6 (cutover).

---

## DynamoDB Schema (Enriched Data)

### Existing PK/SK Patterns (unchanged)

```
PK: SEASON#season_2          SK: TRADE#2025-11-18#1296312256438497280
PK: SEASON#season_3          SK: WAIVER#2025-12-05#1298765432100000000
PK: SEASON#season_3          SK: STANDINGS#CURRENT
PK: SEASON#season_3          SK: MATCHUPS#WEEK#14
PK: SEASON#season_3          SK: METADATA
PK: NFL_STATS#2025           SK: WEEK#14
```

### New Items (added by this migration)

```
-- Reference data (Task 1.3-1.5)
PK: SEASON#season_3          SK: VALUATIONS#LATEST
PK: REFERENCE                SK: TEAM_IDENTITY_MAPPING
PK: REFERENCE                SK: PICK_ORIGIN_MAPPING_2025
PK: REFERENCE                SK: DRAFT_ORDER_2026

-- Enriched outputs (Task 2.1)
PK: SEASON#season_3          SK: ENRICHED_TRADES#LATEST
PK: SEASON#season_3          SK: ENRICHED_TEAMS#LATEST
PK: SEASON#season_3          SK: ENRICHED_STATS#LATEST
PK: SEASON#season_3          SK: ENRICHED_STANDINGS#LATEST
PK: SEASON#season_3          SK: ENRICHED_PLAYOFF#LATEST
PK: SEASON#season_3          SK: ENRICHED_DRAFTORDER#LATEST
PK: SEASON#season_3          SK: ENRICHED_WAIVERS#LATEST

-- (Also for season_2 after backfill)
PK: SEASON#season_2          SK: ENRICHED_TRADES#LATEST
...etc
```

### Item Structure (Enriched Items)

Each enriched item has this structure:

```json
{
  "PK": "SEASON#season_3",
  "SK": "ENRICHED_TRADES#LATEST",
  "EntityType": "enriched_trades",
  "Season": "season_3",
  "Data": "<JSON string matching api-trades.json schema>",
  "EnrichedAt": "2026-02-12T10:00:00Z",
  "EnrichmentVersion": "1.0",
  "ItemCount": 87,
  "UpdatedAt": "2026-02-12T10:00:00Z"
}
```

The `Data` attribute contains the full JSON payload as a string. The Dashboard API Lambda reads this item, parses `Data`, and returns it to the frontend. This keeps the API response schema identical to the current static JSON files.

**DynamoDB item size consideration:** The largest payload is `api-trades.json` at ~120KB per season. DynamoDB's max item size is 400KB. All items are well within limits.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Enrichment Lambda exceeds 15-min timeout | Medium | High | Split enrichment into sub-tasks (trades first, then waivers, etc.). Monitor CloudWatch duration. |
| DynastyProcess CSV format changes | Low | High | Enrichment Lambda validates CSV schema before processing. Log warnings on schema drift. |
| Pandas/NumPy layer too large | Low | Medium | Fall back to container image deployment (Task 1.6 already accounts for this). |
| Enriched JSON exceeds 400KB DynamoDB limit | Low | Medium | Compress with gzip before storing. Or split into multiple items (e.g., `ENRICHED_TRADES#LATEST#PART1`). |
| Pipeline logic drift between local and Lambda | Medium | Medium | Port pipeline code as-is. Do not refactor during migration. Validate outputs match. |
| API Gateway 30s timeout hit on cold start | Low | Low | Pre-computed data means API reads are <100ms. Cold start only affects first request. |
| Frontend schema mismatch after cutover | Medium | High | Task 2.5 mock mode validates schemas before cutover. Smoke test (3.6) catches mismatches. |

---

## Cost Model

### Monthly Cost Estimate: $0.00 (AWS Free Tier)

| Service | Usage | Free Tier Allowance | Overage |
|---------|-------|---------------------|---------|
| Lambda | ~90 invocations/month (daily enrichment + API calls) + ~3,000 API requests | 1M requests, 400K GB-seconds | $0 |
| DynamoDB | ~170MB storage, ~100 WCU/day, ~3,000 RCU/day | 25GB storage, 25 RCU, 25 WCU (provisioned) | $0 |
| API Gateway | ~3,000 requests/month | 1M requests/month (12 months) | $0 |
| CloudWatch | ~50MB logs/month | 5GB ingestion, 5GB storage | $0 |
| S3 | ~50MB static assets | 5GB storage, 20K GET, 2K PUT | $0 |

**Key action items for $0 cost:**
1. Task 1.1 switches DynamoDB to PROVISIONED mode (free tier only applies to provisioned, not on-demand)
2. Enrichment Lambda runs 1x/day (not hourly) -- 30 invocations/month, well under 1M limit
3. Dashboard API Lambda handles ~100 requests/day from 12 users -- 3,000/month, well under 1M limit

**Comparison to current cost:** The project currently costs $0/month (static JSON on Vercel). This migration maintains that $0 cost while adding dynamic data capabilities.

---

## Appendix: Removed Scope (SDM Condition 4)

The following items from v1 are explicitly out of scope:

1. **Lambda@Edge canary release** -- Replaced by `VITE_USE_LAMBDA_API` env var toggle. Rollback = set to `false` and redeploy. 12 users do not need percentage-based rollouts.

2. **Locust load testing** -- Replaced by `smoke-test.sh` (Task 3.6). 12 users generating ~100 requests/day do not need load testing infrastructure.

3. **Progressive enrichment checksumming** -- Enrichment Lambda runs full enrichment every time. The compute cost is ~$0 (free tier covers it). Checksumming to skip unchanged data adds complexity for zero cost savings.

4. **7-day version history for enriched data** -- Enriched items are overwritten in place (`#LATEST`). The static JSON files in `dashboard/frontend/public/` serve as the rollback. If enrichment produces bad data, flip `USE_LAMBDA_API=false` and the frontend reverts to static JSON.

5. **In-memory Lambda cache tier** -- The Enrichment Lambda runs daily as a cron job. Lambda containers are recycled between invocations, making in-memory caching useless. The Dashboard API Lambda reads from DynamoDB (single-digit ms latency). No cache layer needed.

---

## Approval Request

This Sprint Plan v2 addresses all 6 SDM conditions:

- [x] Condition 1 (BLOCKING): Architecture aligned to pre-computed enrichment
- [x] Condition 2 (BLOCKING): Missing dependency tasks added (1.3, 1.4, 1.5)
- [x] Condition 3 (BLOCKING): Team allocation rebalanced (sde-frontend has 7 tasks, no one idle >1 sprint)
- [x] Condition 4 (REQUIRED): Over-engineering cut (5 items removed)
- [x] Condition 5 (REQUIRED): DynamoDB schema uses existing `SEASON#{id}` PK with `ENRICHED_*#LATEST` SK prefixes
- [x] Condition 6 (ADVISORY): Lambda Layer task added (1.6) with container image fallback

**Requesting SDM final approval to begin Sprint 1 execution.**
