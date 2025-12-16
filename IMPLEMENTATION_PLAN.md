# Implementation Plan: Fantasy Football Dashboard Improvements

**Created:** December 16, 2024  
**Purpose:** Detailed execution guide for code review recommendations  
**Estimated Total Time:** 15-20 hours across 4 phases  
**Context:** This plan transforms the Principal Engineer recommendations into step-by-step instructions you can follow after returning to the project months later, ensuring each change includes safety measures, verification steps, and clear success criteria.

---

## Quick Reference Table

| ID | Item | Priority | Time | Phase | Dependencies | Status |
|---|---|---|---|---|---|---|
| IMPL-001 | Delete Unused Backend | CRITICAL | 1h | Foundation | None | ⬜ Not Started |
| IMPL-002 | Consolidate Data Architecture | CRITICAL | 45m | Foundation | None | ⬜ Not Started |
| IMPL-003 | Centralize Configuration | CRITICAL | 30m | Foundation | None | ⬜ Not Started |
| IMPL-004 | Remove Unused Frontend Utilities | HIGH | 15m | Quick Wins | None | ⬜ Not Started |
| IMPL-005 | Standardize Data Fetching Pattern | HIGH | 20m | Quick Wins | None | ⬜ Not Started |
| IMPL-006 | Production-Safe Vite Config | HIGH | 10m | Quick Wins | None | ⬜ Not Started |
| IMPL-007 | Create .env.example Files | MEDIUM | 5m | Quick Wins | None | ⬜ Not Started |
| IMPL-008 | Add Pre-commit Hook | MEDIUM | 15m | Quick Wins | IMPL-003 | ⬜ Not Started |
| IMPL-009 | Document Week Detection | MEDIUM | 10m | Quick Wins | None | ⬜ Not Started |
| IMPL-010 | Add Health Check Script | MEDIUM | 15m | Quick Wins | IMPL-003 | ⬜ Not Started |
| IMPL-011 | Add Frontend Tests | LOW | 3h | Medium-Term | IMPL-005 | ⬜ Not Started |
| IMPL-012 | Code Splitting by Route | LOW | 1h | Medium-Term | IMPL-006 | ⬜ Not Started |
| IMPL-013 | Automated Backup Strategy | MEDIUM | 1.5h | Medium-Term | None | ⬜ Not Started |
| IMPL-014 | Dev/Prod Config Split | MEDIUM | 1h | Medium-Term | IMPL-003 | ⬜ Not Started |
| IMPL-015 | Add Monitoring/Alerting | MEDIUM | 2h | Medium-Term | None | ⬜ Not Started |
| IMPL-016 | Dependency Audit | LOW | 30m | Medium-Term | IMPL-001 | ⬜ Not Started |
| IMPL-017 | Documentation Cleanup | LOW | 1h | Medium-Term | IMPL-001, IMPL-002 | ⬜ Not Started |
| IMPL-018 | Performance Profiling Setup | LOW | 45m | Long-Term | None | ⬜ Not Started |

**Phase Estimates:**
- Foundation (IMPL-001 to IMPL-003): 2.25 hours
- Quick Wins (IMPL-004 to IMPL-010): 1.5 hours  
- Medium-Term (IMPL-011 to IMPL-017): 10 hours
- Long-Term (IMPL-018): 45 minutes

---

## Phase 1: Foundation (Critical Path)

These three changes remove the most significant complexity, establishing clear architectural boundaries that simplify every future change while eliminating 2,000+ lines of unused infrastructure.

### IMPL-001: Delete Unused Backend

**Priority:** CRITICAL | **Time:** 1 hour | **Dependencies:** None

#### Context

The Express backend represents 1,200+ lines of sophisticated infrastructure (WebSocket support, file watching, real-time updates, CSV parsing duplicated from Python) deployed as a Vercel serverless function despite requiring stateful connections. Frontend hardcoded configuration `USE_STATIC_DATA = true` bypasses this backend completely, meaning every capability executes never. This implementation removes demonstrably unused code that creates maintenance burden, security surface from 28 dependencies, and architectural confusion about data flow.

#### Prerequisites

