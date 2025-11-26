# Product Overview

Fantasy Football Trade Analysis Dashboard - a web application that analyzes dynasty fantasy football trades from Sleeper API, tracking team performance and identifying trading patterns.

## Core Features

- Real-time trade monitoring with automatic updates
- Manager skill rankings with win rates and value analysis
- Detailed trade history with filtering and search
- Performance analytics and trend analysis
- Interactive dashboard with responsive UI

## Data Flow

The system consists of two main components:

1. **Python Pipeline** (4-stage ETL process)
   - Fetches trades from Sleeper API
   - Extracts and values assets
   - Generates analysis CSV files
   - Produces JSON files for dashboard

2. **Web Dashboard** (React + Express)
   - Consumes JSON data files
   - Provides interactive UI for trade analysis
   - Real-time updates via WebSocket

## Key Data Files

- `league_trades_analysis_pipeline.csv` - Main analysis output
- `team_identity_mapping.csv` - Team name mappings
- `api-trades.json` - Trade data for dashboard
- `api-teams.json` - Team statistics
- `api-stats-summary.json` - League-wide metrics

## Deployment

- Frontend: Vercel (automatic deployment on push)
- Backend: Express server
- Pipeline: GitHub Actions (daily automated runs at 9 AM EST)
