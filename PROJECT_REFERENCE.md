# Trade Analysis Dashboard - Complete Project Reference

## What This Project Is

A **fantasy football dynasty league analytics platform** called **Dynasuiiii Analytics**. It pulls data from the Sleeper API, runs it through a multi-stage Python ETL pipeline, generates static JSON files, and serves them via a React/TypeScript dashboard. The league has 12 teams across 2 seasons (Season 2 = 2024 historical, Season 3 = 2025 active).

**GitHub repo:** `github.com/capitanlandr/trade-analysis-dashboard`

---

## Production URLs

| Environment | URL | How It Deploys |
|---|---|---|
| **AWS CloudFront (Primary)** | `https://d137gsvp1einvh.cloudfront.net` | GitHub Actions -> S3 -> CloudFront |
| **Vercel (Backup)** | `https://dynasuiiiianalytics.vercel.app` | Automatic on `git push` to main |

**AWS Resources:**
- S3 Bucket: `dynasuiiii-website`
- CloudFront Distribution ID: `EL6SCNZ7VJGN2`
- Region: `us-east-1`
- AWS Account: `216571348281`

**Lambda API (backend-api):**
- API Gateway: `https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod/api/`
- Lambda Function: `fantasy-backend-DashboardApiFunction-fZRCWacynkMU`
- DynamoDB Table: `fantasy-dashboard-data`
- SAM Stack: `fantasy-backend`

---

## Architecture Overview

```
                     Sleeper API
                         |
          +--------------+--------------+
          |                             |
   Python Pipeline               Ingestion Lambda
   (Stages 0-12)               (Hourly -> DynamoDB;
                                 DISABLED 2026-07-27)
          |                             |
   Static JSON Files            Dashboard API Lambda
          |                        (5 endpoints)
   Vite Build (dist/)                  |
          |                     [Future: frontend
   +------+------+              reads from API]
   |             |
  S3/CF        Vercel
  (Primary)    (Backup)
```

**Current state:** The frontend reads from static JSON files baked into the Vite build at `dashboard/frontend/public/`. The backend-api Lambda + DynamoDB layer exists but the frontend does not consume it yet -- that's the AWS migration in progress.

---

## League Configuration

| Property | Season 2 (Historical) | Season 3 (Active) |
|---|---|---|
| League ID | `1180814327660371968` | `1312166810505719808` |
| Year | 2024 | 2025 |
| Status | `static` (immutable) | `active` (daily updates) |
| Teams | 12 | 12 |

Managed in: `pipeline/config/seasons.yaml`

---

## Directory Structure & File Reference

### Root Level

| File | Purpose |
|---|---|
| `update_dashboard.py` | **Master orchestrator.** Runs all pipeline stages, copies JSON to frontend, git commits + pushes. Supports `--dry-run` and `--skip-git`. |
| `update_weekly_standings.py` | Standalone script to update standings data only. |
| `refresh_local_data.py` | Quick local data refresh for development. |
| `deploy-to-aws.sh` | Manual AWS deploy: builds frontend, syncs to S3 (`dynasuiiii-website`), invalidates CloudFront (`EL6SCNZ7VJGN2`). |
| `dev.sh` | Starts local dev server on port 5173. Checks for port conflicts. |
| `setup.sh` | Initial project setup (install deps). |
| `setup-hooks.sh` | Git hooks configuration. |
| `restart_dev.sh` | Kill and restart the dev server. |
| `vercel.json` | Vercel config: static build from `dashboard/frontend/dist`, SPA fallback route. |
| `package.json` | Root monorepo package. Scripts proxy into `dashboard/backend` and `dashboard/frontend`. Only dev dep is `concurrently`. |
| `bucket-policy.json` | S3 bucket policy for CloudFront OAI access. |
| `cloudfront-config.json` | CloudFront distribution configuration snapshot. |
| `cloudfront-details.txt` | CloudFront resource IDs quick reference. |
| `payload.json` | Test payload for Lambda invocations. |
| `.gitignore` | Ignores: `node_modules`, build output, `.env`, pipeline intermediates (`backups/`, `logs/`, `metrics/`, `__pycache__`), generated dashboard JSON (`api-*.json`), root-level data duplicates, and sensitive docs. |
| `LICENSE` | MIT license. |

Note: Root-level data files (CSVs, JSONs) were removed in June 2026. Canonical copies live in `pipeline/`. Debug/test scripts moved to `scripts/`.

---

## `dashboard/` - Frontend Application

### `dashboard/frontend/` - React + TypeScript + Vite

**Tech stack:** React 18.2, TypeScript 5, Vite 5, Tailwind CSS 3, TanStack React Query 5, TanStack React Table 8, React Router 6, Chart.js 4, date-fns, Lucide icons, socket.io-client (installed but for future real-time features).

#### Config Files

| File | Purpose |
|---|---|
| `package.json` | Frontend deps. Build: `tsc && vite build`. Dev: `vite` (port 5173). |
| `vite.config.ts` | React plugin, vendor chunk splitting (react, react-dom, react-router-dom, @tanstack/react-query). |
| `tsconfig.json` | Target ES2020, strict mode. |
| `tailwind.config.js` | Custom colors (primary blue, success green, danger red), custom breakpoint `xs: 475px`. |
| `postcss.config.js` | Tailwind + Autoprefixer. |
| `.env` / `.env.example` | `VITE_DRIVE_FOLDER_ID` for Google Drive archive embed, `VITE_API_BASE_URL`. |
| `index.html` | Entry point with `<div id="root">` and Vite module script. |

#### `src/` Source Code