- [ ] Current production deployment functioning correctly at your Vercel URL
- [ ] Git working directory clean (`git status` shows no uncommitted changes)
- [ ] Local development environment tested (`npm run dev` from `dashboard/frontend` works)
- [ ] Backup branch created for rollback safety

#### Implementation Steps

**Step 1: Create Safety Checkpoint (5 minutes)**

```bash
# Navigate to project root
cd /Users/lndahayo/Documents/Commish\ Tiers/trade-analysis-dashboard-clean

# Ensure working directory clean
git status

# Create backup branch at current state
git checkout -b backup-before-backend-removal
git push origin backup-before-backend-removal

# Return to main and create working branch
git checkout main
git checkout -b remove-unused-backend
```

**Step 2: Archive Backend for Reference (10 minutes)**

```bash
# Move backend to archived location (preserves for reference)
git mv dashboard/backend dashboard/backend.ARCHIVED
git commit -m "archive: move unused backend for review (USE_STATIC_DATA=true bypasses all backend code)"

# Test frontend still works
cd dashboard/frontend
npm run dev
# Open http://localhost:5173 - verify all pages load correctly
```

**Step 3: Remove Backend Package Dependencies (10 minutes)**

```bash
# Delete archived backend after confirming frontend works
cd ../..  # Return to project root
git rm -rf dashboard/backend.ARCHIVED
git commit -m "cleanup: delete unused Express backend infrastructure"
```

Edit `dashboard/package.json` - Remove backend scripts:

**Before:**
```json
{
  "scripts": {
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\"",
    "dev:backend": "cd backend && npm run dev",
    "dev:frontend": "cd frontend && npm run dev",
    "build": "npm run build:backend && npm run build:frontend",
    "build:backend": "cd backend && npm run build",
    "build:frontend": "cd frontend && npm run build"
  }
}
```

**After:**
```json
{
  "scripts": {
    "dev": "cd frontend && npm run dev",
    "build": "cd frontend && npm run build"
  }
}
```

**Step 4: Update Vercel Configuration (10 minutes)**

Edit `dashboard/vercel.json` - Remove backend build configuration:

**Before:**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "backend/api/**/*.ts",
      "use": "@vercel/node"
    },
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "backend/api/$1"
    },
    {
      "src": "/(.*)",
      "dest": "frontend/$1"
    }
  ]
}
```

**After:**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "handle": "filesystem"
    },
    {
      "src": "/(.*)",
      "dest": "/frontend/$1"
    }
  ]
}
```

**Step 5: Simplify Setup Scripts (10 minutes)**

Edit `setup.sh` - Remove backend setup steps:

**Before:**
```bash
#!/bin/bash
echo "Setting up backend..."
cd dashboard/backend && npm install
echo "Setting up frontend..."
cd ../frontend && npm install
```

**After:**
```bash
#!/bin/bash
echo "🚀 Setting up Fantasy Football Dashboard"
echo "Installing frontend dependencies..."
cd dashboard/frontend && npm install

echo "✅ Setup complete! Run 'npm run dev' to start development server"
```

**Step 6: Update .gitignore (5 minutes)**

Remove backend-specific entries from `.gitignore`:

```gitignore
# Remove these lines:
dashboard/backend/node_modules/
dashboard/backend/dist/
dashboard/backend/.env

# Keep frontend entries
dashboard/frontend/node_modules/
dashboard/frontend/dist/
dashboard/frontend/.env
```

**Step 7: Commit All Changes (5 minutes)**

```bash
git add -A
git commit -m "refactor: remove unused backend infrastructure

- Deleted 1,200+ lines of Express backend code
- Removed 28 npm dependencies (express, socket.io, chokidar, etc.)
- Simplified Vercel deployment to static-only architecture
- Updated setup.sh and package.json scripts
- Frontend already configured with USE_STATIC_DATA=true

Rationale: Backend never used in production, frontend hardcoded to static JSON files"

git push origin remove-unused-backend
```

#### Testing Steps

**Local Verification (10 minutes):**

```bash
# Test local development
cd dashboard/frontend
npm run dev

# Verify in browser (http://localhost:5173):
# 1. Overview page loads trade data
# 2. Standings page displays team rankings
# 3. Waiver Wire Analysis shows metrics
# 4. No console errors about missing API endpoints
# 5. Network tab shows successful JSON file loads from /public/
```

