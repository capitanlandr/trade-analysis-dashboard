# Project Structure

## Root Organization

```
├── dashboard/              # Web application
│   ├── backend/           # Express API server
│   └── frontend/          # React application
├── pipeline/              # Python ETL pipeline
├── .github/               # GitHub Actions workflows
└── [config files]         # Root-level configs
```

## Dashboard Structure

### Backend (`dashboard/backend/`)

```
backend/
├── src/
│   ├── routes/           # API endpoint definitions
│   ├── services/         # Business logic layer
│   │   ├── csvParser.ts      # CSV file parsing
│   │   ├── dataService.ts    # Data access layer
│   │   ├── fileWatcher.ts    # File change monitoring
│   │   └── teamResolver.ts   # Team name resolution
│   ├── middleware/       # Express middleware
│   │   ├── errorHandler.ts
│   │   └── requestLogger.ts
│   ├── types/           # TypeScript type definitions
│   └── server.ts        # Application entry point
└── api/                 # API route handlers
    └── status.ts
```

### Frontend (`dashboard/frontend/`)

```
frontend/
├── src/
│   ├── components/      # React components
│   │   ├── ErrorBoundary/   # Error handling
│   │   ├── Layout/          # Layout components
│   │   ├── Modals/          # Modal dialogs
│   │   ├── Notifications/   # Toast notifications
│   │   ├── Tables/          # Data tables
│   │   └── UI/              # Reusable UI components
│   ├── pages/           # Page-level components
│   │   ├── Overview.tsx
│   │   ├── Standings.tsx
│   │   └── PlayoffScenarios.tsx
│   ├── services/        # API client layer
│   │   └── api.ts
│   ├── hooks/           # Custom React hooks
│   │   ├── useDebounce.ts
│   │   ├── useRetry.ts
│   │   └── useWebSocket.ts
│   ├── types/           # TypeScript types
│   │   ├── index.ts
│   │   ├── playoff-scenarios.ts
│   │   ├── standings.ts
│   │   └── team.ts
│   └── utils/           # Utility functions
│       └── performance.ts
└── public/              # Static assets & data files
    ├── data/
    │   └── trades.json
    ├── api-trades.json
    ├── api-teams.json
    ├── api-stats-summary.json
    ├── api-standings.json
    └── api-playoff-scenarios.json
```

## Pipeline Structure (`pipeline/`)

```
pipeline/
├── stage1_fetch_trades.py      # Fetch from Sleeper API
├── stage2_extract_assets.py    # Extract trade assets
├── stage3_cache_values.py      # Value assets
├── stage4_final.py             # Generate final analysis
├── config/
│   └── default.yaml            # Pipeline configuration
├── scripts/                    # Utility scripts
│   ├── generate_dashboard_json.py
│   ├── fetch_standings.py
│   ├── calculate_playoff_scenarios.py
│   └── update_weekly_projections.py
├── utils/                      # Shared utilities
│   ├── api_client.py
│   ├── backup.py
│   ├── logging_config.py
│   ├── metrics.py
│   ├── team_resolver.py
│   └── validators.py
├── tests/                      # Test suite
│   ├── test_stage3_valuations.py
│   ├── test_stage4_calculations.py
│   └── test_team_resolver.py
├── backups/                    # Timestamped backups
├── logs/                       # Pipeline execution logs
└── metrics/                    # Performance metrics
```

## Key Files

### Configuration
- `package.json` - Root npm scripts and dependencies
- `vercel.json` - Vercel deployment config
- `pipeline/config/default.yaml` - Pipeline settings
- `pipeline/constants.py` - Python constants

### Data Files
- `league_trades_analysis_pipeline.csv` - Main analysis output
- `team_identity_mapping.csv` - Team name mappings
- `asset_transactions.csv` - Transaction history
- `asset_values_cache.csv` - Cached asset valuations
- `trades_raw.json` - Raw Sleeper API data

### Documentation
- `README.md` - Main documentation
- `QUICK_START.md` - Quick setup guide
- `CONTRIBUTING.md` - Contribution guidelines
- `MIGRATION_GUIDE.md` - Migration instructions
- `WEEKLY_UPDATE_GUIDE.md` - Weekly update process

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