| File | Purpose |
|---|---|
| `main.tsx` | React entry point. Renders `<App />` in StrictMode. |
| `App.tsx` | Root component. Sets up React Router, QueryClientProvider, ErrorBoundary. Defines all 6 routes nested under `DashboardLayout`. |
| `index.css` | Global Tailwind imports and base styles. |

#### `src/pages/` - 6 Dashboard Pages

| Page | Route | What It Shows |
|---|---|---|
| `Overview.tsx` | `/` | Key metrics cards (total trades, avg margin), league leaders, top performers, manager rankings table, recent trades table (last 10). |
| `Standings.tsx` | `/standings` | Division standings tables with W-L-T records, playoff status badges (Clinched Bye/Division/Playoff/Eliminated), team schedule modal on click. |
| `PlayoffScenarios.tsx` | `/playoff-scenarios` | Monte Carlo simulation results (10,000 runs). Shows playoff %, division winner %, bye week % for each team. Color-coded probabilities. |
| `DraftOrderProjection.tsx` | `/draft-order` | 2026 draft order by round (1-4). Shows original owner, current owner, traded status. Distinguishes locked vs pending/uncertain picks with scenarios. |
| `WaiverWireAnalysis.tsx` | `/waiver-wire` | 4 metric cards (Churn Index, Efficiency Score, Hit Rate, Timing Score) plus a filterable/sortable transactions table with pagination. |
| `CommishTiersArchive.tsx` | `/commish-tiers` | Embeds a Google Drive folder (commissioner power rankings history) via iframe. Requires `VITE_DRIVE_FOLDER_ID` env var. |

#### `src/components/` - Reusable Components

**Layout:**

| Component | Purpose |
|---|---|
| `Layout/DashboardLayout.tsx` | Main layout wrapper. Header with league name/ID/season, 6-tab navigation with active state, last-updated timestamp, footer. |

**Error Handling:**

| Component | Purpose |
|---|---|
| `ErrorBoundary/ErrorBoundary.tsx` | Full-page error boundary. Shows error details in dev, "Try Again" / "Reload Page" buttons. |
| `ErrorBoundary/ComponentErrorBoundary.tsx` | Component-level error boundary. Inline error display with retry, non-destructive. |

**Tables:**

| Component | Purpose |
|---|---|
| `Tables/RecentTradesTable.tsx` | Sortable, filterable trades list. Search by team/asset, team filter dropdown, date range, pagination (10/20/50/100). Opens TradeDetailModal on row click. |
| `Tables/SimpleManagerRankingsTable.tsx` | Manager stats table. Search by name, filter by min trades, performance tier (winners/losers). Sort by: realName, tradeCount, totalValueGained, winRate. |
| `Tables/DivisionTable.tsx` | Single division standings table. Sortable columns, playoff clinch indicators. |
| `Tables/ManagerRankingsTable.tsx` | Extended manager statistics view. |

**Modals:**

| Component | Purpose |
|---|---|
| `Modals/TradeDetailModal.tsx` | Trade breakdown popup. Shows winner at trade vs current, margin progression, asset-by-asset values for Team A vs Team B. |
| `Modals/TeamScheduleModal.tsx` | Team schedule viewer. Completed games (W/L/T with median indicators), upcoming games, points comparison. |

**UI Primitives:**

| Component | Purpose |
|---|---|
| `UI/LoadingSpinner.tsx` | Animated spinner (sm/md/lg sizes). |
| `UI/SkeletonLoader.tsx` | Skeleton placeholders: `CardSkeleton`, `MetricCardSkeleton`, `TableSkeleton`. |
| `UI/ErrorMessage.tsx` | Error display with icon + title + message + optional retry. |
| `UI/RetryButton.tsx` | Async retry button with loading state. |
| `UI/HostingBanner.tsx` | Dismissable banner showing dual hosting info (Vercel + CloudFront URLs). |
| `UI/SeasonFilter.tsx` | Multi-season filter dropdown for "All Seasons" or individual season selection. |
| `UI/LazyLoader.tsx` | Lazy loading wrapper component. |

**Archive:**

| Component | Purpose |
|---|---|
| `Archive/ArchiveHeader.tsx` | Archive page title and description. |
| `Archive/ArchiveInstructions.tsx` | Usage instructions with fallback Google Drive link. |
| `Archive/GoogleDriveEmbed.tsx` | Iframe embed of Google Drive folder. 1500ms loading timeout, sandboxed, error fallback. |

**Waiver Wire Metric Cards:**

| Component | Purpose |
|---|---|
| `WaiverWire/ChurnIndexCard.tsx` | Roster activity rate (%). Shows total adds/drops, league rankings. Team selector. |
| `WaiverWire/EfficiencyScoreCard.tsx` | FAAB spending effectiveness. Points-per-dollar metrics. |
| `WaiverWire/HitRateCard.tsx` | Waiver pick success rate broken down by tier (tier 1/2/3 hits + misses). |
| `WaiverWire/TimingScoreCard.tsx` | Strategic timing analysis (early vs late week pickups). |

#### `src/services/`

| File | Purpose |
|---|---|
| `api.ts` | Centralized data layer. `USE_STATIC_DATA = true` means it fetches from `/api-*.json` and `/waiver-wire-page.json` in `public/`. Exports: `api` object with `getTrades()`, `getTeams()`, `getStatsSummary()`, etc. Also exports React Query hooks: `useWaiverWireData()`, `useStandingsData()`, `usePlayoffScenariosData()`. Query config: 5-min stale time, 30-min GC time. |

#### `src/hooks/`

