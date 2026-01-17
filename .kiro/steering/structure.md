# Project Structure

## Root Organization

```
├── dashboard/              # Web application
│   └── frontend/          # React static site application
├── pipeline/              # Python ETL pipeline (12 stages)
├── plans/                 # Planning and specification documents
├── docs/                  # Detailed technical documentation
├── .github/               # GitHub Actions workflows
├── .kiro/                 # Kiro AI mode configuration
└── [config files]         # Root-level configs
```

## Dashboard Structure

### Frontend (`dashboard/frontend/`)

```
frontend/
├── src/
│   ├── components/      # React components
│   │   ├── Archive/         # Commish Tiers Archive components
│   │   ├── ErrorBoundary/   # Error handling
│   │   ├── Layout/          # Layout components (DashboardLayout)
│   │   ├── Modals/          # Modal dialogs (TeamSchedule, TradeDetail)
│   │   ├── Tables/          # Data tables (Division, ManagerRankings, RecentTrades)
│   │   ├── UI/              # Reusable UI components (Loading, Error, Skeleton)
│   │   └── WaiverWire/      # Waiver wire metric cards
│   ├── pages/           # Page-level components
│   │   ├── Overview.tsx              # Main dashboard (trades, manager rankings)
│   │   ├── Standings.tsx             # Current standings with H2H records
│   │   ├── PlayoffScenarios.tsx      # Playoff simulation viewer
│   │   ├── WaiverWireAnalysis.tsx    # Waiver wire metrics page
│   │   ├── DraftOrderProjection.tsx  # 2026 draft order tracking
│   │   └── CommishTiersArchive.tsx   # Google Drive archive integration
│   ├── services/        # Data fetching layer
│   │   └── api.ts                    # Static JSON file loader
│   ├── hooks/           # Custom React hooks
│   │   ├── useDebounce.ts
│   │   └── useRetry.ts
│   ├── types/           # TypeScript types
│   │   ├── index.ts                  # Core types (Trade, Team, Manager)
│   │   ├── standings.ts              # Standings types
│   │   ├── playoff-scenarios.ts      # Playoff simulation types
│   │   ├── waiver-wire.ts            # Waiver wire metric types
│   │   ├── draft-order.ts            # Draft order projection types
│   │   └── archive.ts                # Archive configuration types
│   ├── config/          # Configuration
│   │   └── archive.ts               # Google Drive archive links
│   └── utils/           # Utility functions
└── public/              # Static assets & data files
    ├── data/
    │   └── trades.json                       # Legacy data location
    ├── api-trades.json                       # Trade analysis
    ├── api-teams.json                        # Team rosters
    ├── api-standings.json                    # Current standings
    ├── api-playoff-scenarios.json            # Playoff simulations
    ├── waiver-wire-page.json                  # Waiver wire metrics
    ├── api-draft-order.json                  # Draft order projections
    └── README.md                             # Data generation guide
```

## Pipeline Structure (`pipeline/`)

```
pipeline/
├── stage1_fetch_trades.py          # Stage 1: Fetch trades from Sleeper API
├── stage2_extract_assets.py        # Stage 2: Extract trade assets
├── stage3_cache_values.py          # Stage 3: Cache asset valuations
├── stage4_final.py                 # Stage 4: Generate trade analysis
├── stage5_waiver_wire.py           # Stage 5: Process waiver transactions
├── config/
│   ├── default.yaml                # Pipeline configuration
│   └── current_week.json           # Current week tracking (auto-updated)
├── scripts/                        # Additional pipeline stages & utilities
│   ├── fetch_standings.py                      # Stage 6: Fetch standings
│   ├── detect_current_week.py                  # Stage 7: Detect current week
│   ├── calculate_progressive_draft_order.py    # Stage 8: Calculate draft order
│   ├── update_weekly_projections.py            # Stage 9: Update weekly projections
│   ├── simulate_playoff_scenarios.py           # Stage 10: Simulate playoffs
│   ├── generate_dashboard_json.py              # Stage 11: Generate dashboard JSON
│   ├── generate_waiver_wire_dashboard_json.py  # Stage 12: Generate waiver JSON
│   ├── analyze_sleeper_api.py                  # API exploration utility
│   ├── explore_waiver_wire_api.py              # Waiver wire exploration
│   └── validate_rollback.py                    # Rollback validation
├── utils/                      # Shared utilities
│   ├── api_client.py           # Sleeper API client with caching
│   ├── backup.py               # Backup management
│   ├── logging_config.py       # Logging configuration
│   ├── metrics.py              # Performance metrics
│   ├── team_resolver.py        # Team name resolution
│   ├── validators.py           # Data validation
│   └── week_config.py          # Week configuration utilities
├── tests/                      # Test suite
│   ├── conftest.py
│   ├── test_stage3_valuations.py
│   ├── test_stage4_calculations.py
│   └── test_team_resolver.py
└── backups/                    # Timestamped data backups
```

