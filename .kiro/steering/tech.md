# Technology Stack

## Frontend

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Data Fetching**: TanStack Query (React Query)
- **Routing**: React Router v6
- **Real-time**: Socket.io client
- **Icons**: Lucide React
- **Charts**: Chart.js with react-chartjs-2
- **Tables**: TanStack Table

## Backend

- **Runtime**: Node.js 18+
- **Framework**: Express.js with TypeScript
- **Real-time**: Socket.io
- **File Watching**: Chokidar
- **CSV Parsing**: PapaParse
- **Logging**: Winston

## Python Pipeline

- **Core**: Python 3.x with pandas
- **HTTP**: requests with tenacity (retry logic)
- **Config**: PyYAML
- **Testing**: pytest with coverage
- **Type Checking**: mypy
- **Code Quality**: black, flake8

## Common Commands

### Development

```bash
# Install all dependencies
npm run install:all

# Start development servers (frontend + backend)
npm run dev

# Start individual services
npm run dev:frontend  # Vite dev server on :5173
npm run dev:backend   # Express server on :3001
```

### Building

```bash
# Build both frontend and backend
npm run build

# Build individually
npm run build:frontend
npm run build:backend
```

### Testing

```bash
# Run all tests
npm test

# Test individually
npm run test:frontend
npm run test:backend

# Python tests
cd pipeline && pytest
```

### Code Quality

```bash
# Lint all code
npm run lint

# Format all code
npm run format

# Python formatting
cd pipeline && black .
```

### Pipeline Operations

```bash
# Full automated update (recommended)
python3 update_dashboard.py

# Manual stage-by-stage
python3 pipeline/stage1_fetch_trades.py
python3 pipeline/stage2_extract_assets.py
python3 pipeline/stage3_cache_values.py
python3 pipeline/stage4_final.py
python3 pipeline/scripts/generate_dashboard_json.py

# Update weekly standings
python3 update_weekly_standings.py

# Analyze 2026 pick ownership
python3 pipeline/analyze_2026_pick_ownership.py
```

### Deployment

```bash
# Production start
npm start

# Clean build artifacts
npm run clean
```

## Configuration Files

- `tsconfig.json` - TypeScript configuration (strict mode enabled)
- `vite.config.ts` - Vite build configuration
- `tailwind.config.js` - Tailwind CSS configuration
- `pipeline/config/default.yaml` - Pipeline configuration
- `vercel.json` - Vercel deployment configuration

## Environment Requirements

- Node.js >= 18.0.0
- npm >= 8.0.0
- Python 3.x
- Modern web browser