| File | Purpose |
|---|---|
| `useDebounce.ts` | `useDebounce<T>(value, delay)` for value debouncing. `useDebouncedCallback` for function debouncing. |
| `useRetry.ts` | Exponential backoff retry hook. Configurable max retries, delay, backoff multiplier. Returns `{ execute, isRetrying, retryCount, reset }`. |
| `useSeasonMetrics.ts` | Filters trades/teams by selected season. Recalculates league stats. Returns filtered data + season counts. |

#### `src/types/`

| File | Key Types |
|---|---|
| `index.ts` | `Trade`, `Team`, `LeagueStats`, `TradeData`, `FilterState`, `SeasonFilter`, `ApiResponse<T>` |
| `team.ts` | `Team`, `SortConfig`, `TeamFilters` |
| `standings.ts` | `StandingsTeam`, `WeeklyMatchup`, `Division`, `StandingsData` |
| `draft-order.ts` | `LockedPick`, `UncertainPick`, `DraftPick`, `ProgressiveDraftOrder`, type guards `isLockedPick()`, `isUncertainPick()` |
| `playoff-scenarios.ts` | `PlayoffScenario`, `PlayoffScenariosData` |
| `waiver-wire.ts` | `WaiverWireTransaction`, `ChurnMetric`, `EfficiencyMetric`, `HitRateMetric`, `TimingMetric`, `WaiverWireData` |
| `archive.ts` | `LoadingState`, `EmbedError`, prop types for archive components |

#### `src/config/`

| File | Purpose |
|---|---|
| `archive.ts` | Google Drive config. `getArchiveConfig()` reads `VITE_DRIVE_FOLDER_ID`, builds embed URL (`drive.google.com/embeddedfolderview?id={folderId}#list`). |

#### `dashboard/frontend/public/` - Static Data Files (Generated by Pipeline)

| File | Generated By | Contents |
|---|---|---|
| `api-trades.json` | `generate_dashboard_json_from_cumulative.py` | All trades with metadata, team info, asset breakdowns, margins, winners. |
| `api-teams.json` | `generate_dashboard_json_from_cumulative.py` | Team rankings: trade count, win rate, total value gained. |
| `api-stats-summary.json` | `generate_dashboard_json_from_cumulative.py` | League overview: total trades, avg margin, most active trader, date range. |
| `api-standings.json` | `fetch_standings.py` | Division standings, W-L-T records, weekly matchup schedules, median records. |
| `api-playoff-scenarios.json` | `simulate_playoff_scenarios.py` | Monte Carlo results: playoff/division/bye probabilities per team. |
| `api-draft-order.json` | `calculate_progressive_draft_order.py` | 2026 draft order by round with locked/pending picks and scenarios. |
| `waiver-wire-page.json` | `generate_waiver_wire_dashboard_json_from_cumulative.py` | All waiver transactions + churn/efficiency/hit-rate/timing metrics per manager. |
| `trades.json` | Copied from `pipeline/trades.json` | Cumulative multi-season raw trade data. |
| `cumulative_processed_waiver_transactions.json` | Copied from pipeline | Cumulative processed waiver transactions. |
| `playoff_scenarios_simulated.json` | `simulate_playoff_scenarios.py` | Raw simulation output. |

### `dashboard/backend.ARCHIVED/`

The original Node.js/Express backend has been archived. It's no longer used -- the frontend reads static JSON files instead. This was replaced by the Lambda-based `backend-api/`.

---

## `pipeline/` - Python ETL Pipeline

### Configuration

| File | Purpose |
|---|---|
| `config/default.yaml` | Main config: league ID, Sleeper API settings (timeout, retries, backoff), GitHub API settings (DynastyProcess values repo), valuation tiers (Early 1st = 5430, Mid 1st = 2558, Late 1st = 1232), storage paths, validation thresholds (max 10% zero values), logging config, performance settings (10 parallel workers, 24h cache TTL). |
| `config/seasons.yaml` | Multi-season config: season_2 (static, 2024), season_3 (active, 2025), pipeline behavior (cumulative files, backup-before-append, validation rules). |
| `config.py` | Configuration loader -- reads `default.yaml` and provides typed access. |
| `constants.py` | Enums: `PickTier`, `AssetType`, `TradeType`, `TradeStatus`, `OutputFiles`. Constants: draft dates, FAAB multiplier, API endpoints, validation thresholds. |
| `config/current_week.json` | Auto-updated current NFL week tracker. |

### Core Pipeline Stages

#### Stage 0: `scripts/detect_current_week.py`
Detects the current NFL week. Handles the Tuesday timing bug (Sleeper API reports wrong week on Tuesdays before data refresh).

#### Stage 1: `stage1_fetch_trades.py`
**Fetches all trade transactions from Sleeper API.**
- Multi-season: only processes active seasons (season_3).
- Incremental fetching via `last_fetch_timestamp` to avoid re-processing.
- Appends to cumulative `trades.json` with deduplication by transaction ID.
- Creates legacy `trades_raw.json` for backward compatibility.
- Retry: 5 attempts with exponential backoff (4s, 8s, 16s, 32s, 60s) + jitter.
- Output: `trades.json`, `trades_raw.json`

#### Stage 2: `stage2_extract_assets.py`
**Flattens trades into individual asset rows (one per asset per trade).**
- Extracts players (added/dropped), draft picks (with origin owner tracking), and FAAB budget.
- Uses `team_resolver` for roster ID -> username mapping across seasons.
- Fetches NFL player data from Sleeper for name resolution.
- Output: `asset_transactions.csv`

#### Stage 3: `stage3_cache_values.py`
**Fetches historical and current valuations for every traded asset.**

