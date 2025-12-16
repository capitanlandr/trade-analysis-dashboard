import chokidar from 'chokidar';
import { EventEmitter } from 'events';
import winston from 'winston';
import { config } from '../config/index.js';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.simple()
  ),
  transports: [new winston.transports.Console()]
});

export interface FileChangeEvent {
  filePath: string;
  eventType: 'add' | 'change' | 'unlink';
  timestamp: Date;
}

export class FileWatcher extends EventEmitter {
  private watcher: chokidar.FSWatcher | null = null;
  private debounceTimers: Map<string, NodeJS.Timeout> = new Map();
  private readonly debounceDelay = 1000; // 1 second debounce

  constructor() {
    super();
  }

  start(): void {
    if (this.watcher) {
      logger.warn('File watcher is already running');
      return;
    }

    const filesToWatch = [
      config.pipelineFiles.tradesAnalysis,
      config.pipelineFiles.teamIdentity,
      config.pipelineFiles.multiTeamTrades
    ];

    logger.info('Starting file watcher for pipeline outputs...');
    logger.info(`Watching files: ${JSON.stringify(filesToWatch)}`);

    this.watcher = chokidar.watch(filesToWatch, {
      ignored: /(^|[\/\\])\../, // ignore dotfiles
      persistent: true,
      ignoreInitial: true, // Don't emit events for files that already exist
      awaitWriteFinish: {
        stabilityThreshold: 500, // Wait for file to be stable for 500ms
        pollInterval: 100 // Check every 100ms
      }
    });

    this.watcher
      .on('add', (path) => this.handleFileEvent(path, 'add'))
      .on('change', (path) => this.handleFileEvent(path, 'change'))
      .on('unlink', (path) => this.handleFileEvent(path, 'unlink'))
      .on('error', (error) => {
        logger.error('File watcher error:', error);
        this.emit('error', error);
      })
      .on('ready', () => {
        logger.info('File watcher is ready and monitoring for changes');
        this.emit('ready');
      });
  }

  stop(): void {
    if (this.watcher) {
      logger.info('Stopping file watcher...');
      this.watcher.close();
      this.watcher = null;
      
      // Clear any pending debounce timers
      this.debounceTimers.forEach(timer => clearTimeout(timer));
      this.debounceTimers.clear();
      
      logger.info('File watcher stopped');
      this.emit('stopped');
    }
  }

  private handleFileEvent(filePath: string, eventType: 'add' | 'change' | 'unlink'): void {
    logger.info(`File ${eventType}: ${filePath}`);

    // Clear existing debounce timer for this file
    const existingTimer = this.debounceTimers.get(filePath);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    // Set new debounce timer
    const timer = setTimeout(() => {
      this.debounceTimers.delete(filePath);
      
      const event: FileChangeEvent = {
        filePath,
        eventType,
        timestamp: new Date()
      };

      logger.info(`Emitting debounced file change event: ${eventType} for ${filePath}`);
      this.emit('fileChanged', event);

      // Emit specific events for different file types
      if (filePath.includes('trades_analysis')) {
        this.emit('tradesFileChanged', event);
      } else if (filePath.includes('team_identity')) {
        this.emit('teamsFileChanged', event);
      } else if (filePath.includes('multi_team_trades')) {
        this.emit('multiTeamTradesFileChanged', event);
      }

    }, this.debounceDelay);

    this.debounceTimers.set(filePath, timer);
  }

  isWatching(): boolean {
    return this.watcher !== null;
  }

  getWatchedFiles(): string[] {
    if (!this.watcher) return [];
    
    return this.watcher.getWatched() 
      ? Object.keys(this.watcher.getWatched()).reduce((files: string[], dir) => {
          const dirFiles = this.watcher!.getWatched()[dir] || [];
          return files.concat(dirFiles.map(file => `${dir}/${file}`));
        }, [])
      : [];
  }
}