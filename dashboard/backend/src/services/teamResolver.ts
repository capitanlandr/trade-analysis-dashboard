import fs from 'fs/promises';
import Papa from 'papaparse';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.simple()
  ),
  transports: [new winston.transports.Console()]
});

export interface TeamInfo {
  rosterId: number;
  sleeperUsername: string;
  realName: string;
  nickname: string;
  currentTeamName: string;
  week7TeamName: string;
  historicalTeamNames: string;
  notes: string;
}

export class TeamResolver {
  private teams = new Map<number, TeamInfo>();
  private usernameToRosterId = new Map<string, number>();
  private realNameToRosterId = new Map<string, number>();

  constructor(private mappingFile: string) {}

  async loadMapping(): Promise<void> {
    try {
      const csvContent = await fs.readFile(this.mappingFile, 'utf-8');
      
      const parseResult = Papa.parse(csvContent, {
        header: true,
        skipEmptyLines: true,
        transformHeader: (header) => header.trim()
      });

      if (parseResult.errors.length > 0) {
        logger.warn('Team mapping CSV parsing warnings:', parseResult.errors);
      }

      this.teams.clear();
      this.usernameToRosterId.clear();
      this.realNameToRosterId.clear();

      parseResult.data.forEach((row: any) => {
        const rosterId = parseInt(row.roster_id);
        if (isNaN(rosterId)) return;

        const teamInfo: TeamInfo = {
          rosterId,
          sleeperUsername: row.sleeper_username || '',
          realName: row.real_name || '',
          nickname: row.nickname || '',
          currentTeamName: row.current_team_name || '',
          week7TeamName: row.week_7_team_name || '',
          historicalTeamNames: row.historical_team_names || '',
          notes: row.notes || ''
        };

        this.teams.set(rosterId, teamInfo);
        
        // Create lookup maps
        if (teamInfo.sleeperUsername) {
          this.usernameToRosterId.set(teamInfo.sleeperUsername.toLowerCase(), rosterId);
        }
        if (teamInfo.realName) {
          this.realNameToRosterId.set(teamInfo.realName.toLowerCase(), rosterId);
        }
      });

      logger.info(`Loaded ${this.teams.size} teams from ${this.mappingFile}`);

    } catch (error) {
      logger.error(`Error loading team mapping from ${this.mappingFile}:`, error);
      throw error;
    }
  }

  getByRosterId(rosterId: number): TeamInfo | undefined {
    return this.teams.get(rosterId);
  }

  getByUsername(username: string): TeamInfo | undefined {
    const rosterId = this.usernameToRosterId.get(username.toLowerCase());
    return rosterId ? this.teams.get(rosterId) : undefined;
  }

  getByRealName(realName: string): TeamInfo | undefined {
    const rosterId = this.realNameToRosterId.get(realName.toLowerCase());
    return rosterId ? this.teams.get(rosterId) : undefined;
  }

  getRosterIdByUsername(username: string): number | undefined {
    return this.usernameToRosterId.get(username.toLowerCase());
  }

  getRosterIdByRealName(realName: string): number | undefined {
    return this.realNameToRosterId.get(realName.toLowerCase());
  }

  getNickname(rosterId: number): string {
    const team = this.getByRosterId(rosterId);
    return team?.nickname || `Unknown (roster ${rosterId})`;
  }

  getCurrentTeamName(rosterId: number): string {
    const team = this.getByRosterId(rosterId);
    return team?.currentTeamName || `Unknown (roster ${rosterId})`;
  }

  getStableIdentifier(rosterId: number): string {
    const team = this.getByRosterId(rosterId);
    return team?.realName || `Unknown (roster ${rosterId})`;
  }

  listAllTeams(): TeamInfo[] {
    return Array.from(this.teams.values()).sort((a, b) => a.rosterId - b.rosterId);
  }

  // Convert trade participant (username) to roster ID for consistent processing
  resolveTradeParticipant(participant: string): { rosterId: number; teamInfo: TeamInfo } | null {
    const teamInfo = this.getByUsername(participant);
    if (teamInfo) {
      return { rosterId: teamInfo.rosterId, teamInfo };
    }
    
    logger.warn(`Could not resolve trade participant: ${participant}`);
    return null;
  }

  // Get display name for UI (can be customized based on preference)
  getDisplayName(rosterId: number, format: 'real' | 'nickname' | 'team' = 'real'): string {
    const team = this.getByRosterId(rosterId);
    if (!team) return `Unknown (roster ${rosterId})`;

    switch (format) {
      case 'nickname':
        return team.nickname || team.realName;
      case 'team':
        return team.currentTeamName || team.realName;
      case 'real':
      default:
        return team.realName;
    }
  }

  // Get comprehensive team info for API responses
  getTeamSummary(rosterId: number) {
    const team = this.getByRosterId(rosterId);
    if (!team) return null;

    return {
      rosterId: team.rosterId,
      realName: team.realName,
      nickname: team.nickname,
      currentTeamName: team.currentTeamName,
      sleeperUsername: team.sleeperUsername,
      // Don't expose internal fields like notes in API
    };
  }
}