Value lookup strategy by asset type:
- **Players:** Historical value from DynastyProcess Git commits (closest date to trade). Current value from latest DynastyProcess CSV. Uses `value_2qb` column.
- **2025 Picks:** Pre-draft = tier value at trade time, player value now. Post-draft = player value for both.
- **2026 Picks:** DynastyProcess exact pick values using `draft_order_2026_progressive.json` for pick labels.
- **2027/2028 Picks:** Tiered values ("2027 Early 1st") based on team projections.

Output: `asset_values_cache.csv` (columns: asset_name, asset_type, trade_date, value_at_trade, value_current, value_source_at_trade, value_source_current, metadata)

#### Stage 4: `stage4_final.py`
**Aggregates asset values into complete trades. Calculates winners and margins.**

For 2-team trades:
- Sums values per team (then vs now).
- `margin_at_trade` = |team_a_value_then - team_b_value_then|
- `margin_current` = |team_a_value_now - team_b_value_now|
- `swing_margin` = margin_now - margin_then (how much the trade shifted)
- Determines `winner_at_trade`, `winner_current`, `swing_winner`.

For multi-team trades:
- Calculates net value per team, outputs to `3team_trades_analysis.json`.

Output: `league_trades_analysis_pipeline.csv`, `3team_trades_analysis.json`

#### Stage 5: `stage5_waiver_wire.py`
**Processes waiver wire and free agent transactions.**
- Same multi-season architecture as Stage 1.
- Incremental with deduplication.
- Historical value lookups via Git commits.
- Output: `cumulative_processed_waiver_transactions.json`

### Supporting Pipeline Stages (run via `scripts/`)

| Stage | Script | Purpose |
|---|---|---|
| 5a | `scripts/fetch_player_stats.py` | Fetches per-player NFL stats from Sleeper. |
| 5b | `scripts/fetch_lineup_data.py` | Fetches lineup/roster data for each week. |
| 6 | `analyze_2026_pick_ownership.py` | Analyzes current 2026 draft pick ownership and distributions. |
| 7 | `generate_playoff_bracket.py` | Generates playoff bracket scenarios. |
| 7a | `scripts/calculate_progressive_draft_order.py` | Calculates progressive 2026 draft order with locked/pending status. |
| 8 | `scripts/generate_dashboard_json_from_cumulative.py` | Generates `api-trades.json`, `api-teams.json`, `api-stats-summary.json` from cumulative files. Writes directly to `dashboard/frontend/public/`. |
| 9 | `scripts/generate_waiver_wire_dashboard_json_from_cumulative.py` | Generates `waiver-wire-page.json` with all 4 metric types (churn, efficiency, hit rate, timing). |
| 10 | `scripts/fetch_standings.py` | Fetches current standings from Sleeper. Generates `api-standings.json`. |
| 11 | `scripts/simulate_playoff_scenarios.py` | Monte Carlo playoff simulation (10,000 runs). Generates `api-playoff-scenarios.json`. |
| 12 | `scripts/generate_dashboard_json_from_cumulative.py` | Re-generates dashboard JSON with updated playoff data. |

### Utility Modules (`pipeline/utils/`)

| File | Purpose |
|---|---|
| `api_client.py` | Sleeper API HTTP client. Tenacity retry (5 attempts), exponential backoff (4-60s), jitter, rate limit handling (429 + Retry-After). Custom exceptions: `APIError`, `RateLimitError`, `TimeoutError`. |
| `backup.py` | `BackupManager` class. Creates timestamped backups (`stage1_trades_raw_YYYYMMDD_HHMMSS.json`). Auto-cleanup based on retention days (default 30). |
| `cumulative_file_manager.py` | `CumulativeFileManager` class. Atomic writes (temp file + rename). Transaction ID deduplication. Auto-backup before modification. File integrity validation. |
| `immutability_guard.py` | Prevents modification of static season data (season_2). Enforces append-only semantics on cumulative files. |
| `logging_config.py` | JSON-formatted structured logging. `OperationLogger` with context (season, operation, count, duration). Log rotation. |
| `metrics.py` | Local metrics collection. Saves to `metrics/run_YYYYMMDD_HHMMSS.json`. Records counts, durations, success/failure, numpy type conversion. |
| `season_config.py` | `SeasonConfiguration` class. Loads `seasons.yaml`, tracks active vs static seasons, updates fetch timestamps, validates operations. |
| `team_resolver.py` | `TeamResolver` class. Maps roster_id -> real_name/username/team_name. Handles team name changes across seasons. |
| `validators.py` | `StageValidator` class. Pre/post validation for each stage. Checks: API connectivity, file existence, format correctness, zero-value percentages (<10%), duplicate detection. |
| `week_config.py` | Week configuration utilities. |

### Other Pipeline Files

| File | Purpose |
|---|---|
| `pick_origin_mapping.py` | Static 2025 draft pick origin lookup. 12-team linear draft, explicit origin mapping to avoid Sleeper API confusion. `ROSTER_TO_OWNER`, `EXPLICIT_ORIGINS`, `PICK_ORIGIN_MAP`. |
| `health_check.py` | Pipeline health monitoring and diagnostics. |
| `fix_tyreek_value.py` | One-off data correction for specific player value issues. |

### Pipeline Data Files

| File | Purpose |
|---|---|
| `trades.json` | Cumulative multi-season trade data (source of truth). |
| `cumulative_processed_waiver_transactions.json` | Cumulative processed waiver transactions. |
| `draft_order_2026_progressive.json` | 2026 draft order with pick labels, locked/pending status. |
| `sleeper_rookie_draft_2025.csv` | 2025 rookie draft results with player-to-pick mapping. |
| `weekly_2026_pick_projections_expanded.csv` | Weekly team-based 2026 pick projections by round. |
| `output/trades_raw.json` | Legacy format trade output. |
| `output/asset_transactions.csv` | Stage 2 output. |
| `output/asset_values_cache.csv` | Stage 3 output. |
| `output/league_trades_analysis_pipeline.csv` | Stage 4 output. |
| `output/manager_rankings_pipeline.csv` | Manager ranking calculations. |
| `output/team_identity_mapping.csv` | Team identity resolution output. |

