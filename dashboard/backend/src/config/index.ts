export const config = {
  port: process.env.PORT || 3001,
  nodeEnv: process.env.NODE_ENV || 'development',
  
  // Pipeline file paths - read from local dashboard directory
  pipelineFiles: {
    tradesAnalysis: process.env.TRADES_FILE || '../../league_trades_analysis_pipeline.csv',
    teamIdentity: process.env.TEAMS_FILE || '../../team_identity_mapping.csv',
    multiTeamTrades: process.env.MULTI_TEAM_FILE || '../../3team_trades_analysis.json'
  },
  
  // CORS settings
  cors: {
    origin: process.env.NODE_ENV === 'production' 
      ? process.env.FRONTEND_URL || false 
      : ['http://localhost:3000', 'http://localhost:5173'],
    methods: ['GET', 'POST'],
    credentials: true
  },
  
  // File watching settings
  fileWatch: {
    debounceMs: 1000, // Wait 1 second after file changes before processing
    pollInterval: 5000 // Check for changes every 5 seconds
  },
  
  // Cache settings
  cache: {
    ttlMs: 5 * 60 * 1000, // 5 minutes
    maxSize: 100 // Maximum number of cached items
  }
};