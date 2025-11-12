# Migration Guide: Moving Pipeline to Git Repo

## Goal
Move all pipeline code into the `trade-analysis-dashboard-clean` git repository so the entire workflow can run in one place (locally or via GitHub Actions).

## Current Structure (Local Machine)
```
/your-local-directory/
├── stage1_fetch_trades.py
├── stage2_extract_assets.py
├── stage3_cache_values.py
├── stage4_final.py
├── analyze_2026_pick_ownership.py
├── generate_playoff_bracket.py
├── fix_tyreek_value.py
├── update_dashboard.py
├── config/
├── utils/
├── scripts/
├── tests/
├── backups/
├── logs/
├── metrics/
├── *.csv (outputs)
├── *.json (outputs)
└── trade-analysis-dashboard-clean/  (git repo)
    ├── dashboard/
    ├── 3team_trades_analysis.json (copied)
    ├── league_trades_analysis_pipeline.csv (copied)
    └── team_identity_mapping.csv (copied)
```

## Target Structure (Git Repo)
```
trade-analysis-dashboard-clean/  (git repo)
├── pipeline/                     # NEW: All pipeline code
│   ├── stage1_fetch_trades.py
│   ├── stage2_extract_assets.py
│   ├── stage3_cache_values.py
│   ├── stage4_final.py
│   ├── analyze_2026_pick_ownership.py
│   ├── generate_playoff_bracket.py
│   ├── fix_tyreek_value.py
│   ├── config/
│   ├── utils/
│   ├── scripts/
│   ├── tests/
│   ├── backups/
│   ├── logs/
│   ├── metrics/
│   ├── requirements.txt
│   ├── constants.py
│   └── *.csv (pipeline outputs)
│   └── *.json (pipeline outputs)
├── dashboard/                    # Existing frontend/backend
├── update_dashboard.py           # UPDATED: Modified to work in git repo
├── 3team_trades_analysis.json   # Copied from pipeline/ for Vercel
├── league_trades_analysis_pipeline.csv  # Copied from pipeline/ for Vercel
├── team_identity_mapping.csv    # Copied from pipeline/ for Vercel
└── .github/
    └── workflows/
        └── update-dashboard.yml  # OPTIONAL: GitHub Actions automation
```

## Migration Steps

### Step 1: Create Pipeline Directory
```bash
cd trade-analysis-dashboard-clean
mkdir -p pipeline
```

### Step 2: Move Pipeline Files
From your local machine root, move these files/folders into `trade-analysis-dashboard-clean/pipeline/`:

**Python Scripts:**
- `stage1_fetch_trades.py`
- `stage2_extract_assets.py`
- `stage3_cache_values.py`
- `stage4_final.py`
- `analyze_2026_pick_ownership.py`
- `generate_playoff_bracket.py`
- `fix_tyreek_value.py`
- `constants.py`
- `requirements.txt`

**Directories:**
- `config/`
- `utils/`
- `scripts/`
- `tests/`

**Optional (for history):**
- `backups/`
- `logs/`
- `metrics/`

**Data Files (if you want to preserve them):**
- `*.csv` files (trades_raw.json, asset_transactions.csv, etc.)
- `*.json` files
- `team_identity_mapping.csv`
- `sleeper_rookie_draft_2025.csv`
- `weekly_2026_pick_projections_expanded.csv`
- `pick_origin_mapping.py`

### Step 3: Move Updated update_dashboard.py
Copy the updated `update_dashboard.py` to the git repo root:
```bash
cp update_dashboard.py trade-analysis-dashboard-clean/
```

### Step 4: Update .gitignore
Add to `trade-analysis-dashboard-clean/.gitignore`:
```
# Pipeline outputs (don't commit intermediate files)
pipeline/backups/
pipeline/logs/
pipeline/metrics/
pipeline/*.pyc
pipeline/__pycache__/

# Keep only the 3 files needed for Vercel at root
# (they're copied from pipeline/)
```

### Step 5: Test Locally
```bash
cd trade-analysis-dashboard-clean
python3 update_dashboard.py --dry-run
```

This should:
1. Check Tyreek value in `pipeline/asset_values_cache.csv`
2. Run stages 1-7 from `pipeline/` directory
3. Copy 3 files from `pipeline/` to git root
4. Show what would be committed

### Step 6: Run for Real
```bash
python3 update_dashboard.py
```

This will:
1. Run the full pipeline
2. Copy files to git root
3. Commit and push to GitHub
4. Trigger Vercel deployment

## What Gets Pushed to GitHub

**Committed to Git:**
- All pipeline code in `pipeline/`
- The 3 data files at root (for Vercel)
- `update_dashboard.py`
- `dashboard/` frontend/backend

**NOT Committed (via .gitignore):**
- `pipeline/backups/`
- `pipeline/logs/`
- `pipeline/metrics/`
- `node_modules/`

## Benefits of This Structure

1. **Single Source of Truth**: Everything in one git repo
2. **GitHub Actions Ready**: Can automate with scheduled workflows
3. **Version Control**: Pipeline code changes are tracked
4. **Easier Collaboration**: Others can clone and run
5. **Cleaner Local Machine**: No duplicate files

## Optional: GitHub Actions Automation

Create `.github/workflows/update-dashboard.yml`:
```yaml
name: Update Dashboard Data

on:
  schedule:
    - cron: '0 12 * * *'  # Daily at noon UTC
  workflow_dispatch:  # Manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd pipeline
          pip install -r requirements.txt
      
      - name: Run pipeline
        run: python3 update_dashboard.py
        env:
          # Add any secrets needed (API keys, etc.)
          LEAGUE_ID: ${{ secrets.LEAGUE_ID }}
```

## Rollback Plan

If something goes wrong, you still have all the original files on your local machine. Just don't delete them until you've verified the new structure works!