### Pipeline Tests (`pipeline/tests/`)

| File | Purpose |
|---|---|
| `conftest.py` | Pytest fixtures: `mock_trades_data`, `mock_dynasty_values`, `mock_asset_transactions`, `mock_cached_values`, `mock_multiteam_cached_values`, `mock_pick_projections`, `mock_draft_results`. |
| `test_stage3_valuations.py` | Tests for asset value caching and source selection logic. |
| `test_stage4_calculations.py` | Tests for margin, swing, and winner calculations. Covers: `TestTradeMarginCalculations`, `TestSwingCalculations`, `TestWinnerDetermination`. |
| `test_team_resolver.py` | Tests for roster ID -> team name resolution. |
| `test_season_config_properties.py` | Tests for season configuration loading and validation. |

---

## `backend-api/` - AWS Serverless Backend (Migration In Progress)

Built with **AWS SAM** (Serverless Application Model). Defines infrastructure in `template.yaml`.

### Infrastructure (`backend-api/fantasy-backend/template.yaml`)

**DynamoDB Table: `fantasy-dashboard-data`**
- Billing: **On-demand (`PAY_PER_REQUEST`)** as of 2026-07-27. See "Cost Posture" below -- it was previously provisioned and was costing ~$14/month.
- Primary key: `PK` (partition) + `SK` (sort).
- GSI1: Global secondary index for flexible queries. Projection: ALL.
- TTL enabled (attribute `TTL`). Point-in-time recovery **disabled**.
- Current size: ~692 items / ~8 MB (well inside the 25 GB always-free storage tier).

**DashboardApiFunction (Lambda):**
- Runtime: Python 3.11, arm64. 128 MB memory.
- Timeout: 30s.
- Trigger: API Gateway `ANY /api/{proxy+}`.

**IngestionFunction (Lambda):**
- Runtime: Python 3.11, arm64.
- Timeout: 900s (15 min), 512 MB memory.
- Trigger: EventBridge schedule `rate(1 hour)` -- **currently DISABLED** (see "Cost Posture").

**EnrichmentFunction (Lambda):**
- Runtime: Python 3.11, arm64. 1024 MB memory, 900s timeout.
- Uses the `PandasNumpyLayer` (pandas + numpy, built via `./build-layer.sh` -> `layers/pandas-numpy-layer.zip`).
- Reads raw DynamoDB data, runs pipeline stages 2-5, writes `ENRICHED_*#LATEST` items.
- Trigger: EventBridge schedule `cron(0 10 * * ? *)` (daily 10:00 UTC) -- **currently DISABLED**.

**PandasNumpyLayer:** `AWS::Serverless::LayerVersion`, ContentUri `layers/pandas-numpy-layer.zip`, python3.11 / arm64.

Note: a leftover `fantasy-backend-HelloWorldFunction-*` from the original SAM scaffold still exists in the account but is not referenced in `template.yaml`.

### `backend-api/fantasy-backend/dashboard_api/app.py` - API Lambda

5 endpoints, all fetch live from Sleeper API (no DynamoDB reads yet):

| Endpoint | What It Returns |
|---|---|
| `GET /api/health` | Status, lambda name, timestamp, available endpoints. |
| `GET /api/trades` | All trades across all weeks. Fetches users, rosters, trades from Sleeper. Sorted by date (newest first). |
| `GET /api/standings` | Current roster standings. Sorted by wins then points_for. |
| `GET /api/waivers` | Waiver + free agent transactions from week 1. |
| `GET /api/league-info` | League metadata: name, season, status, total_rosters. |

CORS enabled (all origins, GET + OPTIONS).

### `backend-api/fantasy-backend/ingestion_lambda/app.py` - Ingestion Lambda

Hourly scheduled Lambda that fetches Sleeper data and writes to DynamoDB.

**3 modes:** INCREMENTAL (active seasons only), BACKFILL (all seasons), CUSTOM (specified seasons).

**6 ingestion functions:**
1. `ingest_trades()` - PK: `SEASON#{id}`, SK: `TRADE#{date}#{trade_id}`
2. `ingest_waivers()` - PK: `SEASON#{id}`, SK: `WAIVER#{date}#{waiver_id}`
3. `ingest_matchups()` - PK: `SEASON#{id}`, SK: `MATCHUPS#WEEK#{week:02d}`
4. `ingest_nfl_stats()` - PK: `NFL_STATS#{year}`, SK: `WEEK#{week:02d}`
5. `ingest_standings()` - PK: `SEASON#{id}`, SK: `STANDINGS#CURRENT`
6. `ingest_league_info()` - PK: `SEASON#{id}`, SK: `METADATA`

Season config embedded + in `ingestion_lambda/seasons.yaml`.

### `backend-api/fantasy-backend/samconfig.toml`

SAM deploy config: stack name `fantasy-backend`, region `us-east-1`, cached parallel builds, warm containers for local testing.

### Tests

| File | Purpose |
|---|---|
| `tests/unit/test_handler.py` | Unit tests for Lambda handler (hello world baseline). |
| `tests/integration/test_api_gateway.py` | Integration tests against deployed API Gateway. Reads stack URL from CloudFormation outputs. |

---

## `.github/` - CI/CD & Templates

### Workflows