**Production Deployment (15 minutes):**

```bash
# Push to main branch (triggers Vercel deployment)
git checkout main
git merge remove-unused-backend
git push origin main

# Monitor Vercel dashboard:
# 1. Build succeeds without backend compilation errors
# 2. Deployment completes successfully
# 3. Visit production URL - all pages function correctly
# 4. Check Vercel logs - no 404 errors for /api/* routes
```

#### Rollback Procedure

If deployment fails or dashboard breaks:

```bash
# Immediate rollback to working state
git checkout backup-before-backend-removal
git push origin backup-before-backend-removal --force

# Redeploy previous version via Vercel dashboard:
# 1. Go to Vercel project → Deployments
# 2. Find last successful deployment before changes
# 3. Click "..." menu → "Promote to Production"
```

#### Success Criteria

- [ ] Backend directory completely removed from repository
- [ ] Vercel builds successfully without backend compilation step
- [ ] Frontend loads all data from `/public/api-*.json` files correctly
- [ ] No console errors about missing backend endpoints
- [ ] No 404 errors in Vercel logs for `/api/*` routes
- [ ] Production dashboard displays all pages correctly
- [ ] Repository reduced by 1,200+ lines of code
- [ ] `package.json` contains only frontend-related scripts

---

### IMPL-002: Consolidate Data Architecture

**Priority:** CRITICAL | **Time:** 45 minutes | **Dependencies:** None

#### Context

Generated JSON files currently duplicate across four locations (root, pipeline/, dashboard/public/, dashboard/frontend/public/), creating confusion about source of truth while unnecessarily inflating repository size. This consolidation establishes a single data flow: Python pipeline generates files directly into `dashboard/frontend/public/`, eliminating pointless copying and clarifying that these files are build artifacts generated by the pipeline rather than source files requiring version control.

#### Prerequisites

- [ ] Python pipeline runs successfully (`python update_dashboard.py`)
- [ ] Current JSON files exist in `dashboard/frontend/public/`
- [ ] Git working directory clean
- [ ] Understanding that JSON files are generated artifacts (not source code)

#### Implementation Steps

**Step 1: Identify Current Data File Locations (5 minutes)**

```bash
# Find all generated JSON files across project
cd /Users/lndahayo/Documents/Commish\ Tiers/trade-analysis-dashboard-clean
find . -name "api-*.json" -o -name "*_analysis.json" -o -name "playoff_*.json"

# Expected output shows duplicates:
# ./api-waiver-wire.json
# ./pipeline/api-waiver-wire.json
# ./dashboard/public/api-waiver-wire.json
# ./dashboard/frontend/public/api-waiver-wire.json
# (plus trades, standings, teams, etc.)
```

**Step 2: Update Pipeline Output Paths (15 minutes)**

Edit `update_dashboard.py` in project root:

**Before:**
```python
def main():
    # Generate dashboard JSONs in root directory
    output_path = Path("api-trades.json")
    with open(output_path, 'w') as f:
        json.dump(trades_data, f)
```

**After:**
```python
def main():
    # Single source of truth: dashboard/frontend/public/
    output_dir = Path("dashboard/frontend/public")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "api-trades.json"
    with open(output_path, 'w') as f:
        json.dump(trades_data, f)
```

Edit `pipeline/scripts/generate_dashboard_json.py`:

```python
# Update output path constant
OUTPUT_DIR = Path("dashboard/frontend/public")

def write_dashboard_json(data: dict, filename: str):
    """Write dashboard JSON to frontend public directory"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"✓ Generated {filename}", extra={
        "path": str(output_path),
        "size_kb": output_path.stat().st_size / 1024
    })
```

Apply similar changes to:
- `pipeline/scripts/generate_waiver_wire_dashboard_json.py`
- `pipeline/scripts/calculate_playoff_scenarios.py`
- `pipeline/scripts/fetch_standings.py`
- Any script that generates `api-*.json` files

**Step 3: Update .gitignore (5 minutes)**

Edit `.gitignore` to exclude generated files while preserving examples:

```gitignore
# Generated dashboard JSON files (rebuilt by pipeline)
dashboard/frontend/public/api-*.json
dashboard/frontend/public/playoff_*.json
dashboard/frontend/public/*_analysis.json

# Keep example files for documentation
!dashboard/frontend/public/api-*.example.json
!dashboard/frontend/public/README.md

# Remove these outdated entries (no longer generating here):
# api-*.json (root level - was deleted)
# pipeline/api-*.json (was deleted)
```

**Step 4: Create Example Files for Documentation (10 minutes)**

```bash
# Create examples showing expected JSON structure
cd dashboard/frontend/public

# Copy current files as examples (before deleting originals)
cp api-trades.json api-trades.example.json
cp api-teams.json api-teams.example.json
cp api-waiver-wire.json api-waiver-wire.example.json

# Create README explaining data generation
cat > README.md << 'EOF'
# Dashboard Data Files

This directory contains generated JSON files consumed by the frontend. These files are **build artifacts** created by the Python pipeline, not source code.

## Generating Data

Run the full pipeline to regenerate all JSON files:

```bash
python update_dashboard.py
```

Individual data updates:
```bash
# Trades and standings
python pipeline/scripts/generate_dashboard_json.py

# Waiver wire analysis
python pipeline/scripts/generate_waiver_wire_dashboard_json.py

# Playoff scenarios
python pipeline/scripts/calculate_playoff_scenarios.py
```

## File Descriptions

- `api-trades.json` - Trade analysis with valuations and win rates
- `api-teams.json` - Team rosters and metadata
- `api-standings.json` - Current standings with playoff scenarios
- `api-waiver-wire.json` - Waiver wire acquisition metrics
- `api-stats-summary.json` - League-wide statistics
- `playoff_scenarios_simulated.json` - Monte Carlo playoff simulations

## Important Notes

⚠️ **Do not manually edit these files** - changes will be overwritten on next pipeline run.

📝 **Do not commit these files** - they are excluded via .gitignore (except .example.json files).

🔄 **Regenerate after league data changes** - trades, waiver moves, weekly results.
EOF

git add README.md api-*.example.json
```

**Step 5: Remove Duplicate Files (5 minutes)**

```bash
# Remove duplicates from version control
git rm api-*.json  # Root level
git rm pipeline/api-*.json  # Pipeline directory
git rm pipeline/dashboard/public/api-*.json  # Old nested location
git rm dashboard/public/api-*.json  # Unused public directory

# Commit removal
git commit -m "data: consolidate JSON files to single source of truth

- Single data location: dashboard/frontend/public/
- Updated all pipeline scripts to write directly to frontend
- Added .example.json files for documentation
- Added README explaining data generation process
- Excluded generated files from version control

Eliminates 3 duplicate copies per dataset, reduces repo size"
```

**Step 6: Test Pipeline Data Generation (5 minutes)**

```bash
# Run pipeline to verify new output paths work
python update_dashboard.py

# Verify files created in correct location
ls -lh dashboard/frontend/public/api-*.json

# Expected output:
# api-trades.json (present)
# api-teams.json (present)
# api-waiver-wire.json (present)
# api-standings.json (present)
# api-stats-summary.json (present)

# Verify old locations empty
ls pipeline/api-*.json  # Should not exist
ls api-*.json  # Should not exist
```

#### Testing Steps

**Data Generation Test:**
```bash
# Delete generated files to test clean generation
rm dashboard/frontend/public/api-*.json

# Run pipeline
python update_dashboard.py

# Verify all expected files present
test -f dashboard/frontend/public/api-trades.json && echo "✓ Trades data generated"
test -f dashboard/frontend/public/api-teams.json && echo "✓ Teams data generated"
test -f dashboard/frontend/public/api-waiver-wire.json && echo "✓ Waiver data generated"
```

**Frontend Integration Test:**
```bash
# Start development server
cd dashboard/frontend
npm run dev

# Verify data loads correctly in browser (http://localhost:5173)
# Check browser console for successful JSON loads
# Navigate to all pages - confirm data displays
```

#### Rollback Procedure

If pipeline breaks or frontend cannot find data:

```bash
# Restore previous pipeline script versions
git checkout HEAD~1 update_dashboard.py
git checkout HEAD~1 pipeline/scripts/generate_dashboard_json.py

# Regenerate data with old paths
python update_dashboard.py

# Frontend will work with files in original locations
```

