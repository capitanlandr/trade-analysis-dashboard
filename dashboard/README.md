# Trade Analysis Dashboard

A real-time web dashboard for fantasy football trade analysis, built to visualize and interact with trade data from your existing pipeline.

## Features

- 📊 Interactive trade tables with sorting and filtering
- 📈 Team performance charts and visualizations  
- 🔥 Blockbuster trade highlights
- ⚡ Real-time updates when new trades are processed
- 📱 Responsive design for mobile and desktop

## Quick Start

### Prerequisites
- Node.js 18+ 
- Your existing trade analysis pipeline outputs

### Installation

1. Install all dependencies:
```bash
cd dashboard
npm run install:all
```

2. Start the development servers:
```bash
npm run dev
```

This will start:
- Frontend: http://localhost:3000
- Backend API: http://localhost:3001

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
dashboard/
├── frontend/          # React TypeScript frontend
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Page components
│   │   └── types/         # TypeScript interfaces
├── backend/           # Express TypeScript API
│   └── src/
│       ├── routes/        # API route handlers
│       ├── services/      # Business logic
│       └── types/         # Shared type definitions
└── package.json       # Root package with scripts
```

## Configuration

The dashboard reads your pipeline CSV outputs from:
- `league_trades_analysis_pipeline.csv` - Main trade data
- `team_identity_mapping.csv` - Team name mappings
- `3team_trades_analysis.json` - Multi-team trades (if any)

Configure the file paths in `backend/src/config.ts` to match your pipeline output directory.

## Deployment

Ready for free deployment to Vercel:

1. Push to GitHub
2. Connect repository to Vercel
3. Deploy automatically

See deployment documentation for detailed setup instructions.

## Development

- `npm run dev` - Start both frontend and backend in development mode
- `npm run build` - Build both applications for production
- Frontend runs on port 3000, backend on port 3001
- Hot reload enabled for both frontend and backend changes