| File | Trigger | What It Does |
|---|---|---|
| `workflows/update-dashboard.yml` | Daily at 9 AM EST (cron `0 14 * * *`) + manual | **The main pipeline workflow.** Checks out repo, installs Python deps, runs `update_dashboard.py`, builds frontend, deploys to S3, invalidates CloudFront. Updates both Vercel (via git push) and AWS (via S3 sync). |
| `workflows/deploy-aws.yml` | Push to `main` (if `dashboard/frontend/**` or `pipeline/**` changed) + manual | Builds frontend, syncs to S3, invalidates CloudFront. Triggered on code changes only (not data updates). |
| `workflows/ci.yml` | Push to `main`/`develop`, PRs to `main` | 6 parallel jobs: test-backend, test-frontend, security-scan (Trivy), dependency-check (`npm audit`), code-quality (tsc + format check), integration-test (starts backend, runs frontend integration tests). Deploy preview on PRs. |

### Templates

| File | Purpose |
|---|---|
| `ISSUE_TEMPLATE/` | Issue templates for bug reports and feature requests. |
| `pull_request_template.md` | PR template with sections for description, type, testing, checklist. |

---

## `scripts/` - Utility Scripts

| File | Purpose |
|---|---|
| `bulletproof_rename_template.sh` | Safe find-and-replace template for bulk file renames. |
| `rename_waiver_files.sh` | Renames waiver wire output files to standardized names. |
| `deploy_aws.sh` | Portable AWS deploy script (uses env vars for bucket/distribution). |
| `debug_json_generation.py` | Debug utility for JSON output issues. |
| `verify_archive_implementation.js` | Node script to verify archive feature works. |
| `SAFE_FIND_REPLACE_GUIDE.md` | Guide for safely doing find/replace across the codebase. |

---

## `docs/` - Documentation

| File | Purpose |
|---|---|
| `2026_PICK_TRACKING_AND_WEEK_CONFIG_ANALYSIS.md` | Analysis of 2026 pick tracking logic and week configuration. |
| `LOGGING_SYSTEM.md` | Documentation of the structured JSON logging system. |
| `PHASE3_WHR_IMPLEMENTATION_SUMMARY.md` | Waiver Hit Rate (WHR) implementation summary. |
| `WAIVER_WIRE_COMPONENTS_DESIGN.md` | Design doc for the 4 waiver wire metric card components. |
| `WAIVER_WIRE_IMPLEMENTATION_PLAN.md` | Full implementation plan for waiver wire analysis feature. |
| `guides/` | Additional guide documents. |

---

## `plans/` - Architecture & Design Plans

| File | Purpose |
|---|---|
| `MULTI_SEASON_LEAGUE_ID_ARCHITECTURE.md` | Complete multi-season architecture spec (84KB). Covers cumulative file management, season tagging, immutability guards, and backward compatibility. |
| `UNIFIED_CUMULATIVE_MULTI_SEASON_ARCHITECTURE.md` | Unified approach to cumulative file handling across seasons (51KB). |
| `DRAFT_ORDER_SPECIFICATION.md` | Full spec for progressive draft order tracking (45KB). |
| `PROGRESSIVE_DRAFT_ORDER_TRACKING.md` | Draft order tracking implementation plan (33KB). |
| `SLEEPER_API_ANALYSIS_PLAN.md` | Analysis of Sleeper API capabilities and data extraction plan. |
| `SLEEPER_API_CAPABILITIES.md` | Documentation of all Sleeper API endpoints used. |
| `CURRENT_WEEK_IMPACT_ANALYSIS.md` | Impact analysis of current week detection on pipeline. |

---

## Markdown Documentation

**Root (active docs):**

| File | Purpose |
|---|---|
| `README.md` | Project overview, features, setup instructions, architecture diagram. |
| `QUICK_START.md` | Quick setup guide for new developers. |
| `CONTRIBUTING.md` | Contribution guidelines. |
| `CODEX_STEERING.md` | AI agent steering document. |
| `PROJECT_REFERENCE.md` | This file. Complete project reference. |
| `DEPLOYMENT.md` | Deployment procedures and environments. |
| `WEEKLY_UPDATE_GUIDE.md` | Guide for running weekly data updates. |
| `LAMBDA_ARCHITECTURE_GUIDE.md` | Architecture guide for the Lambda-based backend. |
| `DYNAMODB_SCHEMA_DESIGN.md` | DynamoDB table design with PK/SK patterns, GSI strategy, TTL, and access patterns. |
| `METRICS_DESIGN_PATTERN.md` | Design pattern for the metrics collection system. |
| `PLAYER_VALUE_CACHE_DESIGN.md` | Design for the player value caching layer. |
| `SLEEPER_API_AUDIT.md` | Audit of all Sleeper API usage across the codebase. |
| `REAL_TIME_DASHBOARD_ROADMAP.md` | Roadmap for real-time features (WebSockets, live updates). |
| `PRINCIPAL_ENGINEER_RECOMMENDATIONS.md` | Architecture recommendations and best practices. |

**`docs/setup/` (setup and configuration references):**

| File | Purpose |
|---|---|
| `AWS_LOCAL_DEVELOPMENT_GUIDE.md` | How to develop and test the Lambda backend locally. |
| `AWS_MIGRATION_GUIDE.md` | Guide for the Vercel -> AWS migration. |
| `GITHUB_ACTIONS_SETUP.md` | GitHub Actions setup guide. |
| `GITHUB_ACTIONS_FIX.md` | Fix documentation for GitHub Actions issues. |
| `CUSTOM_DOMAIN_OPTIONS.md` | Options for custom domain setup. |
| `VERCEL_DOMAIN_OPTIONS.md` | Vercel-specific domain configuration. |
| `TEST_SETUP.md` | Test environment setup instructions. |
| `URL_REFERENCE.md` | Quick reference for all production URLs and AWS resource IDs. |

