# Fantasy Football Trade Analysis Dashboard

A comprehensive web application for analyzing fantasy football trades, tracking team performance, and identifying trading patterns in your league.

## 🏆 Features

- **Real-time Trade Monitoring**: Automatically updates when new trade data is available (Last updated: 2025-11-04)
- **Manager Rankings**: Comprehensive skill-based rankings with win rates and value analysis
- **Trade History**: Detailed trade logs with filtering and search capabilities
- **Performance Analytics**: Team performance metrics and trend analysis
- **Commish Tiers Archive**: Browse and download weekly power rankings from embedded Google Drive folder
- **Interactive Dashboard**: Modern, responsive UI with real-time updates
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

2. **Run setup script**
   ```bash
   ./setup.sh
   ```

3. **Start the application**
   ```bash
   npm run dev
   ```

4. **Open your browser**
   Navigate to `http://localhost:5173`

## 📊 Data Pipeline Integration

This dashboard is powered by a Python pipeline that processes Sleeper API data. The pipeline runs in the parent directory and generates the data files this dashboard consumes.

### Data Flow

```
Sleeper API
    ↓
Python Pipeline (4 stages)
    ↓
CSV Files (league_trades_analysis_pipeline.csv, team_identity_mapping.csv)
    ↓
JSON Generation (scripts/generate_dashboard_json.py)
    ↓
Dashboard JSON Files (api-trades.json, api-teams.json, api-stats-summary.json)
    ↓
React Dashboard (this application)
```

### Updating Dashboard Data

**Automated (Recommended):**
```bash
cd ..  # Go to parent directory
python3 update_dashboard.py
```

This single command:
1. Fetches latest trades from Sleeper
2. Processes and values all assets
3. Generates CSV and JSON files
4. Copies files to dashboard directory
5. Commits and pushes to GitHub
6. Triggers Vercel deployment

**Manual:**
```bash
cd ..  # Go to parent directory
python3 stage1_fetch_trades.py
python3 stage2_extract_assets.py
python3 stage3_cache_values.py
python3 stage4_final.py
python3 scripts/generate_dashboard_json.py

# Then commit and push the generated JSON files
cd trade-analysis-dashboard-clean
git add dashboard/frontend/public/*.json
git commit -m "data: update dashboard data"
git push origin main
```

### Data Files

The dashboard reads from JSON files in `dashboard/frontend/public/`:

**api-trades.json** - Trade data
```json
{
  "success": true,
  "data": {
    "trades": [
      {
        "tradeId": "123",
        "tradeDate": "2025-09-30",
        "teamA": "manager1",
        "teamAReceived": ["Player A", "2026 Round 1"],
        "teamAValueThen": 5000,
        "teamAValueNow": 5500,
        "teamB": "manager2",
        "teamBReceived": ["Player B"],
        "teamBValueThen": 4800,
        "teamBValueNow": 4200,
        "winnerCurrent": "manager1",
        "swingMargin": 800
      }
    ]
  }
}
```

**api-teams.json** - Team statistics
```json
{
  "success": true,
  "data": {
    "teams": [
      {
        "sleeperUsername": "manager1",
        "realName": "John Doe",
        "teamName": "Team Name",
        "tradeCount": 15,
        "winRate": 73.3,
        "totalValueGained": 2500
      }
    ]
  }
}
```

**api-stats-summary.json** - League-wide statistics
```json
{
  "success": true,
  "data": {
    "overview": {
      "totalTrades": 70,
      "avgTradeMargin": 850,
      "mostActiveTrader": "John Doe",
      "biggestWinner": "Jane Smith"
    }
  }
}
```

## 🛠️ Development

### Project Structure

```
├── dashboard/
│   ├── backend/          # Express.js API server
│   │   ├── src/
│   │   │   ├── routes/   # API endpoints
│   │   │   ├── services/ # Business logic
│   │   │   └── utils/    # Utilities
│   │   └── package.json
│   └── frontend/         # React application
│       ├── src/
│       │   ├── components/ # React components
│       │   ├── pages/      # Page components
│       │   ├── services/   # API clients
│       │   ├── hooks/      # Custom hooks
│       │   └── types/      # TypeScript types
│       └── package.json
├── pipeline_outputs/     # CSV data files
└── .github/             # GitHub workflows and templates
```

