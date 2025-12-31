# Fantasy Football Trade Analysis Dashboard

A comprehensive web application for analyzing fantasy football trades, tracking team performance, and identifying trading patterns in your league. Features live standings, playoff scenarios, draft order projections, waiver wire analysis, and historical trade data.

## 🏆 Features

### Core Analytics
- **Trade Analysis**: Comprehensive trade history with value tracking and win/loss analysis
- **Manager Rankings**: Skill-based rankings with win rates and value analysis
- **Live Standings**: Current week standings with division rankings and playoff positioning
- **Playoff Scenarios**: Monte Carlo simulations showing playoff probabilities and projected seeds
- **Draft Order Projection**: Progressive draft order tracking across the season with 2026 pick analysis
- **Waiver Wire Analysis**: Advanced metrics including hit rate, churn index, efficiency scores, and timing analysis

### User Experience
- **Commish Tiers Archive**: Browse and download weekly power rankings from embedded Google Drive folder
- **Interactive Dashboard**: Modern, responsive UI with TanStack Query for data management
- **Error Handling**: Robust error boundaries and retry mechanisms
- **Performance Optimized**: Skeleton loading, debounced search, and memoized components

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Modern web browser

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/capitanlandr/trade-analysis-dashboard.git
   cd trade-analysis-dashboard
   ```

2. **Install dependencies**
   ```bash
   cd dashboard
   npm install
   ```

3. **Start the application**
   ```bash
   npm run dev
   ```

4. **Open your browser**
   Navigate to `http://localhost:5173`

## 📊 Data Pipeline Integration

This dashboard is powered by a Python pipeline that processes Sleeper API data. The pipeline is located in the [`pipeline/`](pipeline/) directory and generates JSON files directly into [`dashboard/frontend/public/`](dashboard/frontend/public/).

### Data Flow

```
Sleeper API
    ↓
Python Pipeline (Multiple stages in pipeline/)
    ├─ Stage 0: Detect current week (scripts/detect_current_week.py)
    ├─ Stages 1-4: Trade analysis (stage1-4 scripts)
    ├─ Stage 5: Waiver wire analysis (stage5_waiver_wire.py)
    ├─ Stage 6: 2026 pick ownership (analyze_2026_pick_ownership.py)
    ├─ Stage 7: Playoff scenarios (scripts/simulate_playoff_scenarios.py)
    ├─ Stage 7a: Draft order projection (scripts/calculate_progressive_draft_order.py)
    ├─ Stage 8+: JSON generation (scripts/generate_dashboard_json.py, etc.)
    ↓
Dashboard JSON Files (dashboard/frontend/public/)
    ├─ api-trades.json
    ├─ api-teams.json
    ├─ api-stats-summary.json
    ├─ api-standings.json
    ├─ api-playoff-scenarios.json
    ├─ api-waiver-wire.json
    └─ api-draft-order.json
    ↓
React Dashboard (Vite + React + TypeScript)
```

### Updating Dashboard Data

**Automated (Recommended):**
```bash
python3 update_dashboard.py
```

This single command (from project root):
1. Detects current week from Sleeper API
2. Fetches latest trades and standings
3. Runs waiver wire analysis
4. Simulates playoff scenarios (10,000 Monte Carlo simulations)
5. Calculates progressive draft order projections
6. Generates all dashboard JSON files
7. Commits and pushes to GitHub
8. Triggers Vercel deployment

**Manual (for debugging):**
```bash
cd pipeline
python3 scripts/detect_current_week.py
python3 stage1_fetch_trades.py
python3 stage2_extract_assets.py
python3 stage3_cache_values.py
python3 stage4_final.py
python3 stage5_waiver_wire.py
python3 scripts/fetch_standings.py
python3 scripts/simulate_playoff_scenarios.py
python3 scripts/calculate_progressive_draft_order.py
python3 scripts/generate_dashboard_json.py
python3 scripts/generate_waiver_wire_dashboard_json.py

# Then commit and push
cd ..
git add dashboard/frontend/public/*.json
git commit -m "data: update dashboard data"
git push origin main
```

### Data Files

The dashboard reads from JSON files in [`dashboard/frontend/public/`](dashboard/frontend/public/):

- **api-trades.json** - Historical trade data with value analysis
- **api-teams.json** - Manager statistics and rankings
- **api-stats-summary.json** - League-wide trade statistics
- **api-standings.json** - Current week standings with division info
- **api-playoff-scenarios.json** - Monte Carlo simulation results with playoff probabilities
- **api-waiver-wire.json** - Waiver wire metrics (hit rate, churn, efficiency, timing)
- **api-draft-order.json** - Progressive 2026 draft order projections by week

See [`dashboard/frontend/public/README.md`](dashboard/frontend/public/README.md) for detailed schema documentation.

## 🛠️ Development

### Project Structure

