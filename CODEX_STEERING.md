# Codex Steering: trade-analysis-dashboard

## Purpose and Scope
This repository contains a fantasy football analytics dashboard for a single Sleeper league. It is a static React site that reads pre-generated JSON files, and a Python ETL pipeline that fetches, processes, and generates those JSON files. The pipeline is the system of record; the frontend is a static renderer.

## Architecture Summary
- **Two main parts**
  - **pipeline/**: Python ETL pipeline that talks to Sleeper APIs, calculates metrics, and writes JSON into `dashboard/frontend/public/`.
  - **dashboard/frontend/**: React + Vite static site that fetches those JSON files at runtime.
- **No active backend**: `dashboard/backend.ARCHIVED/` is legacy; current app runs entirely from static JSON.
- **Deployment**: GitHub Actions runs pipeline daily; site is deployed to Vercel and AWS S3/CloudFront.

## Key Entry Points
- Frontend app bootstrap: `dashboard/frontend/src/main.tsx`
- Frontend routing/layout: `dashboard/frontend/src/App.tsx`, `dashboard/frontend/src/components/Layout/DashboardLayout.tsx`
- Data fetching layer: `dashboard/frontend/src/services/api.ts`
- Page components: `dashboard/frontend/src/pages/*.tsx`
- Pipeline master script: `update_dashboard.py`
- Multi-season config: `pipeline/config/seasons.yaml` (active vs static seasons)

## Data Flow (Authoritative)
1. Pipeline stages run from `update_dashboard.py` (root).
2. Pipeline reads/writes data in `pipeline/` and generates **final JSON** into `dashboard/frontend/public/`.
3. React app fetches JSON files directly (no API server) via `fetch('/api-standings.json')` etc.

## Pipeline Stages (High Level)
Defined in `update_dashboard.py`:
- Stage 0: detect current week (`pipeline/scripts/detect_current_week.py`)
- Stages 1-4: trades fetch → asset extraction → valuation cache → trade analysis
- Stage 5: waiver wire analysis
- Stage 5a/5b: player stats and lineup data fetch
- Stage 6: 2026 pick ownership analysis
- Stage 7: playoff bracket generation
- Stage 7a: draft order projection
- Stage 8/9: generate dashboard JSON from cumulative files
- Stage 10: standings fetch
- Stage 11: playoff simulations
- Stage 12: regenerate dashboard JSON with playoff data

If you change the shape of any pipeline outputs, update both the JSON generators and the frontend types/components.

## Frontend Data Contract
- **Static JSON is always used** in `dashboard/frontend/src/services/api.ts` (`USE_STATIC_DATA = true`).
- Expected files in `dashboard/frontend/public/`:
  - `api-trades.json`
  - `api-teams.json`
  - `api-stats-summary.json`
  - `api-standings.json`
  - `api-playoff-scenarios.json`
  - `waiver-wire-page.json`
  - `api-draft-order.json`
- Schemas are documented in `dashboard/frontend/public/README.md`.
- `DashboardLayout` expects `api-standings.json` to include `metadata.last_updated`.

## Multi-Season Handling
- `pipeline/config/seasons.yaml` defines which seasons are **active** vs **static**.
- Static seasons are immutable and skipped by the pipeline; active seasons are incrementally refreshed.
- Validation and schema enforcement live in `pipeline/utils/season_config.py`.

## Frontend Pages and Responsibilities
- `Overview.tsx`: league overview metrics, recent trades, manager rankings
- `Standings.tsx`: division standings + schedules (uses `api-standings.json` and playoff data)
- `PlayoffScenarios.tsx`: Monte Carlo results from `api-playoff-scenarios.json`
- `DraftOrderProjection.tsx`: 2026 pick projections (`api-draft-order.json`)
- `WaiverWireAnalysis.tsx`: waiver metrics (`waiver-wire-page.json`)
- `CommishTiersArchive.tsx`: Google Drive embedded archive

## Important Config and Environment Variables
- Frontend optional env:
  - `VITE_DRIVE_FOLDER_ID` (enables Commish Tiers archive embed)
- `VITE_API_BASE_URL` exists but is unused while `USE_STATIC_DATA = true`.
- Pipeline configs:
  - `pipeline/config/default.yaml` (general settings)
  - `pipeline/config/current_week.json` (auto-updated)
  - `pipeline/config/seasons.yaml` (multi-season config)

## Deployment Notes
- GitHub Actions: `./.github/workflows/update-dashboard.yml` runs daily at 14:00 UTC and deploys to AWS S3 + CloudFront.
- Vercel:
  - Root `vercel.json` builds from `dashboard/frontend/dist`.
  - `dashboard/vercel.json` redirects to CloudFront (historical setup).
- Local AWS deploy helper: `./scripts/deploy_aws.sh` (used by `make deploy-aws`) expects `AWS_S3_BUCKET` and `AWS_CLOUDFRONT_DISTRIBUTION_ID` and optionally `AWS_PROFILE`.

## Local Development Commands
Frontend:
```bash
cd dashboard/frontend
npm install
npm run dev
```
Pipeline:
```bash
pip install -r pipeline/requirements.txt
python3 update_dashboard.py
# or, skip git push
python3 refresh_local_data.py
```
AWS deploy (local):
```bash
export AWS_PROFILE=personal-cli-user
export AWS_S3_BUCKET=your-bucket
export AWS_CLOUDFRONT_DISTRIBUTION_ID=your-distribution-id
make deploy-aws
```

## Known Gotchas
- Root `package.json` includes scripts for a backend that no longer exists (`dashboard/backend`). Use `dashboard/package.json` or direct `dashboard/frontend` scripts instead.
- The frontend assumes static JSON; switching to live API calls requires changing `USE_STATIC_DATA` and adding an API server.
- Large JSON files in `pipeline/` (player stats, transaction history) can be heavy to process locally.

## Where to Look for Deep Docs
- `README.md` and `dashboard/README.md`
- `docs/guides/PIPELINE_DOCUMENTATION.md`
- `docs/guides/DATA_ARCHITECTURE.md`
- `docs/guides/WEEK_DETECTION.md`
- `.kiro/steering/*` (product/tech/structure summaries)

## If You Ask Codex to Change Things
Be explicit about:
- Whether to update pipeline outputs, frontend rendering, or both.
- Which JSON schema to change (and update `dashboard/frontend/public/README.md`).
- Whether to run pipeline locally or only adjust code.
