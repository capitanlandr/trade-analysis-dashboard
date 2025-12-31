# Product Overview

Fantasy Football Trade Analysis Dashboard - a comprehensive web application that analyzes dynasty fantasy football trades from Sleeper API, tracking team performance, standings, playoff scenarios, waiver wire efficiency, and 2026 draft order projections.

## Core Features

- **Trade Analysis**: Manager skill rankings with win rates, value analysis, and trade history
- **Standings & Playoffs**: Current standings with head-to-head records and simulated playoff scenarios
- **Waiver Wire Analysis**: Comprehensive waiver efficiency metrics (timing, churn, hit rate, efficiency scores)
- **Draft Order Tracking**: Progressive 2026 draft order projections updated weekly based on current standings
- **Commish Tiers Archive**: Historical integration with Google Drive-hosted Commish Tiers articles
- **Interactive Dashboard**: Responsive UI with real-time data updates

## Data Flow

The system consists of two main components:

1. **Python Pipeline** (12-stage ETL process)
   - Stages 1-4: Trade data fetching, asset extraction, valuation, and analysis
   - Stage 5: Waiver wire transaction processing
   - Stages 6-12: Weekly standings, playoff simulations, draft order projections, and JSON generation

2. **Static Web Dashboard** (React + Vite)
   - Consumes JSON data files from [`dashboard/frontend/public/`](../../dashboard/frontend/public/)
   - Static site deployment with no backend server
   - Pages: Overview, Standings, Playoff Scenarios, Waiver Wire, Draft Order, Archive

## Key Data Files

**Core Analysis:**
- `league_trades_analysis_pipeline.csv` - Main trade analysis output
- `team_identity_mapping.csv` - Team name mappings
- `asset_transactions.csv` - Transaction history
- `asset_values_cache.csv` - Cached asset valuations

**Dashboard JSON Files:**
- `api-trades.json` - Trade data with valuations
- `api-teams.json` - Team rosters and metadata
- `api-standings.json` - Current standings
- `api-playoff-scenarios.json` - Playoff simulations
- `api-waiver-wire.json` - Waiver wire metrics
- `api-draft-order.json` - 2026 draft order projections

**Weekly Data:**
- `standings_data.json` - Current week standings
- `playoff_scenarios_simulated.json` - Monte Carlo playoff simulations
- `draft_order_2026_progressive.json` - Weekly-updated draft order
- `pipeline/config/current_week.json` - Current week configuration

## Deployment

- **Frontend**: Vercel static site (automatic deployment on push to main)
- **Pipeline**: GitHub Actions (daily automated runs at 9 AM EST)
- **Architecture**: Static site with client-side routing, no backend server required