```
├── dashboard/
│   ├── frontend/             # React application (Vite + TypeScript)
│   │   ├── src/
│   │   │   ├── components/   # React components
│   │   │   │   ├── Archive/  # Commish Tiers Archive
│   │   │   │   ├── Layout/   # Dashboard layout
│   │   │   │   ├── Modals/   # Trade/Schedule modals
│   │   │   │   ├── Tables/   # Data tables
│   │   │   │   ├── UI/       # Shared UI components
│   │   │   │   └── WaiverWire/ # Waiver wire cards
│   │   │   ├── pages/        # Page components
│   │   │   │   ├── Overview.tsx
│   │   │   │   ├── Standings.tsx
│   │   │   │   ├── PlayoffScenarios.tsx
│   │   │   │   ├── DraftOrderProjection.tsx
│   │   │   │   ├── WaiverWireAnalysis.tsx
│   │   │   │   └── CommishTiersArchive.tsx
│   │   │   ├── services/     # API client
│   │   │   ├── hooks/        # Custom hooks
│   │   │   └── types/        # TypeScript types
│   │   └── public/           # Static JSON data files
│   └── backend.ARCHIVED/     # Legacy backend (no longer used)
├── pipeline/                 # Python data pipeline
│   ├── scripts/              # Pipeline scripts
│   ├── utils/                # Shared utilities
│   ├── config/               # Configuration files
│   │   ├── current_week.json # Auto-detected current week
│   │   └── default.yaml      # Pipeline defaults
│   └── tests/                # Python tests
├── docs/                     # Technical documentation
├── plans/                    # Feature specifications
└── .github/                  # GitHub workflows
```

### Available Scripts

**Dashboard (from `dashboard/` directory):**
- `npm run dev` - Start frontend in development mode (port 5173)
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally

**Pipeline (from project root):**
- `python3 update_dashboard.py` - Run full pipeline and deploy
- `python3 update_dashboard.py --dry-run` - Preview changes without executing
- `python3 update_dashboard.py --skip-git` - Run pipeline without deployment

### Technology Stack

**Frontend (Static Site):**
- React 18 with TypeScript
- Vite for build tooling and dev server
- TanStack Query v5 for data fetching and caching
- React Router v6 for navigation
- Tailwind CSS for styling
- Lucide React for icons
- Chart.js with react-chartjs-2 for visualizations
- date-fns for date handling

**Data Pipeline (Python):**
- Python 3.9+
- pandas for data processing
- requests for API calls
- PyYAML for configuration
- pytest for testing

**Deployment:**
- Vercel for static hosting
- GitHub Actions for CI/CD (optional)

## 🔧 Configuration

### Environment Variables

**Frontend (.env):**
```env
VITE_DRIVE_FOLDER_ID=your_google_drive_folder_id
```

**Google Drive Configuration (Optional):**

The Commish Tiers Archive feature embeds a Google Drive folder for viewing weekly power rankings. To configure:

1. Create or identify your Google Drive folder containing Commish Tiers documents
2. Get the folder ID from the URL: `https://drive.google.com/drive/folders/[FOLDER_ID]`
3. Set `VITE_DRIVE_FOLDER_ID` in `dashboard/frontend/.env`
4. Ensure folder sharing is set to "Anyone with the link can view"

The folder ID is not sensitive and can be committed to version control since it's visible in the iframe URL anyway.

### Pipeline Configuration

**Week Detection:**
The pipeline automatically detects the current week from the Sleeper API and stores it in [`pipeline/config/current_week.json`](pipeline/config/current_week.json). This is used for standings, playoff scenarios, and draft order calculations.

**Manual Week Override (if needed):**
Edit `pipeline/config/current_week.json`:
```json
{
  "current_week": 14,
  "last_updated": "2024-12-15T10:30:00Z"
}
```

Then regenerate dashboard data with `python3 update_dashboard.py`.

## 📱 Usage

### Navigation

The dashboard includes six main pages accessible via the sidebar:

1. **Overview** - Trade analysis dashboard with manager rankings
2. **Standings** - Current week standings by division
3. **Playoff Scenarios** - Monte Carlo simulation results
4. **Draft Order** - Progressive 2026 draft order projections
5. **Waiver Wire** - Advanced waiver wire metrics
6. **Archive** - Commish Tiers power rankings

### Overview Page (Trade Analysis)

**Key Metrics:**
- Total trades, value exchanged, active traders
- Average trade margins and biggest swings

**Manager Rankings:**
- Sortable table with trade count, win rate, value gained
- Search and filter capabilities
- Performance tier filtering (winners/losers)

**Recent Trades:**
- Chronological trade history
- Click any trade for detailed modal view
- Search and date filtering

### Standings Page

**Current Week Standings:**
- Division-based standings (East/West)
- Win-Loss-Tie records
- Points For (PF) and Points Against (PA)
- Playoff positioning indicators

**Schedule Modal:**
- Click any team to view their schedule
- Shows past results and remaining matchups
- Color-coded wins/losses/upcoming games

### Playoff Scenarios Page