**`docs/archive/` (historical, completed, or paused work):**

| File | Purpose |
|---|---|
| `IMPLEMENTATION_PLAN.md` | Original implementation plan for the dashboard (completed). |
| `IMPLEMENTATION_2026_EXACT_PICKS.md` | Implementation details for exact 2026 pick valuations (completed). |
| `MIGRATION_GUIDE.md` | Guide for migrating between versions/architectures (completed). |
| `SPRINT_1_EXECUTION_LOG.md` | Lambda migration sprint (paused). |
| `ARCHIVE_DEPLOYMENT_CHECKLIST.md` | Commish Tiers archive feature deployment (completed). |
| `ARCHIVE_LOADING_FIX.md` | Archive loading fix documentation (completed). |
| `COMMISH_TIERS_ARCHIVE_TESTING_GUIDE.md` | Archive feature testing guide (completed). |

---

## Data Flow Summary

### Daily Automated Flow (9 AM EST)

```
1. GitHub Actions triggers update-dashboard.yml
2. update_dashboard.py runs:
   a. Validates season config (seasons.yaml)
   b. Stage 0: Detect current NFL week
   c. Stage 1: Fetch new trades from Sleeper API (incremental, active seasons only)
   d. Stage 2: Extract individual assets from trades
   e. Stage 3: Fetch/cache valuations from DynastyProcess
   f. Stage 4: Calculate trade analysis (margins, winners, swings)
   g. Stage 5: Process waiver wire transactions
   h. Stage 5a-5b: Fetch player stats and lineup data
   i. Stage 6: Analyze 2026 pick ownership
   j. Stage 7-7a: Generate playoff bracket + draft order
   k. Stage 8: Generate dashboard JSON from cumulative files -> public/
   l. Stage 9: Generate waiver wire JSON -> public/
   m. Stage 10: Fetch current standings -> public/
   n. Stage 11: Run playoff simulations -> public/
   o. Stage 12: Re-generate dashboard JSON with playoff data
3. Copies cumulative files (trades.json, waiver transactions) to public/
4. Verifies all dashboard JSON files exist
5. Updates season metadata timestamps
6. git add + commit + push -> triggers Vercel deploy
7. Builds frontend (npm run build)
8. Syncs dist/ to S3 (assets: 1yr cache, HTML/JSON: 1hr cache)
9. Invalidates CloudFront cache
```

### On Code Push to `main`

```
1. ci.yml runs: lint, test, type-check, security scan, audit
2. deploy-aws.yml runs: build frontend, sync to S3, invalidate CloudFront
3. Vercel auto-deploys from git integration
```

---

## AWS Migration Status

**What exists and works:**
- S3 + CloudFront static site hosting (primary production).
- SAM-based Lambda + API Gateway + DynamoDB infrastructure deployed.
- Dashboard API Lambda serves 5 endpoints with live Sleeper data.

**Current production approach (as of June 2026):**
- Frontend reads **static JSON files** generated by the Python pipeline. This is the stable, daily-updated data path.
- Controlled by `VITE_USE_LAMBDA_API=false` in `.env` and `.env.production`.
- GitHub Actions runs the pipeline daily, builds the frontend, and deploys `dist/` to S3/CloudFront.

**Lambda migration — PAUSED:**
- The frontend code supports Lambda (`api-client.ts` has the toggle) but it is disabled in production.
- Lambda/DynamoDB data has diverged from pipeline output (different valuations, different trade counts).
- Do not enable `VITE_USE_LAMBDA_API=true` in production until Lambda data parity with the pipeline is verified.
- **The ingestion and enrichment schedules are now DISABLED**, so DynamoDB data is frozen as of 2026-07-27 and will go stale. Resuming the migration requires re-enabling both schedules and backfilling.
- `socket.io-client` is installed for future real-time features.
- `REAL_TIME_DASHBOARD_ROADMAP.md` outlines WebSocket plans.

---

## Cost Posture (audited 2026-07-27)

AWS account `216571348281`. The site is intended to run at $0/month. An audit on 2026-07-27 found one real charge and corrected it.

### The problem: provisioned DynamoDB capacity

`template.yaml` declared the table as `BillingMode: PROVISIONED` with 25 RCU / 25 WCU, **and** declared a second 25 RCU / 25 WCU on the `GSI1` index. The DynamoDB free tier covers **25 RCU + 25 WCU per account, not per table or per index**. The base table consumed the entire free allowance, so the GSI's capacity was fully billable:

| Item | Math | Cost |
|---|---|---|
| GSI1 reads | 25 RCU x 730 hrs x $0.00013 | ~$2.37/mo |
| GSI1 writes | 25 WCU x 730 hrs x $0.00065 | ~$11.86/mo |
| **Total** | | **~$14/mo (~$170/yr)** |

This was being paid on a table holding ~692 items / ~8 MB that **nothing reads** (the frontend uses static JSON).

### The fix

1. `BillingMode` changed to `PAY_PER_REQUEST` (on-demand) in `template.yaml`; both `ProvisionedThroughput` blocks removed. On-demand bills per request, and actual volume is ~453 Lambda requests/month, which rounds to $0.
2. Both EventBridge schedules set to `Enabled: false` in `template.yaml` (hourly ingestion, daily enrichment), since nothing consumes the table while the migration is paused.

Applied live on 2026-07-27 via CLI (`aws dynamodb update-table --billing-mode PAY_PER_REQUEST` and `aws events disable-rule` on both rules) because a full `sam deploy` would have rebuilt all three Lambdas plus the pandas/numpy layer for what is a config-only change. **The template was updated first**, so the next `sam deploy` reinforces this state rather than reverting it. CloudFormation's cached stack state will lag live state until that next deploy; this is harmless.