## Root-Level Pipeline Scripts

```
├── update_dashboard.py         # Master script: runs full 12-stage pipeline
├── update_weekly_standings.py  # Weekly update: stages 6-12 only
├── refresh_local_data.py       # Quick refresh without re-fetching API data
└── health_check.py             # Pipeline health monitoring
```

## Key Files

### Configuration
- `package.json` - Root npm scripts and dependencies
- `vercel.json` - Vercel static site deployment config
- `pipeline/config/default.yaml` - Pipeline settings and league configuration
- `pipeline/config/current_week.json` - Auto-updated current week tracking
- `pipeline/constants.py` - Python constants and API configuration

### Data Files (Generated by Pipeline)
- `league_trades_analysis_pipeline.csv` - Main trade analysis output
- `team_identity_mapping.csv` - Team name mappings
- `asset_transactions.csv` - Transaction history
- `asset_values_cache.csv` - Cached asset valuations
- `trades_raw.json` - Raw Sleeper API trade data
- `waiver_transactions_raw.json` - Raw waiver wire data
- `standings_data.json` - Current standings with H2H records
- `playoff_scenarios_simulated.json` - Monte Carlo playoff simulations
- `draft_order_2026_progressive.json` - Weekly draft order projections
- `2026_pick_ownership_detailed.json` - Draft pick ownership tracking

### Dashboard JSON Files (in [`dashboard/frontend/public/`](../../dashboard/frontend/public/))
- `api-trades.json` - Trade analysis with valuations
- `api-teams.json` - Team rosters and metadata
- `api-standings.json` - Current standings
- `api-playoff-scenarios.json` - Playoff simulation results
- `waiver-wire-page.json` - Waiver wire efficiency metrics
- `api-draft-order.json` - Draft order projections

### Documentation
- [`README.md`](../../README.md) - Main documentation
- [`QUICK_START.md`](../../QUICK_START.md) - Quick setup guide
- [`DEPLOYMENT.md`](../../DEPLOYMENT.md) - Deployment instructions
- [`WEEKLY_UPDATE_GUIDE.md`](../../WEEKLY_UPDATE_GUIDE.md) - Weekly update process
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) - Contribution guidelines
- [`docs/guides/`](../../docs/guides/) - Technical architecture guides
- [`plans/`](../../plans/) - Planning and specification documents

## Naming Conventions

- **TypeScript**: PascalCase for components, camelCase for functions/variables
- **Python**: snake_case for files, functions, and variables
- **CSS**: kebab-case for class names (Tailwind)
- **Files**: Descriptive names with stage prefixes for pipeline files
- **Backups**: Timestamped format `stage{N}_{name}_{YYYYMMDD_HHMMSS}.{ext}`

## Import Patterns

### Frontend
- Absolute imports from `src/` root
- Component imports: `import { Component } from '@/components/...'`
- Type imports: `import type { Type } from '@/types/...'`

### Backend
- ES modules with `.js` extensions in imports
- Service layer imports: `import { service } from './services/...'`

### Pipeline
- Relative imports within pipeline directory
- Utility imports: `from utils.module import function`
