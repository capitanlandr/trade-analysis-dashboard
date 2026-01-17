# Trade Analysis Dashboard

A comprehensive fantasy football analytics dashboard featuring trade analysis, live standings, playoff scenarios, draft order projections, and waiver wire metrics.

## Features

### Core Analytics
- 📊 **Trade Analysis**: Historical trades with value tracking and win/loss analysis
- 📈 **Manager Rankings**: Skill-based rankings with win rates and value metrics
- 🏆 **Live Standings**: Current week standings with division rankings
- 🎯 **Playoff Scenarios**: Monte Carlo simulations (10,000 scenarios) with probabilities
- 📋 **Draft Order Projection**: Progressive 2026 draft order tracking
- 🔄 **Waiver Wire Analysis**: Hit rate, churn index, efficiency, and timing scores
- 📚 **Commish Tiers Archive**: Browse and download weekly power rankings

### Technical Features
- ⚡ Static site (no backend server required)
- 🔥 Fast page loads with pre-generated JSON data
- 📱 Responsive design for mobile and desktop
- 🎨 Modern UI with Tailwind CSS
- 🔍 TanStack Query for efficient data fetching and caching
- ♿ Error boundaries and retry mechanisms

## Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

1. Install dependencies:
```bash
cd dashboard
npm install
```

2. Start development server:
```bash
npm run dev
```

3. Open browser:
```
http://localhost:5173
```

### Production Build

```bash
npm run build
npm run preview
```

## Project Structure

```
dashboard/
├── frontend/                 # React application (Vite + TypeScript)
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── Archive/      # Commish Tiers Archive
│   │   │   ├── Layout/       # Dashboard layout
│   │   │   ├── Modals/       # Trade/Schedule modals
│   │   │   ├── Tables/       # Data tables
│   │   │   ├── UI/           # Shared UI components
│   │   │   └── WaiverWire/   # Waiver wire metric cards
│   │   ├── pages/            # Page components
│   │   │   ├── Overview.tsx
│   │   │   ├── Standings.tsx
│   │   │   ├── PlayoffScenarios.tsx
│   │   │   ├── DraftOrderProjection.tsx
│   │   │   ├── WaiverWireAnalysis.tsx
│   │   │   └── CommishTiersArchive.tsx
│   │   ├── services/         # API client for JSON files
│   │   ├── hooks/            # Custom React hooks
│   │   └── types/            # TypeScript type definitions
│   └── public/               # Static JSON data files
│       ├── api-trades.json
│       ├── api-teams.json
│       ├── api-stats-summary.json
│       ├── api-standings.json
│       ├── api-playoff-scenarios.json
│       ├── waiver-wire-page.json
│       └── api-draft-order.json
└── backend.ARCHIVED/         # Legacy backend (no longer used)
```

## Data Architecture

### Static JSON Approach

The dashboard uses **pre-generated JSON files** rather than a backend API:

**Advantages:**
- ⚡ Instant page loads (no API calls to process)
- 💰 Zero hosting costs (static hosting is free)
- 🔒 No server security concerns
- 📈 Scales infinitely
- 🌐 Works with CDN caching

**Data Generation:**
The Python pipeline (`../pipeline/`) generates all JSON files:

```bash
# From project root
python3 update_dashboard.py
```

This creates all 7 JSON files in `frontend/public/`.

### Data Files

**api-trades.json** - Trade analysis
- Historical trades with value tracking
- Win/loss analysis per trade
- Asset valuations over time

**api-teams.json** - Manager statistics
- Trade count and win rate
- Total value gained/lost
- Performance rankings

**api-stats-summary.json** - League-wide stats
- Total trades and value exchanged
- Most active traders
- Biggest winners/losers

**api-standings.json** - Current standings
- Division-based standings (East/West)
- Win-Loss-Tie records
- Points For/Against
- Playoff positioning

**api-playoff-scenarios.json** - Simulation results
- 10,000 Monte Carlo simulations
- Playoff probability per team
- Projected seeds and ranges
- Clinch/elimination status

**waiver-wire-page.json** - Waiver metrics
- Hit Rate: % of claims becoming starters
- Churn Index: Add/drop activity
- Efficiency Score: Weighted hit rate + value
- Timing Score: Claim timing effectiveness

**api-draft-order.json** - Draft projections
- Progressive week-by-week projections
- 2026 pick ownership tracking
- Tiebreaker scenarios

See [`frontend/public/README.md`](frontend/public/README.md) for detailed schemas.

## Configuration

### Environment Variables

Create `frontend/.env`:

```env
# Optional: For Commish Tiers Archive feature
VITE_DRIVE_FOLDER_ID=your_google_drive_folder_id
```

The Google Drive folder ID is the only optional configuration needed.

## Development

### Available Scripts

**From `dashboard/` directory:**

- `npm install` - Install dependencies
- `npm run dev` - Start dev server (port 5173)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 5
- **Styling**: Tailwind CSS 3
- **Data Fetching**: TanStack Query v5
- **Routing**: React Router v6
- **Charts**: Chart.js with react-chartjs-2
- **Icons**: Lucide React
- **Date Handling**: date-fns

### Code Organization

**Components:**
- Atomic design approach (UI → Components → Pages)
- Shared UI components in `components/UI/`
- Feature-specific components in dedicated folders
- Error boundaries for resilience

**Data Management:**
- TanStack Query for caching and refetching
- Automatic refetch on window focus
- 5-minute stale time for dashboard data
- Retry logic with exponential backoff

**Type Safety:**
- Strict TypeScript configuration
- Comprehensive type definitions in `types/`
- No `any` types (enforced by ESLint)

## Deployment

### Vercel (Recommended)

The dashboard is configured for zero-config Vercel deployment:

1. Push to GitHub
2. Connect repository to Vercel
3. Deploy automatically

**Build Settings (Auto-detected):**
- Framework Preset: Vite
- Build Command: `cd dashboard && npm install && npm run build`
- Output Directory: `dashboard/frontend/dist`
- Install Command: `npm install`

### Manual Deployment

Build locally and deploy static files:

```bash
npm run build
# Upload 'dist' folder to any static host
```

## Updating Data

The dashboard displays static data from JSON files. To update:

**Automated (GitHub Actions):**
Runs daily at 9 AM EST automatically.

**Manual:**
```bash
# From project root
python3 update_dashboard.py
```

This regenerates all JSON files and triggers Vercel deployment.

## Troubleshooting

### Data Not Loading

**Symptom:** "Failed to fetch data" errors

**Solution:**
1. Check JSON files exist in `frontend/public/api-*.json`
2. Verify files are valid JSON: `jq . frontend/public/api-trades.json`
3. Regenerate data: `python3 ../update_dashboard.py`

### Build Failures

**Symptom:** `npm run build` fails

**Solution:**
1. Check TypeScript errors: `npm run lint`
2. Clear cache: `rm -rf node_modules dist && npm install`
3. Check Node version: `node --version` (needs 18+)

### Archive Page Not Loading

**Symptom:** Commish Tiers Archive shows blank

**Solution:**
1. Verify `VITE_DRIVE_FOLDER_ID` is set
2. Check folder is set to "Anyone with link can view"
3. Test folder URL directly in browser

## Contributing

See [../CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [../LICENSE](../LICENSE) for details.
