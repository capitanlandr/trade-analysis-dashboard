import { Router, Request, Response } from 'express';
import { DataService } from '../services/dataService.js';
import { ApiResponse } from '../types/index.js';

const router = Router();

export function createTeamsRouter(dataService: DataService): Router {
  
  // GET /api/teams - Get all teams with statistics
  router.get('/', async (req: Request, res: Response) => {
    try {
      let tradeData = dataService.getCachedData();
      if (!tradeData) {
        tradeData = await dataService.loadAllData();
      }

      const { sortBy, order } = req.query;
      let teams = [...tradeData.teams];

      // Sort teams
      if (sortBy) {
        const sortField = sortBy as string;
        const sortOrder = (order as string)?.toLowerCase() === 'desc' ? -1 : 1;

        teams.sort((a, b) => {
          let aVal: any, bVal: any;
          
          switch (sortField) {
            case 'tradeCount':
              aVal = a.tradeCount;
              bVal = b.tradeCount;
              break;
            case 'winRate':
              aVal = a.winRate;
              bVal = b.winRate;
              break;
            case 'totalValueGained':
              aVal = a.totalValueGained;
              bVal = b.totalValueGained;
              break;
            case 'avgMargin':
              aVal = a.avgMargin;
              bVal = b.avgMargin;
              break;
            case 'realName':
            default:
              aVal = a.realName;
              bVal = b.realName;
              break;
          }

          if (typeof aVal === 'string') {
            return aVal.localeCompare(bVal) * sortOrder;
          }
          return (aVal - bVal) * sortOrder;
        });
      }

      const response: ApiResponse = {
        success: true,
        data: {
          teams,
          summary: {
            totalTeams: teams.length,
            activeTraders: teams.filter(t => t.tradeCount > 0).length,
            topTrader: teams.reduce((prev, current) => 
              prev.tradeCount > current.tradeCount ? prev : current
            ),
            biggestWinner: teams.reduce((prev, current) => 
              prev.totalValueGained > current.totalValueGained ? prev : current
            )
          }
        },
        timestamp: new Date().toISOString()
      };

      res.json(response);

    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load teams',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });

  // GET /api/teams/:id - Get specific team details
  router.get('/:id', async (req: Request, res: Response) => {
    try {
      let tradeData = dataService.getCachedData();
      if (!tradeData) {
        tradeData = await dataService.loadAllData();
      }

      const teamId = req.params.id;
      
      // Find team by roster ID, real name, nickname, or team name
      const team = tradeData.teams.find(t => 
        t.rosterId.toString() === teamId || 
        t.realName.toLowerCase() === teamId.toLowerCase() || 
        t.nickname.toLowerCase() === teamId.toLowerCase() ||
        t.teamName.toLowerCase() === teamId.toLowerCase() ||
        t.sleeperUsername.toLowerCase() === teamId.toLowerCase()
      );

      if (!team) {
        const response: ApiResponse = {
          success: false,
          error: `Team not found: ${teamId}`,
          timestamp: new Date().toISOString()
        };
        return res.status(404).json(response);
      }

      // Get team's trades (match by sleeper username)
      const teamTrades = tradeData.trades.filter(trade => 
        trade.teamA === team.sleeperUsername || trade.teamB === team.sleeperUsername
      );

      // Calculate detailed statistics
      const wins = teamTrades.filter(trade => trade.winnerCurrent === team.sleeperUsername).length;
      const losses = teamTrades.length - wins;
      
      const valueGainedOverTime = teamTrades.map(trade => {
        const isTeamA = trade.teamA === team.sleeperUsername;
        const valueGained = isTeamA 
          ? (trade.teamAValueNow - trade.teamAValueThen)
          : (trade.teamBValueNow - trade.teamBValueThen);
        
        return {
          date: trade.tradeDate,
          valueGained,
          cumulativeGained: 0 // Will be calculated below
        };
      }).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

      // Calculate cumulative value gained
      let cumulative = 0;
      valueGainedOverTime.forEach(item => {
        cumulative += item.valueGained;
        item.cumulativeGained = cumulative;
      });

      const response: ApiResponse = {
        success: true,
        data: {
          team,
          trades: teamTrades.sort((a, b) => 
            new Date(b.tradeDate).getTime() - new Date(a.tradeDate).getTime()
          ),
          statistics: {
            wins,
            losses,
            winRate: teamTrades.length > 0 ? (wins / teamTrades.length) * 100 : 0,
            totalValueGained: team.totalValueGained,
            avgMargin: team.avgMargin,
            bestTrade: teamTrades.reduce((best, trade) => {
              const isTeamA = trade.teamA === team.sleeperUsername;
              const margin = isTeamA ? trade.marginCurrent : -trade.marginCurrent;
              const bestMargin = best ? (
                best.teamA === team.sleeperUsername ? best.marginCurrent : -best.marginCurrent
              ) : -Infinity;
              return margin > bestMargin ? trade : best;
            }, null as any),
            worstTrade: teamTrades.reduce((worst, trade) => {
              const isTeamA = trade.teamA === team.sleeperUsername;
              const margin = isTeamA ? trade.marginCurrent : -trade.marginCurrent;
              const worstMargin = worst ? (
                worst.teamA === team.sleeperUsername ? worst.marginCurrent : -worst.marginCurrent
              ) : Infinity;
              return margin < worstMargin ? trade : worst;
            }, null as any),
            valueGainedOverTime
          }
        },
        timestamp: new Date().toISOString()
      };

      res.json(response);

    } catch (error) {
      const response: ApiResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to load team details',
        timestamp: new Date().toISOString()
      };
      res.status(500).json(response);
    }
  });

  return router;
}