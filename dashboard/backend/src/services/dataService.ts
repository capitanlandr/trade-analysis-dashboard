import { CSVParser } from './csvParser.js';
import { TeamResolver } from './teamResolver.js';
import { Trade, Team, LeagueStats, TradeData } from '../types/index.js';
import { config } from '../config/index.js';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.simple()
  ),
  transports: [new winston.transports.Console()]
});

export class DataService {
  private csvParser: CSVParser;
  private teamResolver: TeamResolver;
  private cachedData: TradeData | null = null;
  private lastUpdate: Date | null = null;

  constructor() {
    this.csvParser = new CSVParser();
    this.teamResolver = new TeamResolver(config.pipelineFiles.teamIdentity);
  }

  async loadAllData(): Promise<TradeData> {
    try {
      logger.info('Loading all trade data from pipeline files...');

      // Load team resolver first
      await this.teamResolver.loadMapping();

      // Load trades and teams in parallel
      const [trades, teams, multiTeamTrades] = await Promise.all([
        this.loadTrades(),
        this.loadTeams(),
        this.loadMultiTeamTrades()
      ]);

      // Calculate team statistics based on trades
      const enhancedTeams = this.calculateTeamStats(teams, trades);
      
      // Calculate league statistics
      const statistics = this.calculateLeagueStats(trades, enhancedTeams);

      const tradeData: TradeData = {
        metadata: {
          lastUpdated: new Date().toISOString(),
          totalTrades: trades.length,
          dateRange: this.getDateRange(trades)
        },
        trades,
        teams: enhancedTeams,
        statistics
      };

      this.cachedData = tradeData;
      this.lastUpdate = new Date();
      
      logger.info(`Successfully loaded ${trades.length} trades and ${enhancedTeams.length} teams`);
      return tradeData;

    } catch (error) {
      logger.error('Error loading trade data:', error);
      throw error;
    }
  }

  async loadTrades(): Promise<Trade[]> {
    const filePath = config.pipelineFiles.tradesAnalysis;
    const exists = await this.csvParser.fileExists(filePath);
    
    if (!exists) {
      logger.warn(`Trades file not found: ${filePath}`);
      return [];
    }

    return await this.csvParser.parseTradesCSV(filePath);
  }

  async loadTeams(): Promise<Team[]> {
    // Use team resolver instead of direct CSV parsing
    const teamInfos = this.teamResolver.listAllTeams();
    
    return teamInfos.map(teamInfo => ({
      rosterId: teamInfo.rosterId,
      teamName: teamInfo.currentTeamName,
      realName: teamInfo.realName,
      sleeperUsername: teamInfo.sleeperUsername,
      nickname: teamInfo.nickname,
      tradeCount: 0, // Will be calculated later
      winRate: 0, // Will be calculated later
      avgMargin: 0, // Will be calculated later
      totalValueGained: 0 // Will be calculated later
    }));
  }

  async loadMultiTeamTrades(): Promise<any[]> {
    const filePath = config.pipelineFiles.multiTeamTrades;
    return await this.csvParser.parseMultiTeamTradesJSON(filePath);
  }

  private calculateTeamStats(teams: Team[], trades: Trade[]): Team[] {
    // Use roster_id as the source of truth
    const rosterIdToTeam = new Map<number, Team>();
    teams.forEach(team => {
      rosterIdToTeam.set(team.rosterId, team);
    });

    const teamStats = new Map<number, {
      tradeCount: number;
      wins: number;
      totalMargin: number;
      totalValueGained: number;
    }>();

    // Initialize stats for all teams using roster_id
    teams.forEach(team => {
      teamStats.set(team.rosterId, {
        tradeCount: 0,
        wins: 0,
        totalMargin: 0,
        totalValueGained: 0
      });
    });

    // Calculate stats from trades
    trades.forEach(trade => {
      // Resolve trade participants to roster IDs
      const teamAResolved = this.teamResolver.resolveTradeParticipant(trade.teamA);
      const teamBResolved = this.teamResolver.resolveTradeParticipant(trade.teamB);

      if (teamAResolved) {
        const stats = teamStats.get(teamAResolved.rosterId)!;
        stats.tradeCount++;
        stats.totalMargin += Math.abs(trade.marginCurrent);
        stats.totalValueGained += (trade.teamAValueNow - trade.teamAValueThen);
        if (trade.winnerCurrent === trade.teamA) {
          stats.wins++;
        }
      }

      if (teamBResolved) {
        const stats = teamStats.get(teamBResolved.rosterId)!;
        stats.tradeCount++;
        stats.totalMargin += Math.abs(trade.marginCurrent);
        stats.totalValueGained += (trade.teamBValueNow - trade.teamBValueThen);
        if (trade.winnerCurrent === trade.teamB) {
          stats.wins++;
        }
      }
    });

    // Apply calculated stats to teams
    return teams.map(team => {
      const stats = teamStats.get(team.rosterId);
      if (!stats) return team;

      return {
        ...team,
        tradeCount: stats.tradeCount,
        winRate: stats.tradeCount > 0 ? (stats.wins / stats.tradeCount) * 100 : 0,
        avgMargin: stats.tradeCount > 0 ? stats.totalMargin / stats.tradeCount : 0,
        totalValueGained: stats.totalValueGained
      };
    });
  }

