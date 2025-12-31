# Technology Stack

## Frontend

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite (static site generation)
- **Styling**: Tailwind CSS
- **Routing**: React Router v6 (client-side routing)
- **Icons**: Lucide React
- **Error Handling**: Component-level error boundaries
- **State Management**: React hooks and context
- **Type Safety**: TypeScript with strict mode

## Python Pipeline

- **Core**: Python 3.x with pandas, numpy
- **HTTP**: requests with tenacity (retry logic) and caching
- **Config**: PyYAML for pipeline configuration
- **Data Processing**: pandas for CSV/JSON manipulation
- **Testing**: pytest with fixtures and mocking
- **Validation**: Custom validators for data integrity
- **Logging**: Structured logging with rotation

## Common Commands

### Development

```bash
# Install dependencies
npm install                    # Frontend dependencies
pip install -r pipeline/requirements.txt  # Pipeline dependencies

# Start development server
npm run dev                    # Vite dev server on :5173
# or
cd dashboard/frontend && npm run dev
```

### Building

```bash
# Build frontend for production
npm run build                  # Creates dashboard/frontend/dist/
# or
cd dashboard/frontend && npm run build
```

### Testing

```bash
# Frontend tests
npm run test                   # Run frontend tests
# or
cd dashboard/frontend && npm run test

# Python pipeline tests
cd pipeline && pytest          # Run all tests
cd pipeline && pytest -v       # Verbose output
cd pipeline && pytest --cov    # With coverage report
```

### Pipeline Operations

#### Full Update (Recommended)
```bash
# Complete 12-stage pipeline update
python3 update_dashboard.py
```

#### Weekly Update (During Season)
```bash
# Stages 6-12: Weekly standings, playoffs, draft order
python3 update_weekly_standings.py
```

#### Quick Refresh (Local Development)
```bash
# Regenerate JSON without re-fetching API data
python3 refresh_local_data.py
```

#### Manual Stage-by-Stage Execution
```bash
# Stages 1-5: Trade and waiver data
python3 pipeline/stage1_fetch_trades.py
python3 pipeline/stage2_extract_assets.py
python3 pipeline/stage3_cache_values.py
python3 pipeline/stage4_final.py
python3 pipeline/stage5_waiver_wire.py

# Stages 6-12: Weekly data and dashboard JSON
python3 pipeline/scripts/fetch_standings.py
python3 pipeline/scripts/detect_current_week.py
python3 pipeline/scripts/calculate_progressive_draft_order.py
python3 pipeline/scripts/update_weekly_projections.py
python3 pipeline/scripts/simulate_playoff_scenarios.py
python3 pipeline/scripts/generate_dashboard_json.py
python3 pipeline/scripts/generate_waiver_wire_dashboard_json.py
```

#### Specialized Scripts
```bash
# Analyze 2026 draft pick ownership
python3 pipeline/analyze_2026_pick_ownership.py

# Health check and validation
python3 pipeline/health_check.py

# Explore Sleeper API capabilities
python3 pipeline/scripts/analyze_sleeper_api.py
```

### Deployment

```bash
# Deploy to Vercel (automatic on git push)
git push origin main           # Triggers automatic deployment

# Manual Vercel deployment
vercel --prod                  # Deploy to production
vercel                         # Deploy to preview

# Clean build artifacts
rm -rf dashboard/frontend/dist/
rm -rf dashboard/frontend/node_modules/
```

## Configuration Files

### Frontend
- `tsconfig.json` - TypeScript configuration (strict mode enabled)
- `vite.config.ts` - Vite build configuration with path aliases
- `tailwind.config.js` - Tailwind CSS theme and plugin configuration
- `postcss.config.js` - PostCSS configuration for Tailwind
- `vercel.json` - Vercel static site deployment configuration

### Pipeline
- `pipeline/config/default.yaml` - League and API configuration
- `pipeline/config/current_week.json` - Auto-updated current week tracker
- `pipeline/constants.py` - API endpoints and constants
- `pipeline/requirements.txt` - Python dependencies

### Root
- `package.json` - Workspace scripts and frontend dependencies
- `.gitignore` - Git ignore patterns for build artifacts and data files

## Environment Requirements

- **Node.js**: >= 18.0.0
- **npm**: >= 8.0.0
- **Python**: 3.9+ (tested on 3.9, 3.10, 3.11)
- **Browser**: Modern browser with ES6+ support
- **Git**: For version control and deployments

## Architecture Notes

### Static Site Approach
- No backend server required
- All data served as static JSON files
- Client-side routing with React Router
- Deployed as Jamstack application on Vercel

### Data Flow
1. Python pipeline generates JSON files → `dashboard/frontend/public/`
2. Vite build includes public files in distribution
3. React app fetches JSON files at runtime
4. No API server, database, or real-time connections needed

### Key Benefits
- **Simple Deployment**: Single static site, no server management
- **Fast Performance**: Static files served via CDN
- **Easy Local Development**: No backend setup required
- **Reliable**: No server to crash or scale
- **Cost-Effective**: Free hosting on Vercel

### Data Update Flow
1. GitHub Actions runs daily at 9 AM EST
2. Executes `update_dashboard.py` (full 12-stage pipeline)
3. Commits updated JSON files to repository
4. Vercel automatically deploys updated site
5. Dashboard reflects new data within minutes