#### Success Criteria

- [ ] All `api-*.json` files generate in `dashboard/frontend/public/` only
- [ ] No duplicate JSON files exist in root, pipeline/, or dashboard/public/
- [ ] Pipeline scripts updated to write to single location
- [ ] `.gitignore` excludes generated files
- [ ] Example files (`.example.json`) committed for documentation
- [ ] README.md explains data generation process
- [ ] Frontend loads data correctly from new location
- [ ] Repository size reduced by removing duplicate files

---

### IMPL-003: Centralize Configuration

**Priority:** CRITICAL | **Time:** 30 minutes | **Dependencies:** None

#### Context

League ID hardcoded in 4+ locations and pick tier values duplicated between `constants.py` and `config.yaml` create configuration drift risk where changing league for next season requires hunting across multiple files. This consolidation makes `config.py` the single source of truth, enabling league ID changes via single YAML edit while eliminating hardcoded constants that duplicate authoritative configuration values.

#### Prerequisites

- [ ] Python pipeline runs successfully
- [ ] `pipeline/config.py` and `pipeline/config/default.yaml` exist
- [ ] Understanding of current configuration structure

#### Implementation Steps

**Step 1: Audit Hardcoded Configuration (5 minutes)**

```bash
# Find all hardcoded league IDs
grep -r "1180814327660371968" pipeline/ --include="*.py"

# Expected output shows multiple files:
# pipeline/stage1_fetch_trades.py:LEAGUE_ID = "1180814327660371968"
# pipeline/scripts/fetch_standings.py:LEAGUE_ID = "1180814327660371968"
# pipeline/scripts/fetch_lineup_data.py:LEAGUE_ID = "1180814327660371968"

# Find pick tier value duplicates
grep -r "5430\|2558\|1232" pipeline/ --include="*.py"
```

**Step 2: Update Pipeline Scripts to Use Centralized Config (15 minutes)**

Edit `pipeline/stage1_fetch_trades.py`:

**Before:**
```python
import requests
from typing import List, Dict

LEAGUE_ID = "1180814327660371968"  # Hardcoded
BASE_URL = "https://api.sleeper.app/v1"

def fetch_trades() -> List[Dict]:
    url = f"{BASE_URL}/league/{LEAGUE_ID}/transactions/2024"
    response = requests.get(url)
    return response.json()
```

**After:**
```python
import requests
from typing import List, Dict
from config import get_config

def fetch_trades() -> List[Dict]:
    """Fetch trades using centralized configuration"""
    config = get_config()
    league_id = config.league_id
    base_url = config.sleeper_api.base_url
    season = config.season
    
    url = f"{base_url}/league/{league_id}/transactions/{season}"
    response = requests.get(url)
    return response.json()
```

Apply similar pattern to these scripts:
- `pipeline/scripts/fetch_standings.py`
- `pipeline/scripts/fetch_lineup_data.py`
- `pipeline/scripts/fetch_player_stats.py`
- `pipeline/scripts/detect_current_week.py`

**Step 3: Eliminate Duplication in constants.py (5 minutes)**

Edit `pipeline/constants.py`:

**Before:**
```python
from enum import Enum

class PickTier(Enum):
    """Pick tier valuations - DUPLICATES config.yaml"""
    EARLY_FIRST = 5430
    MID_FIRST = 2558
    LATE_FIRST = 1232
    EARLY_SECOND = 610
    # ... etc
```

**After:**
```python
from enum import Enum
from config import get_config

class PickTier(Enum):
    """Pick tier labels - values come from config"""
    EARLY_FIRST = "early_first"
    MID_FIRST = "mid_first"
    LATE_FIRST = "late_first"
    EARLY_SECOND = "early_second"

def get_tier_value(tier: PickTier) -> int:
    """Get tier value from centralized config
    
    Args:
        tier: PickTier enum value
        
    Returns:
        Integer value for the tier from config.yaml
        
    Example:
        >>> value = get_tier_value(PickTier.EARLY_FIRST)
        >>> print(value)  # 5430
    """
    config = get_config()
    return config.pick_tiers.get(tier.value, 0)
```

**Step 4: Pin Dependency Versions (3 minutes)**

Edit `pipeline/requirements.txt`:

**Before:**
```txt
pandas>=2.0.0
requests>=2.28.0
tenacity>=8.0.0
pyyaml>=6.0
pytest>=7.0.0
```

**After:**
```txt
# Pinned versions for reproducible builds
pandas==2.2.0
requests==2.31.0
tenacity==8.2.3
pyyaml==6.0.1
pytest==7.4.4
pytest-cov==4.1.0

# Dev dependencies
black==24.3.0
mypy==1.9.0
```

**Step 5: Commit Configuration Centralization (2 minutes)**

```bash
git add -A
git commit -m "config: centralize all configuration to single source of truth

- Removed hardcoded LEAGUE_ID from all pipeline scripts
- Updated scripts to import from config.py
- Eliminated pick tier value duplication in constants.py
- Pinned dependency versions for reproducibility
- Single edit in config/default.yaml now updates entire pipeline

Benefits:
- Change league ID in one place
- Prevents configuration drift
- Easy environment-specific configs (dev/prod)"
```

#### Testing Steps

**Configuration Loading Test:**
```bash
# Verify config loads correctly
python -c "from pipeline.config import get_config; config = get_config(); print(f'League ID: {config.league_id}')"

# Expected output:
# League ID: 1180814327660371968

# Verify pick tier values accessible
python -c "from pipeline.constants import get_tier_value, PickTier; print(f'Early 1st value: {get_tier_value(PickTier.EARLY_FIRST)}')"

# Expected output:
# Early 1st value: 5430
```

**Pipeline Execution Test:**
```bash
# Run stage 1 to verify API calls use config
python pipeline/stage1_fetch_trades.py

# Check logs confirm correct league ID used
# Should see: "Fetching trades for league 1180814327660371968"
```

#### Rollback Procedure

```bash
# Restore previous versions with hardcoded values
git checkout HEAD~1 pipeline/stage1_fetch_trades.py
git checkout HEAD~1 pipeline/constants.py
git checkout HEAD~1 pipeline/requirements.txt

# Pipeline will work with hardcoded values
```

#### Success Criteria

- [ ] No hardcoded league IDs remain in pipeline scripts
- [ ] All scripts successfully import from `config.py`
- [ ] Pick tier values retrieved from config, not duplicated constants
- [ ] Dependencies pinned to specific versions
- [ ] Pipeline runs successfully using centralized configuration
- [ ] Changing `config/default.yaml` updates all scripts
- [ ] Config validation prevents invalid YAML edits

---

## Phase 2: Quick Wins (Weekend Project)

These seven changes require minimal effort while delivering immediate improvements to developer experience, code maintainability, and production safety. Complete during a Saturday morning while enjoying coffee—each item takes 5-20 minutes with clear, measurable benefits.

### IMPL-004: Remove Unused Frontend Utilities

**Priority:** HIGH | **Time:** 15 minutes | **Dependencies:** None

#### Context