**Monte Carlo Simulations:**
- 10,000 simulated remaining season scenarios
- Playoff probability for each team
- Projected seed ranges and averages
- Clinch/elimination status indicators

**Key Metrics Per Team:**
- Playoff %
- Division Win %
- First Round Bye %
- Championship %
- Projected seed with confidence intervals

### Draft Order Projection Page

**Progressive Tracking:**
- Week-by-week 2026 draft order projections
- Shows how draft position changes throughout season
- Pick ownership analysis
- Current standings vs. projected draft position

**Features:**
- Historical progression charts
- Pick trading impact visualization
- Tiebreaker explanations

### Waiver Wire Analysis Page

**Advanced Metrics:**

1. **Hit Rate** - % of waiver claims that became regular starters
2. **Churn Index** - Add/drop activity normalized by league average
3. **Efficiency Score** - Weighted combination of hit rate and value
4. **Timing Score** - How well managers time their waiver claims

Each metric includes league averages and percentile rankings.

### Commish Tiers Archive

- **Embedded Google Drive folder** with weekly power rankings
- **Search and filter** documents by name
- **Preview and download** capabilities
- **Mobile responsive** with fallback link if embed fails

## 🚨 Troubleshooting

### Common Issues

1. **"Failed to Load Data" or Missing JSON Files**
   - **Cause:** Dashboard JSON files not generated or outdated
   - **Solution:** Run `python3 update_dashboard.py` from project root
   - **Check:** Verify files exist in `dashboard/frontend/public/api-*.json`
   - **Quick Test:** Check file timestamps with `ls -lh dashboard/frontend/public/api-*.json`

2. **Dashboard Shows Old/Stale Data**
   - **Cause:** JSON files not regenerated after Sleeper API changes
   - **Solution:** Run `python3 update_dashboard.py` to fetch latest data
   - **Automatic:** Set up a cron job or GitHub Action to run daily

3. **Standings/Playoffs Show Wrong Week**
   - **Cause:** Current week not detected correctly
   - **Check:** View `pipeline/config/current_week.json`
   - **Solution:** Manually update week number or re-run `python3 pipeline/scripts/detect_current_week.py`

4. **Vercel Deployment Not Updating**
   - **Cause:** JSON files not committed/pushed to GitHub
   - **Solution:** Ensure JSON files are committed: `git add dashboard/frontend/public/*.json`
   - **Check:** Verify commit appears on GitHub and Vercel deployment triggered
   - **Logs:** Check Vercel deployment logs for errors

5. **Playoff Simulations Not Running**
   - **Cause:** Missing current week or standings data
   - **Solution:** Ensure `pipeline/config/current_week.json` and standings data exist
   - **Test:** Run `python3 pipeline/scripts/simulate_playoff_scenarios.py` directly

6. **Waiver Wire Analysis Missing**
   - **Cause:** Stage 5 waiver wire analysis not run
   - **Solution:** Run `python3 pipeline/stage5_waiver_wire.py`
   - **Check:** Verify `pipeline/waiver_wire_stats.json` exists

7. **Draft Order Projection Errors**
   - **Cause:** Missing 2026 pick ownership data
   - **Solution:** Run `python3 pipeline/analyze_2026_pick_ownership.py`
   - **Then:** Run `python3 pipeline/scripts/calculate_progressive_draft_order.py`

### Pipeline Debugging

**See detailed logs during pipeline execution:**
```bash
python3 update_dashboard.py 2>&1 | tee pipeline_run.log
```

**Run specific stage only:**
```bash
cd pipeline
python3 scripts/detect_current_week.py       # Week detection
python3 stage1_fetch_trades.py               # Trade fetching
python3 scripts/fetch_standings.py           # Current standings
python3 scripts/simulate_playoff_scenarios.py # Playoff simulations
python3 scripts/calculate_progressive_draft_order.py # Draft order
```

**Check pipeline output files:**
```bash
ls -lh pipeline/*.json pipeline/*.csv
```

**Validate JSON files:**
```bash
cd dashboard/frontend/public
for f in api-*.json; do echo "=== $f ==="; jq . "$f" > /dev/null && echo "✓ Valid JSON" || echo "✗ Invalid JSON"; done
```

### Data Quality Issues

**Problem:** Dashboard shows incorrect player values

**Solution:** Values are cached from KeepTradeCut. To refresh:
```bash
cd pipeline
python3 stage3_cache_values.py  # Re-fetch all valuations
python3 update_dashboard.py      # Regenerate everything
```

**Problem:** Missing trades in dashboard

**Solution:** Full pipeline refresh:
```bash
python3 update_dashboard.py
```

**Problem:** Standings don't match Sleeper app

**Solution:**
1. Check current week is correct in `pipeline/config/current_week.json`
2. Re-fetch standings: `python3 pipeline/scripts/fetch_standings.py`
3. Verify league ID is correct in pipeline scripts

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Happy Trading! 🏈📈**