import { Router, Request, Response } from 'express';
import { readFile } from 'fs/promises';
import { join } from 'path';
import { ApiResponse } from '../types/index.js';

const router = Router();

export function createWaiverWireRouter(): Router {
  
  // GET /api/waiver-wire - Get waiver wire analysis data
  router.get('/', async (req: Request, res: Response) => {
    try {
      // Try to read from public directory first, then fallback to root
      const possiblePaths = [
        join(process.cwd(), '..', 'frontend', 'public', 'api-waiver-wire.json'),
        join(process.cwd(), '..', '..', 'api-waiver-wire.json'),
        join(process.cwd(), 'public', 'api-waiver-wire.json')
      ];

      let waiverWireData = null;
      let dataFound = false;

      for (const filePath of possiblePaths) {
        try {
          const fileContent = await readFile(filePath, 'utf-8');
          waiverWireData = JSON.parse(fileContent);
          dataFound = true;
          break;
        } catch (error) {
          // Continue to next path
          continue;
        }
      }

      if (!dataFound || !waiverWireData) {
        const response: ApiResponse = {
          success: false,
          error: 'Waiver wire data not found. Please run the waiver wire analysis pipeline first.',
          timestamp: new Date().toISOString()
        };
        return res.status(404).json(response);
      }

      const response: ApiResponse = {
        success: true,
        data: waiverWireData,
        timestamp: new Date().toISOString()
      };

      res.json(response);

    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load waiver wire data',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });

  // GET /api/waiver-wire/summary - Get waiver wire summary stats
  router.get('/summary', async (req: Request, res: Response) => {
    try {
      // Try to read from public directory first, then fallback to root
      const possiblePaths = [
        join(process.cwd(), '..', 'frontend', 'public', 'api-waiver-wire.json'),
        join(process.cwd(), '..', '..', 'api-waiver-wire.json'),
        join(process.cwd(), 'public', 'api-waiver-wire.json')
      ];

      let waiverWireData = null;
      let dataFound = false;

      for (const filePath of possiblePaths) {
        try {
          const fileContent = await readFile(filePath, 'utf-8');
          waiverWireData = JSON.parse(fileContent);
          dataFound = true;
          break;
        } catch (error) {
          continue;
        }
      }

      if (!dataFound || !waiverWireData) {
        const response: ApiResponse = {
          success: false,
          error: 'Waiver wire data not found',
          timestamp: new Date().toISOString()
        };
        return res.status(404).json(response);
      }

      // Extract just the summary data
      const summaryData = {
        metadata: waiverWireData.metadata,
        topStats: {
          mostActiveManager: waiverWireData.manager_activity.reduce((prev: any, current: any) => 
            (prev.total_claims > current.total_claims) ? prev : current
          ),
          highestSuccessRate: waiverWireData.manager_activity.reduce((prev: any, current: any) => 
            (prev.success_rate > current.success_rate) ? prev : current
          ),
          biggestSpender: waiverWireData.manager_activity.reduce((prev: any, current: any) => 
            (prev.total_bid > current.total_bid) ? prev : current
          ),
          mostContestedPlayer: waiverWireData.contested_players[0] || null,
          busiestWeek: waiverWireData.weekly_activity.reduce((prev: any, current: any) => 
            (prev.total_transactions > current.total_transactions) ? prev : current
          )
        }
      };

      const response: ApiResponse = {
        success: true,
        data: summaryData,
        timestamp: new Date().toISOString()
      };

      res.json(response);

    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load waiver wire summary',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });

  return router;
}