  private calculateLeagueStats(trades: Trade[], teams: Team[]): LeagueStats {
    if (trades.length === 0) {
      return {
        totalTrades: 0,
        totalTradeValue: 0,
        avgTradeMargin: 0,
        mostActiveTrader: '',
        biggestWinner: '',
        blockbusterCount: 0,
        dateRange: { earliest: '', latest: '' }
      };
    }



    const totalTradeValue = trades.reduce((sum, trade) => 
      sum + trade.teamAValueNow + trade.teamBValueNow, 0
    );

    const avgTradeMargin = trades.reduce((sum, trade) => 
      sum + Math.abs(trade.marginCurrent), 0
    ) / trades.length;

    const mostActiveTrader = teams
      .sort((a, b) => b.tradeCount - a.tradeCount)[0]?.realName || '';

    const biggestWinner = teams
      .sort((a, b) => b.totalValueGained - a.totalValueGained)[0]?.realName || '';

    const blockbusterCount = trades.filter(trade => 
      (trade.teamAValueNow + trade.teamBValueNow) > 5000
    ).length;

    return {
      totalTrades: trades.length,
      totalTradeValue,
      avgTradeMargin,
      mostActiveTrader,
      biggestWinner,
      blockbusterCount,
      dateRange: this.getDateRange(trades)
    };
  }

  private getDateRange(trades: Trade[]): { earliest: string; latest: string } {
    if (trades.length === 0) {
      return { earliest: '', latest: '' };
    }

    const dates = trades.map(trade => new Date(trade.tradeDate)).sort((a, b) => a.getTime() - b.getTime());
    return {
      earliest: dates[0].toISOString().split('T')[0],
      latest: dates[dates.length - 1].toISOString().split('T')[0]
    };
  }

  async getFileStatus(): Promise<{
    tradesFile: { exists: boolean; stats: any };
    teamsFile: { exists: boolean; stats: any };
    multiTeamFile: { exists: boolean; stats: any };
  }> {
    const [tradesExists, teamsExists, multiTeamExists] = await Promise.all([
      this.csvParser.fileExists(config.pipelineFiles.tradesAnalysis),
      this.csvParser.fileExists(config.pipelineFiles.teamIdentity),
      this.csvParser.fileExists(config.pipelineFiles.multiTeamTrades)
    ]);

    const [tradesStats, teamsStats, multiTeamStats] = await Promise.all([
      this.csvParser.getFileStats(config.pipelineFiles.tradesAnalysis),
      this.csvParser.getFileStats(config.pipelineFiles.teamIdentity),
      this.csvParser.getFileStats(config.pipelineFiles.multiTeamTrades)
    ]);

    return {
      tradesFile: { exists: tradesExists, stats: tradesStats },
      teamsFile: { exists: teamsExists, stats: teamsStats },
      multiTeamFile: { exists: multiTeamExists, stats: multiTeamStats }
    };
  }

  getCachedData(): TradeData | null {
    return this.cachedData;
  }

  getLastUpdate(): Date | null {
    return this.lastUpdate;
  }

  clearCache(): void {
    this.cachedData = null;
    this.lastUpdate = null;
    this.csvParser.clearCache();
    logger.info('Data service cache cleared');
  }
}