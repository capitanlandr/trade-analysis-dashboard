export const config = {
  port: process.env.PORT || 3001,
  nodeEnv: process.env.NODE_ENV || 'development',
  
  // Pipeline file paths - adjust these to match your pipeline output directory
  pipelineFiles: {
    tradesAnalysis: process.env.TRADES_FILE || (process.env.NODE_ENV === 'production' ? './league_trades_analysis_pipeline.csv' : '../../league_trades_analysis_pipeline.csv'),
    teamIdentity: process.env.TEAMS_FILE || (process.env.NODE_ENV === 'production' ? './team_identity_mapping.csv' : '../../team_identity_mapping.csv'),
    multiTeamTrades: process.env.MULTI_TEAM_FILE || (process.env.NODE_ENV === 'production' ? './3team_trades_analysis.json' : '../../3team_trades_analysis.json')
  },
  
  // CORS settings
  cors: {
    origin: process.env.NODE_ENV === 'production' 
      ? process.env.FRONTEND_URL || false 
      : ['http://localhost:3000'],
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