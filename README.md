# Fantasy Football Trade Analysis Dashboard

A comprehensive web application for analyzing fantasy football trades, tracking team performance, and identifying trading patterns in your league.

## 🏆 Features

- **Real-time Trade Monitoring**: Automatically updates when new trade data is available (Last updated: 2025-11-04)
- **Manager Rankings**: Comprehensive skill-based rankings with win rates and value analysis
- **Trade History**: Detailed trade logs with filtering and search capabilities
- **Performance Analytics**: Team performance metrics and trend analysis
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

## 📊 Data Format

The dashboard expects CSV files in the `pipeline_outputs` directory:

### trades.csv
```csv
tradeId,tradeDate,teamA,teamB,teamAReceived,teamBReceived,winnerCurrent,marginCurrent
trade_001,2024-01-15,Team1,Team2,"Player A,Player B","Player C",Team1,15.5
```

### teams.csv
```csv
sleeperUsername,realName,tradeCount,totalValueGained,winRate
user123,John Doe,5,125.5,80.0
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
```

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

## 🚨 Troubleshooting

### Common Issues

1. **"Failed to Load Data"**
   - Check that CSV files exist in `pipeline_outputs/`
   - Verify file format matches expected structure
   - Check backend server is running

2. **Real-time Updates Not Working**
   - Ensure WebSocket connection is established
   - Check browser console for connection errors
   - Verify file watching permissions

3. **Performance Issues**
   - Large datasets may cause slow rendering
   - Consider implementing pagination for 100+ trades
   - Check browser memory usage

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Happy Trading! 🏈📈**