### Verified free-tier usage at time of audit

All line items reported by `aws freetier get-free-tier-usage` were **"Always Free"** type -- nothing here depends on the expiring 12-month tier.

| Service | Used | Limit | % |
|---|---|---|---|
| Lambda compute | 14,283 GB-sec | 400,000 | 3.6% |
| Lambda requests | 453 | 1,000,000 | 0.0% |
| DynamoDB storage | 0.01 GB | 25 GB | 0.0% |
| CloudWatch log storage | 0.01 GB | 5 GB | 0.2% |
| KMS requests | 4 | 20,000 | 0.0% |
| Glue catalog requests | 67 | 1,000,000 | 0.0% |

CloudFront (1 TB/mo transfer) and S3 (~2 MB in `dynasuiiii-website`) are nowhere near any limit.

### Known open items

- **Python 3.11 runtime is end-of-life.** All three Lambdas use `python3.11`, deprecated 2026-06-30. Function *creation* was disabled 2026-07-31 and **function updates are disabled after 2026-08-31**. Migrate to `python3.14` before that date or the stack becomes undeployable. `sam validate --lint` flags this (W2531) at template lines 83, 108, 139.
- **Cost Explorer requires a one-time console activation** -- it CANNOT be enabled via API or CLI. `aws ce get-cost-and-usage` returns `AccessDeniedException: User not enabled for cost explorer access` even though `personal-cli-user` holds `AdministratorAccess`, so this is an account-level service activation, not an IAM permissions gap. To enable: sign in to the AWS console as the account root or an admin, open **Billing and Cost Management -> Cost Explorer**, and click through the activation. Data becomes available within ~24 hours and cannot be backfilled beyond that point. Until then, use the Free Tier API and Pricing API (see "Re-running this audit" above). Note the **AWS Budgets API works today** (`aws budgets describe-budgets --account-id 216571348281`, currently returns no budgets), so a zero-spend budget alert can be configured without Cost Explorer.
- **CloudWatch log retention: RESOLVED 2026-07-27.** All four Lambda log groups were set to retain forever (`Retention: None`); now set to **30 days**. Applied via CLI, not CloudFormation -- SAM does not manage these implicitly-created log groups, so the setting persists across deploys but will NOT apply to any newly created function's log group. If a new Lambda is added, set its retention explicitly:
  ```bash
  aws logs put-retention-policy --log-group-name /aws/lambda/<fn> \
    --retention-in-days 30 --profile personal --region us-east-1
  ```
- **`sts2-dashboard-216571348281-20260419-154335`** (1,031 objects / ~172 MB) is a **separate side project**, not part of this dashboard. Intentional; leave it alone.
- **Still unidentified:** a second CloudFront distribution `E31NFGUDZK6AUK` (`d31ehxmgiph3gd.cloudfront.net`) -- possibly serving the `sts2-dashboard` project -- and the leftover `fantasy-backend-HelloWorldFunction-*` from the SAM scaffold. Both free at current size.
- Both CloudFront distributions use `PriceClass_All`. `PriceClass_100` would be cheaper above the free transfer tier, but at this traffic level it is cosmetic.

### Re-running this audit

```bash
aws sts get-caller-identity --profile personal            # expect account 216571348281
aws freetier get-free-tier-usage --profile personal --region us-east-1
aws dynamodb describe-table --profile personal --region us-east-1 \
  --table-name fantasy-dashboard-data \
  --query 'Table.{Billing:BillingModeSummary.BillingMode,RCU:ProvisionedThroughput.ReadCapacityUnits}'
aws events list-rules --profile personal --region us-east-1 \
  --query 'Rules[].{Name:Name,State:State}' --output table
```

---

## Development Quick Start

```bash
# Navigate to the project
cd "/Users/lndahayo/Documents/Commish Tiers/trade-analysis-dashboard-clean"

# Start local dev server (port 5173)
./dev.sh

# OR manually:
cd dashboard/frontend && npm run dev

# Run the full pipeline locally
python3 update_dashboard.py --skip-git

# Dry run (see what would happen):
python3 update_dashboard.py --dry-run

# Deploy to AWS manually:
./deploy-to-aws.sh

# Run pipeline tests:
cd pipeline && python3 -m pytest tests/

# Build for production:
cd dashboard/frontend && npm run build
```

---

## Key External Dependencies

| Service | What For | URL Pattern |
|---|---|---|
| **Sleeper API** | League data (trades, rosters, standings, matchups, transactions) | `https://api.sleeper.app/v1/league/{id}/...` |
| **DynastyProcess (GitHub)** | Player valuations (historical via Git commits, current via raw CSV) | `https://api.github.com/repos/dynastyprocess/data/...` |
| **Google Drive** | Commish Tiers archive (embedded folder viewer) | `https://drive.google.com/embeddedfolderview?id={folderId}` |
| **KeepTradeCut** | Alternate player valuations (referenced but DynastyProcess is primary) | N/A |

---

## Environment Variables & Secrets

**Frontend (.env):**
- `VITE_DRIVE_FOLDER_ID` - Google Drive folder ID for archive embed.
- `VITE_API_BASE_URL` - API base URL (defaults to `/api`).

**GitHub Actions Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_S3_BUCKET` (`dynasuiiii-website`)
- `AWS_CLOUDFRONT_DISTRIBUTION_ID` (`EL6SCNZ7VJGN2`)

**Lambda Environment:**
- `TABLE_NAME` - DynamoDB table name (set by SAM template).