### Available Scripts

- `npm run dev` - Start both frontend and backend in development mode
- `npm run build` - Build both applications for production
- `npm run start` - Start production server
- `npm test` - Run all tests
- `npm run lint` - Run linting on all code

### Technology Stack

**Frontend:**
- React 18 with TypeScript
- Vite for build tooling
- TanStack Query for data fetching
- Tailwind CSS for styling
- Lucide React for icons

**Backend:**
- Node.js with Express
- TypeScript
- Socket.io for real-time updates
- Chokidar for file watching
- CSV parsing utilities

## 🔧 Configuration

### Environment Variables

The setup script creates `.env` files automatically, but you can customize:

**Backend (.env):**
```env
PORT=3001
NODE_ENV=development
CORS_ORIGIN=http://localhost:5173
```

**Frontend (.env):**
```env
VITE_API_BASE_URL=http://localhost:3001/api
VITE_DRIVE_FOLDER_ID=your_google_drive_folder_id
```

**Google Drive Configuration:**

The Commish Tiers Archive feature embeds a Google Drive folder for viewing weekly power rankings. To configure:

1. Create or identify your Google Drive folder containing Commish Tiers documents
2. Get the folder ID from the URL: `https://drive.google.com/drive/folders/[FOLDER_ID]`
3. Set `VITE_DRIVE_FOLDER_ID` in `dashboard/frontend/.env`
4. Ensure folder sharing is set to "Anyone with the link can view"

The folder ID is not sensitive and can be committed to version control since it's visible in the iframe URL anyway.

## 📱 Usage

### Dashboard Overview

The main dashboard provides:
- **Key Metrics**: Total trades, value, active traders, average margins
- **League Leaders**: Most active traders and biggest winners
- **Manager Rankings**: Sortable table with performance metrics
- **Recent Trades**: Detailed trade history with filtering

### Manager Rankings

- **Search**: Find specific managers
- **Filters**: Minimum trades, performance tiers
- **Sorting**: Click column headers to sort by different metrics
- **Performance Tiers**: Filter by winners/losers

### Trade Analysis

- **Detailed View**: Click any trade for comprehensive details
- **Filtering**: By date range, teams, or trade value
- **Search**: Find trades by team names or player assets
- **Real-time Updates**: Automatically refreshes with new data

### Commish Tiers Archive

- **Browse Documents**: View all weekly power rankings in embedded Google Drive folder
- **Preview & Download**: Click any document to preview or download
- **Mobile Responsive**: Optimized viewing on all device sizes
- **Direct Access**: Fallback link provided if embed fails to load

## 🚨 Troubleshooting

### Common Issues

1. **"Failed to Load Data"**
   - **Cause:** JSON files missing or not generated
   - **Solution:** Run `cd .. && python3 update_dashboard.py`
   - **Check:** Verify files exist in `dashboard/frontend/public/api-*.json`

2. **Dashboard Shows Old Data**
   - **Cause:** JSON files not regenerated after pipeline run
   - **Solution:** Always run `scripts/generate_dashboard_json.py` after Stage 4
   - **Quick Fix:** Use `update_dashboard.py` which handles this automatically

3. **Vercel Deployment Not Updating**
   - **Cause:** JSON files not committed/pushed to GitHub
   - **Solution:** Ensure JSON files are committed and pushed
   - **Check:** Verify commit appears on GitHub and Vercel deployment triggered

4. **Real-time Updates Not Working**
   - Ensure WebSocket connection is established
   - Check browser console for connection errors
   - Verify file watching permissions

5. **Performance Issues**
   - Large datasets may cause slow rendering
   - Consider implementing pagination for 100+ trades
   - Check browser memory usage

### Pipeline Integration Issues

**Problem:** Dashboard shows incorrect player values

**Solution:** Use the value correction script:
```bash
cd ..  # Go to parent directory
python3 fix_tyreek_value.py  # Edit script for specific player/value
```

**Problem:** Missing trades in dashboard

**Solution:** Run full pipeline refresh:
```bash
cd ..
python3 update_dashboard.py
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Happy Trading! 🏈📈**