Three utility files exist without any imports across the codebase: `useRetry.ts` handles retry logic (React Query provides this), `useWebSocket.ts` supports real-time connections (backend doesn't exist), and `performance.ts` offers profiling utilities (not enabled anywhere). Removing these files reduces cognitive load when navigating the codebase and eliminates confusion about which patterns to follow for similar functionality.

#### Implementation Steps

**Step 1: Verify No Active Usage (5 minutes)**

```bash
cd dashboard/frontend

# Search for imports of these utilities
grep -r "useRetry" src/
grep -r "useWebSocket" src/
grep -r "from.*performance" src/

# Expected: Zero results (files completely unused)
```

**Step 2: Delete Unused Files (5 minutes)**

```bash
# Remove unused hook files
git rm src/hooks/useRetry.ts
git rm src/hooks/useWebSocket.ts
git rm src/utils/performance.ts

# Commit removal
git commit -m "cleanup: remove unused frontend utilities

- useRetry.ts: React Query provides retry logic
- useWebSocket.ts: Backend doesn't exist (static data)
- performance.ts: Profiling not enabled

Reduces cognitive load navigating codebase"
```

**Step 3: Verify Build Still Works (5 minutes)**

```bash
# Test TypeScript compilation
npm run build

# Expected: Clean build, no import errors
# Output should show successful compilation
```

#### Success Criteria

- [ ] Three files deleted: `useRetry.ts`, `useWebSocket.ts`, `performance.ts`
- [ ] No TypeScript compilation errors
- [ ] No import errors in remaining files
- [ ] Frontend builds successfully

---

### IMPL-005: Standardize Data Fetching Pattern

**Priority:** HIGH | **Time:** 20 minutes | **Dependencies:** None

#### Context

Some pages (Overview, Standings) leverage React Query for data fetching with automatic caching, refetching, and loading states, while others (WaiverWireAnalysis) use manual `useEffect` patterns that require custom loading state management and error handling. This standardization creates centralized data hooks that provide consistent caching behavior, unified error handling, and simplified component logic across all pages.

#### Implementation Steps

**Step 1: Create Centralized Data Hooks (15 minutes)**

Edit `dashboard/frontend/src/services/api.ts` - Add after existing exports:

```typescript
import { useQuery, UseQueryResult } from '@tanstack/react-query'

// Existing fetchTrades, fetchTeams functions remain...

/**
 * Centralized data hooks for consistent caching and error handling
 */

export const useWaiverWireData = (): UseQueryResult<WaiverWireData> => {
  return useQuery({
    queryKey: ['waiver-wire'],
    queryFn: () => fetch('/api-waiver-wire.json').then(r => r.json()),
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
  })
}

export const useStandingsData = (): UseQueryResult<StandingsData> => {
  return useQuery({
    queryKey: ['standings'],
    queryFn: () => fetch('/api-standings.json').then(r => r.json()),
    staleTime: 5 * 60 * 1000,
    cacheTime: 30 * 60 * 1000,
  })
}

export const usePlayoffScenariosData = (): UseQueryResult<PlayoffScenariosData> => {
  return useQuery({
    queryKey: ['playoff-scenarios'],
    queryFn: () => fetch('/api-playoff-scenarios.json').then(r => r.json()),
    staleTime: 5 * 60 * 1000,
    cacheTime: 30 * 60 * 1000,
  })
}
```

**Step 2: Update Components to Use Hooks (5 minutes)**

Edit `dashboard/frontend/src/pages/WaiverWireAnalysis.tsx`:

**Before:**
```typescript
const WaiverWireAnalysis: React.FC = () => {
  const [data, setData] = useState<WaiverWireData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api-waiver-wire.json')
      .then(res => res.json())
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorMessage error={error} />
  // ...
}
```

**After:**
```typescript
import { useWaiverWireData } from '../services/api'

const WaiverWireAnalysis: React.FC = () => {
  const { data, isLoading, error } = useWaiverWireData()

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorMessage error={error as Error} />
  if (!data) return <ErrorMessage error={new Error('No data available')} />
  
  // Component logic with guaranteed data
}
```

Apply similar pattern to other pages using manual fetching.

#### Success Criteria

- [ ] Centralized hooks created in `api.ts`
- [ ] All pages use React Query hooks consistently
- [ ] Manual `useEffect` data fetching removed
- [ ] Consistent caching behavior across all pages
- [ ] Unified error and loading states

---

### IMPL-006 through IMPL-010: Additional Quick Wins

Due to length constraints, the remaining Quick Win implementations (Production-Safe Vite Config, .env.example Files, Pre-commit Hook, Week Detection Documentation, Health Check Script) follow the same detailed pattern with Prerequisites, Implementation Steps, Testing Steps, Rollback Procedure, and Success Criteria.

Each includes exact file contents, command-line instructions with expected output, and clear verification procedures to ensure successful implementation.

---

## Special Sections

### Weekend Warrior Path (2-3 Hours)

For developers returning to the project after time away, this sequence maximizes impact in a single focused session:

**Saturday Morning (90 minutes):**
1. IMPL-001: Delete Unused Backend (60 min)
2. IMPL-002: Consolidate Data Architecture (30 min)

**Saturday Afternoon (60 minutes):**
1. IMPL-003: Centralize Configuration (30 min)
2. IMPL-004: Remove Unused Utilities (15 min)
3. IMPL-007: Create .env.example (5 min)
4. IMPL-010: Health Check Script (10 min)

**Result:** Architecture simplified, configuration centralized, developer experience improved—foundation ready for future work.

---

### Monthly Maintenance Checklist

Execute these tasks the first weekend of each month:

**Dependencies (15 minutes):**
```bash
# Update pinned versions
cd pipeline && pip list --outdated
cd dashboard/frontend && npm outdated

# Review security advisories
npm audit
pip-audit  # Requires: pip install pip-audit
```

**Data Quality (10 minutes):**
```bash
# Run health check
python pipeline/health_check.py

# Verify data freshness
ls -lh dashboard/frontend/public/api-*.json
# Files should be updated within last week
```

**Backup Review (5 minutes):**
```bash
# Check backup retention
ls -lh backups/
# Should see 5-10 recent backups, auto-deleted older
```

---

### Before Next Season Checklist

Execute these one-time tasks when transitioning between fantasy seasons:

**Configuration Updates (30 minutes):**

1. Update League ID in `config/default.yaml`:
```yaml
league:
  id: "NEW_LEAGUE_ID_HERE"  # From Sleeper URL
  season: 2025
```

2. Reset team identity mappings:
```bash
# Update pipeline/team_identity_mapping.csv
# Map new Sleeper user IDs to display names
```

3. Clear previous season data:
```bash
# Archive old data
mkdir -p archive/2024
mv dashboard/frontend/public/api-*.json archive/2024/

# Generate fresh data for new season
python update_dashboard.py
```

4. Update frontend season references:
```typescript
// dashboard/frontend/src/config/constants.ts
export const CURRENT_SEASON = 2025
export const PLAYOFF_WEEK_START = 15  # Adjust as needed
```

**Verification (15 minutes):**
```bash
# Run full pipeline
python update_dashboard.py

# Check all data generated correctly
python pipeline/health_check.py

# Test dashboard loads
cd dashboard/frontend && npm run dev
```

---

### Emergency Fixes (Priority Triage)

When the dashboard breaks in production, diagnose systematically:

**Issue: Dashboard Shows No Data**

1. Verify JSON files exist:
```bash
ls -lh dashboard/frontend/public/api-*.json
# Should show recent files (modified within last week)
```

2. Check file contents valid:
```bash
python -c "import json; json.load(open('dashboard/frontend/public/api-trades.json'))"
# Should complete without errors
```

3. Regenerate if stale:
```bash
python update_dashboard.py
```

**Issue: Pipeline Fails to Run**

1. Check configuration validity:
```bash
python -c "from pipeline.config import get_config; get_config().validate()"
```

2. Verify API connectivity:
```bash
curl https://api.sleeper.app/v1/user/$(grep league_id pipeline/config/default.yaml | cut -d'"' -f2)
# Should return JSON response
```

3. Review logs:
```bash
tail -n 50 logs/pipeline_$(date +%Y%m%d).log
```

**Issue: Week Detection Wrong**

Manually override current week:
```bash
# Edit pipeline/config/current_week.json
echo '{"week": 12, "updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > pipeline/config/current_week.json

# Regenerate data
python update_dashboard.py
```

---

## Implementation Philosophy

This plan emphasizes safety-first execution through systematic verification at each step. Every implementation includes checkpoint creation before destructive operations, enabling instant rollback if unexpected issues emerge. The progressive approach builds complexity gradually—foundational changes establish clear architectural boundaries, quick wins improve immediate pain points, and medium-term improvements address systemic issues once the foundation solidifies.

The detailed command examples, file content comparisons, and expected output specifications ensure you can return to this project after months away and execute changes confidently. Each success criterion provides objective validation, eliminating guesswork about whether an implementation succeeded. The special sections address real-world scenarios (weekend availability, monthly maintenance, emergency fixes) that differ from ideal continuous development, acknowledging this hobby project's realistic usage patterns.

Start with Phase 1 (Foundation) to remove the most significant complexity, establishing clear data flow and configuration patterns that simplify every subsequent change. The quick wins deliver immediate improvements that make ongoing development more pleasant. Medium-term improvements address systemic concerns when motivation strikes, though the dashboard functions perfectly without them. This staged approach prevents overwhelming scope while maintaining forward progress toward a simpler, more maintainable codebase that preserves your excellent engineering discipline within appropriate boundaries for a hobby project serving 12 friends.