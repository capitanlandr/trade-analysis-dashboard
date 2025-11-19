import express from 'express'
import cors from 'cors'
import { createServer } from 'http'
import { Server } from 'socket.io'
import winston from 'winston'
// Force reload - asset values fix

import { config } from './config/index.js'
import { requestLogger } from './middleware/requestLogger.js'
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js'
import { ApiResponse } from './types/index.js'
import { DataService } from './services/dataService.js'
import { FileWatcher } from './services/fileWatcher.js'
import { createTradesRouter } from './routes/trades.js'
import { createTeamsRouter } from './routes/teams.js'
import { createStatsRouter } from './routes/stats.js'

// Configure logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
})

const app = express()
const server = createServer(app)
const io = new Server(server, {
  cors: config.cors
})

// Initialize services
const dataService = new DataService()
const fileWatcher = new FileWatcher()

// Middleware
app.use(cors(config.cors))
app.use(express.json({ limit: '10mb' }))
app.use(express.urlencoded({ extended: true }))
app.use(requestLogger)

// Health check endpoint
app.get('/api/health', (req, res) => {
  const response: ApiResponse = {
    success: true,
    data: {
      status: 'ok',
      environment: config.nodeEnv,
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      version: '1.0.0'
    },
    timestamp: new Date().toISOString()
  }
  res.json(response)
})

// API status endpoint
app.get('/api/status', async (req, res) => {
  try {
    const fileStatus = await dataService.getFileStatus()
    const lastUpdate = dataService.getLastUpdate()
    
    const response: ApiResponse = {
      success: true,
      data: {
        message: 'Trade Analysis Dashboard API is running',
        pipelineFiles: config.pipelineFiles,
        fileStatus,
        lastDataUpdate: lastUpdate?.toISOString() || null,
        connectedClients: io.engine.clientsCount
      },
      timestamp: new Date().toISOString()
    }
    res.json(response)
  } catch (error) {
    const response: ApiResponse = {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    }
    res.status(500).json(response)
  }
})

// Load data endpoint
app.get('/api/data/load', async (req, res) => {
  try {
    const tradeData = await dataService.loadAllData()
    const response: ApiResponse = {
      success: true,
      data: tradeData,
      timestamp: new Date().toISOString()
    }
    res.json(response)
  } catch (error) {
    const response: ApiResponse = {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to load data',
      timestamp: new Date().toISOString()
    }
    res.status(500).json(response)
  }
})

// API Routes
app.use('/api/trades', createTradesRouter(dataService))
app.use('/api/teams', createTeamsRouter(dataService))
app.use('/api/stats', createStatsRouter(dataService))

// File watcher event handlers
fileWatcher.on('fileChanged', async (event) => {
  logger.info(`Pipeline file changed: ${event.filePath} (${event.eventType})`)
  
  try {
    // Clear cache and reload data
    dataService.clearCache()
    const newData = await dataService.loadAllData()
    
    // Notify all connected clients
    io.emit('data-updated', {
      message: 'Trade data has been updated',
      timestamp: event.timestamp.toISOString(),
      changedFile: event.filePath,
      eventType: event.eventType,
      metadata: newData.metadata
    })
    
    logger.info(`Successfully reloaded data and notified ${io.engine.clientsCount} clients`)
  } catch (error) {
    logger.error('Error reloading data after file change:', error)
    
    // Notify clients of the error
    io.emit('data-error', {
      message: 'Failed to reload data after file change',
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString(),
      changedFile: event.filePath
    })
  }
})

fileWatcher.on('error', (error) => {
  logger.error('File watcher error:', error)
})

fileWatcher.on('ready', () => {
  logger.info('File watcher is ready and monitoring pipeline files')
})

// WebSocket connection handling
io.on('connection', (socket) => {
  logger.info(`Client connected: ${socket.id}`)
  
  socket.emit('welcome', { 
    message: 'Connected to Trade Analysis Dashboard',
    timestamp: new Date().toISOString(),
    fileWatcherStatus: fileWatcher.isWatching(),
    watchedFiles: fileWatcher.getWatchedFiles()
  })
  
  // Send current data status
  const lastUpdate = dataService.getLastUpdate()
  if (lastUpdate) {
    socket.emit('data-status', {
      lastUpdate: lastUpdate.toISOString(),
      hasData: dataService.getCachedData() !== null
    })
  }
  
  socket.on('disconnect', () => {
    logger.info(`Client disconnected: ${socket.id}`)
  })
  
  // Handle manual data refresh requests
  socket.on('refresh-data', async () => {
    try {
      logger.info(`Manual data refresh requested by client: ${socket.id}`)
      dataService.clearCache()
      const newData = await dataService.loadAllData()
      
      socket.emit('data-refreshed', {
        message: 'Data refreshed successfully',
        timestamp: new Date().toISOString(),
        metadata: newData.metadata
      })
    } catch (error) {
      socket.emit('refresh-error', {
        message: 'Failed to refresh data',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString()
      })
    }
  })
})

// Error handling middleware (must be last)
app.use(notFoundHandler)
app.use(errorHandler)

server.listen(config.port, () => {
  logger.info(`🚀 Trade Analysis Dashboard API running on port ${config.port}`)
  logger.info(`📊 Environment: ${config.nodeEnv}`)
  logger.info(`📁 Pipeline files: ${JSON.stringify(config.pipelineFiles)}`)
  logger.info(`🔗 CORS origins: ${JSON.stringify(config.cors.origin)}`)
  
  // Start file watcher
  fileWatcher.start()
  
  logger.info(`✅ Ready to serve trade data and real-time updates`)
})

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully...')
  fileWatcher.stop()
  server.close(() => {
    logger.info('Server closed')
    process.exit(0)
  })
})

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully...')
  fileWatcher.stop()
  server.close(() => {
    logger.info('Server closed')
    process.exit(0)
  })
})