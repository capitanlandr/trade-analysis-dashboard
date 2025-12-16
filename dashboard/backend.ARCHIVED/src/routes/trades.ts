import { Router, Request, Response } from 'express';
import { DataService } from '../services/dataService.js';
import { ApiResponse, Trade } from '../types/index.js';

const router = Router();

export function createTradesRouter(dataService: DataService): Router {
  
  // GET /api/trades/debug-csv - Test CSV parsing directly
  router.get('/debug-csv', async (req: Request, res: Response) => {
    try {
      const { CSVParser } = await import('../services/csvParser.js');
      const { config } = await import('../config/index.js');
      const csvParser = new CSVParser();
      
      const assetValuesPath = config.pipelineFiles.assetValues;
      const exists = await csvParser.fileExists(assetValuesPath);
      
      if (!exists) {
        return res.json({
          success: false,
          error: `File not found: ${assetValuesPath}`,
          absolutePath: assetValuesPath
        });
      }
      
      const assets = await csvParser.parseAssetValuesCSV(assetValuesPath);
      
      res.json({
        success: true,
        data: {
          path: assetValuesPath,
          fileExists: exists,
          assetsLoaded: assets.length,
          sampleAssets: assets.slice(0, 3)
        }
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });
  
  // GET /api/trades/debug - Debug endpoint to check asset loading
  router.get('/debug', async (req: Request, res: Response) => {
    try {
      // Force reload data
      dataService.clearCache();
      const tradeData = await dataService.loadAllData();

      const sampleTrade = tradeData.trades[0];
      
      // Check all trades for any with assets
      const tradesWithAssets = tradeData.trades.filter(t => 
        (t.teamAAssets && t.teamAAssets.length > 0) || 
        (t.teamBAssets && t.teamBAssets.length > 0)
      );
      
      const response: ApiResponse = {
        success: true,
        data: {
          totalTrades: tradeData.trades.length,
          tradesWithAssets: tradesWithAssets.length,
          sampleTrade: {
            transactionId: sampleTrade?.transactionId,
            teamAAssets: sampleTrade?.teamAAssets,
            teamBAssets: sampleTrade?.teamBAssets,
            hasAssets: (sampleTrade?.teamAAssets?.length || 0) > 0 || (sampleTrade?.teamBAssets?.length || 0) > 0
          },
          sampleTradeWithAssets: tradesWithAssets[0] ? {
            transactionId: tradesWithAssets[0].transactionId,
            teamAAssets: tradesWithAssets[0].teamAAssets,
            teamBAssets: tradesWithAssets[0].teamBAssets
          } : null
        },
        timestamp: new Date().toISOString()
      };

      res.json(response);
    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Debug failed',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });
  
  // GET /api/trades/blockbuster - Get blockbuster trades (must come before /:id)
  router.get('/blockbuster', async (req: Request, res: Response) => {
    try {
      let tradeData = dataService.getCachedData();
      if (!tradeData) {
        tradeData = await dataService.loadAllData();
      }

      const threshold = req.query.threshold ? 
        parseFloat(req.query.threshold as string) : 5000;

      const blockbusterTrades = tradeData.trades
        .filter(trade => (trade.teamAValueNow + trade.teamBValueNow) > threshold)
        .sort((a, b) => {
          const aValue = a.teamAValueNow + a.teamBValueNow;
          const bValue = b.teamAValueNow + b.teamBValueNow;
          return bValue - aValue; // Highest value first
        });

      const response: ApiResponse = {
        success: true,
        data: {
          blockbusterTrades,
          threshold,
          count: blockbusterTrades.length,
          averageValue: blockbusterTrades.length > 0 
            ? blockbusterTrades.reduce((sum, trade) => 
                sum + trade.teamAValueNow + trade.teamBValueNow, 0
              ) / blockbusterTrades.length
            : 0
        },
        timestamp: new Date().toISOString()
      };

      res.json(response);

    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load blockbuster trades',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });

  // GET /api/trades - Get all trades with optional filtering
  router.get('/', async (req: Request, res: Response) => {
    try {
      let tradeData = dataService.getCachedData();
      if (!tradeData) {
        tradeData = await dataService.loadAllData();
      }

      let filteredTrades = tradeData.trades;

      // Apply filters from query parameters
      const { startDate, endDate, teams, minValue, maxResults } = req.query;

      // Date range filter
      if (startDate) {
        const start = new Date(startDate as string);
        filteredTrades = filteredTrades.filter(trade => 
          new Date(trade.tradeDate) >= start
        );
      }

      if (endDate) {
        const end = new Date(endDate as string);
        filteredTrades = filteredTrades.filter(trade => 
          new Date(trade.tradeDate) <= end
        );
      }

      // Team filter (comma-separated list)
      if (teams) {
        const teamList = (teams as string).split(',').map(t => t.trim());
        filteredTrades = filteredTrades.filter(trade => 
          teamList.includes(trade.teamA) || teamList.includes(trade.teamB)
        );
      }

      // Minimum trade value filter
      if (minValue) {
        const minVal = parseFloat(minValue as string);
        filteredTrades = filteredTrades.filter(trade => 
          (trade.teamAValueNow + trade.teamBValueNow) >= minVal
        );
      }

      // Limit results
      if (maxResults) {
        const limit = parseInt(maxResults as string);
        filteredTrades = filteredTrades.slice(0, limit);
      }

      // Sort by trade date (newest first)
      filteredTrades.sort((a, b) => 
        new Date(b.tradeDate).getTime() - new Date(a.tradeDate).getTime()
      );

      const response: ApiResponse = {
        success: true,
        data: {
          trades: filteredTrades,
          metadata: {
            ...tradeData.metadata,
            filteredCount: filteredTrades.length,
            totalCount: tradeData.trades.length,
            filters: { startDate, endDate, teams, minValue, maxResults }
          }
        },
        timestamp: new Date().toISOString()
      };

      res.json(response);

    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load trades',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });

  // GET /api/trades/:id - Get specific trade details
  router.get('/:id', async (req: Request, res: Response) => {
    try {
      let tradeData = dataService.getCachedData();
      if (!tradeData) {
        tradeData = await dataService.loadAllData();
      }

      const tradeId = req.params.id;
      const trade = tradeData.trades.find(t => 
        t.tradeId === tradeId || t.transactionId === tradeId
      );

      if (!trade) {
        const response: ApiResponse = {
          success: false,
          error: `Trade not found: ${tradeId}`,
          timestamp: new Date().toISOString()
        };
        return res.status(404).json(response);
      }

      // Get related trades (same teams within 30 days)
      const tradeDate = new Date(trade.tradeDate);
      const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;
      
      const relatedTrades = tradeData.trades.filter(t => {
        if (t.tradeId === trade.tradeId) return false;
        
        const otherDate = new Date(t.tradeDate);
        const timeDiff = Math.abs(tradeDate.getTime() - otherDate.getTime());
        
        return timeDiff <= thirtyDaysMs && (
          (t.teamA === trade.teamA || t.teamA === trade.teamB) ||
          (t.teamB === trade.teamA || t.teamB === trade.teamB)
        );
      });

      const response: ApiResponse = {
        success: true,
        data: {
          trade,
          relatedTrades: relatedTrades.slice(0, 5), // Limit to 5 related trades
          context: {
            isBlockbuster: (trade.teamAValueNow + trade.teamBValueNow) > 5000,
            swingPercentage: trade.marginAtTrade > 0 
              ? ((trade.swingMargin / trade.marginAtTrade) * 100).toFixed(1)
              : 'N/A',
            daysAgo: Math.floor((Date.now() - tradeDate.getTime()) / (1000 * 60 * 60 * 24))
          }
        },
        timestamp: new Date().toISOString()
      };

      res.json(response);

    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load trade details',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });



  return router;
}