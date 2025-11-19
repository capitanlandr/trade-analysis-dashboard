import fs from 'fs/promises';
import path from 'path';
import Papa from 'papaparse';
import winston from 'winston';
import { Trade, Team } from '../types/index.js';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.simple()
  ),
  transports: [new winston.transports.Console()]
});

export class CSVParser {
  private cache = new Map<string, { data: any; timestamp: number }>();
  private readonly cacheTimeout = 5 * 60 * 1000; // 5 minutes

  async parseTradesCSV(filePath: string): Promise<Trade[]> {
    try {
      const absolutePath = path.resolve(filePath);
      const csvContent = await fs.readFile(absolutePath, 'utf-8');
      
      const parseResult = Papa.parse(csvContent, {
        header: true,
        skipEmptyLines: true,
        transformHeader: (header) => header.trim()
      });

      if (parseResult.errors.length > 0) {
        logger.warn('CSV parsing warnings:', parseResult.errors);
      }

      const trades: Trade[] = parseResult.data.map((row: any) => ({
        tradeId: `${row.transaction_id}_${row.trade_date}`,
        tradeDate: row.trade_date,
        transactionId: row.transaction_id,
        teamA: row.team_a,
        teamB: row.team_b,
        teamAReceived: this.parseAssetList(row.team_a_received),
        teamBReceived: this.parseAssetList(row.team_b_received),
        teamAValueThen: parseFloat(row.team_a_value_then) || 0,
        teamAValueNow: parseFloat(row.team_a_value_now) || 0,
        teamBValueThen: parseFloat(row.team_b_value_then) || 0,
        teamBValueNow: parseFloat(row.team_b_value_now) || 0,
        winnerAtTrade: row.winner_at_trade,
        winnerCurrent: row.winner_current,
        marginAtTrade: parseFloat(row.margin_at_trade) || 0,
        marginCurrent: parseFloat(row.margin_current) || 0,
        swingWinner: row.swing_winner,
        swingMargin: parseFloat(row.swing_margin) || 0
      }));

      logger.info(`Parsed ${trades.length} trades from ${filePath}`);
      return trades;

    } catch (error) {
      logger.error(`Error parsing trades CSV from ${filePath}:`, error);
      throw new Error(`Failed to parse trades CSV: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async parseTeamIdentityCSV(filePath: string): Promise<Team[]> {
    try {
      const absolutePath = path.resolve(filePath);
      const csvContent = await fs.readFile(absolutePath, 'utf-8');
      
      const parseResult = Papa.parse(csvContent, {
        header: true,
        skipEmptyLines: true,
        transformHeader: (header) => header.trim()
      });

      if (parseResult.errors.length > 0) {
        logger.warn('Team identity CSV parsing warnings:', parseResult.errors);
      }

      const teams: Team[] = parseResult.data.map((row: any) => ({
        rosterId: parseInt(row.roster_id) || 0,
        teamName: row.current_team_name || row.team_name || '',
        realName: row.real_name || '',
        sleeperUsername: row.sleeper_username || '',
        nickname: row.nickname || '',
        tradeCount: 0, // Will be calculated later
        winRate: 0, // Will be calculated later
        avgMargin: 0, // Will be calculated later
        totalValueGained: 0 // Will be calculated later
      }));

      logger.info(`Parsed ${teams.length} teams from ${filePath}`);
      return teams;

    } catch (error) {
      logger.error(`Error parsing team identity CSV from ${filePath}:`, error);
      throw new Error(`Failed to parse team identity CSV: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async parseMultiTeamTradesJSON(filePath: string): Promise<any[]> {
    try {
      const absolutePath = path.resolve(filePath);
      
      // Check if file exists
      try {
        await fs.access(absolutePath);
      } catch {
        logger.info(`Multi-team trades file not found: ${filePath}, returning empty array`);
        return [];
      }

      const jsonContent = await fs.readFile(absolutePath, 'utf-8');
      const multiTeamTrades = JSON.parse(jsonContent);
      
      logger.info(`Parsed ${Array.isArray(multiTeamTrades) ? multiTeamTrades.length : 'unknown'} multi-team trades from ${filePath}`);
      return Array.isArray(multiTeamTrades) ? multiTeamTrades : [];

    } catch (error) {
      logger.error(`Error parsing multi-team trades JSON from ${filePath}:`, error);
      // Don't throw error for multi-team trades as they're optional
      return [];
    }
  }

  async parseAssetValuesCSV(filePath: string): Promise<any[]> {
    try {
      const absolutePath = path.resolve(filePath);
      const csvContent = await fs.readFile(absolutePath, 'utf-8');
      
      const parseResult = Papa.parse(csvContent, {
        header: true,
        skipEmptyLines: true,
        transformHeader: (header) => header.trim()
      });

      if (parseResult.errors.length > 0) {
        logger.warn('Asset values CSV parsing warnings:', parseResult.errors);
      }

      const assets = parseResult.data.map((row: any) => ({
        asset_name: row.asset_name,
        asset_type: row.asset_type,
        trade_date: row.trade_date,
        trade_id: row.trade_id,
        receiving_team: row.receiving_team,
        giving_team: row.giving_team,
        value_at_trade: parseFloat(row.value_at_trade) || 0,
        value_current: parseFloat(row.value_current) || 0
      }));

      logger.info(`Parsed ${assets.length} asset values from ${filePath}`);
      return assets;

    } catch (error) {
      logger.error(`Error parsing asset values CSV from ${filePath}:`, error);
      return [];
    }
  }

  private parseAssetList(assetString: string): string[] {
    if (!assetString || assetString.trim() === '') {
      return [];
    }
    
    // Handle different formats: "asset1, asset2" or "['asset1', 'asset2']"
    const cleaned = assetString.replace(/[\[\]']/g, '');
    return cleaned.split(',').map(asset => asset.trim()).filter(asset => asset.length > 0);
  }

  async fileExists(filePath: string): Promise<boolean> {
    try {
      const absolutePath = path.resolve(filePath);
      await fs.access(absolutePath);
      return true;
    } catch {
      return false;
    }
  }

  async getFileStats(filePath: string): Promise<{ size: number; modified: Date } | null> {
    try {
      const absolutePath = path.resolve(filePath);
      const stats = await fs.stat(absolutePath);
      return {
        size: stats.size,
        modified: stats.mtime
      };
    } catch {
      return null;
    }
  }

  clearCache(): void {
    this.cache.clear();
    logger.info('CSV parser cache cleared');
  }

  getCacheStats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys())
    };
  }
}