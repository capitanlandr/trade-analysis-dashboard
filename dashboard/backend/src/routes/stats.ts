import { Router, Request, Response } from 'express';
import { DataService } from '../services/dataService.js';
import { ApiResponse } from '../types/index.js';

const router = Router();

export function createStatsRouter(dataService: DataService): Router {
  
  // GET /api/stats/summary - Get league-wide statistics
  router.get('/summary', async (req: Request, res: Response) => {
    try {
      let tradeData = dataService.getCachedData();
      if (!tradeData) {
        tradeData = await dataService.loadAllData();
      }

      const { trades, teams, statistics } = tradeData;

      // Calculate additional statistics
      const tradesByMonth = trades.reduce((acc, trade) => {
        const month = trade.tradeDate.substring(0, 7); // YYYY-MM
        acc[month] = (acc[month] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      const valueDistribution = {
        under1000: trades.filter(t => (t.teamAValueNow + t.teamBValueNow) < 1000).length,
        '1000-2500': trades.filter(t => {
          const total = t.teamAValueNow + t.teamBValueNow;
          return total >= 1000 && total < 2500;
        }).length,
        '2500-5000': trades.filter(t => {
          const total = t.teamAValueNow + t.teamBValueNow;
          return total >= 2500 && total < 5000;
        }).length,
        '5000-10000': trades.filter(t => {
          const total = t.teamAValueNow + t.teamBValueNow;
          return total >= 5000 && total < 10000;
        }).length,
        over10000: trades.filter(t => (t.teamAValueNow + t.teamBValueNow) >= 10000).length
      };

      const swingAnalysis = {
        biggestSwing: trades.reduce((max, trade) => 
          Math.abs(trade.swingMargin) > Math.abs(max.swingMargin) ? trade : max
        ),
        averageSwing: trades.reduce((sum, trade) => 
          sum + Math.abs(trade.swingMargin), 0
        ) / trades.length,
        positiveSwings: trades.filter(t => t.swingMargin > 0).length,
        negativeSwings: trades.filter(t => t.swingMargin < 0).length
      };

      const response: ApiResponse = {
        success: true,
        data: {
          overview: statistics,
          tradesByMonth,
          valueDistribution,
          swingAnalysis,
          teamRankings: {
            byTradeCount: [...teams].sort((a, b) => b.tradeCount - a.tradeCount).slice(0, 5),
            byWinRate: [...teams].filter(t => t.tradeCount >= 3).sort((a, b) => b.winRate - a.winRate).slice(0, 5),
            byValueGained: [...teams].sort((a, b) => b.totalValueGained - a.totalValueGained).slice(0, 5)
          },
          recentActivity: {
            last30Days: trades.filter(trade => {
              const tradeDate = new Date(trade.tradeDate);
              const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
              return tradeDate >= thirtyDaysAgo;
            }).length,
            last7Days: trades.filter(trade => {
              const tradeDate = new Date(trade.tradeDate);
              const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
              return tradeDate >= sevenDaysAgo;
            }).length
          }
        },
        timestamp: new Date().toISOString()
      };

      res.json(response);

    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load statistics',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });

  // GET /api/stats/trends - Get trend analysis
  router.get('/trends', async (req: Request, res: Response) => {
    try {
      let tradeData = dataService.getCachedData();
      if (!tradeData) {
        tradeData = await dataService.loadAllData();
      }

      const { trades } = tradeData;
      const { period = 'month' } = req.query;

      // Group trades by time period
      const groupedTrades = trades.reduce((acc, trade) => {
        let key: string;
        const date = new Date(trade.tradeDate);
        
        switch (period) {
          case 'week':
            // Get week of year
            const weekStart = new Date(date);
            weekStart.setDate(date.getDate() - date.getDay());
            key = weekStart.toISOString().split('T')[0];
            break;
          case 'month':
          default:
            key = trade.tradeDate.substring(0, 7); // YYYY-MM
            break;
        }

        if (!acc[key]) {
          acc[key] = {
            period: key,
            tradeCount: 0,
            totalValue: 0,
            avgMargin: 0,
            blockbusters: 0
          };
        }

        acc[key].tradeCount++;
        acc[key].totalValue += trade.teamAValueNow + trade.teamBValueNow;
        acc[key].avgMargin += Math.abs(trade.marginCurrent);
        
        if ((trade.teamAValueNow + trade.teamBValueNow) > 5000) {
          acc[key].blockbusters++;
        }

        return acc;
      }, {} as Record<string, any>);

      // Calculate averages and sort by period
      const trends = Object.values(groupedTrades).map((group: any) => ({
        ...group,
        avgValue: group.totalValue / group.tradeCount,
        avgMargin: group.avgMargin / group.tradeCount
      })).sort((a: any, b: any) => a.period.localeCompare(b.period));

      const response: ApiResponse = {
        success: true,
        data: {
          trends,
          period,
          summary: {
            totalPeriods: trends.length,
            peakTradingPeriod: trends.reduce((peak: any, current: any) => 
              current.tradeCount > peak.tradeCount ? current : peak
            ),
            highestValuePeriod: trends.reduce((peak: any, current: any) => 
              current.avgValue > peak.avgValue ? current : peak
            )
          }
        },
        timestamp: new Date().toISOString()
      };

      res.json(response);

    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load trends',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });

  return router;
}