import React, { useMemo } from 'react';
import type { Trade, Team, LeagueStats, SeasonFilter, TradeData } from '../types';

interface SeasonMetrics {
  filteredTrades: Trade[];
  filteredTeams: Team[];
  filteredStats: LeagueStats | undefined;
  seasonCounts: Record<string, number>;
  availableSeasons: string[];
  totalFilteredCount: number;
}

/**
 * Hook for calculating metrics based on season filtering
 * Provides client-side filtering and metric recalculation for multi-season data
 */
export const useSeasonMetrics = (
  tradeData: TradeData | undefined,
  seasonFilter: SeasonFilter
): SeasonMetrics => {
  return useMemo(() => {
    if (!tradeData) {
      return {
        filteredTrades: [],
        filteredTeams: [],
        filteredStats: undefined,
        seasonCounts: {},
        availableSeasons: [],
        totalFilteredCount: 0
      };
    }

    const { trades, teams, statistics, metadata } = tradeData;

    // Extract available seasons from metadata or trades
    const availableSeasons = metadata.seasons_included || 
      [...new Set(trades.map(trade => trade.season).filter(Boolean))] as string[];

    // Calculate season counts
    const seasonCounts = metadata.trades_by_season || 
      trades.reduce((counts, trade) => {
        if (trade.season) {
          counts[trade.season] = (counts[trade.season] || 0) + 1;
        }
        return counts;
      }, {} as Record<string, number>);

    // Filter trades based on selected seasons
    const filteredTrades = trades.filter(trade => {
      if (!trade.season) return seasonFilter.type === 'all'; // Include trades without season in "All" view
      return seasonFilter.seasons.includes(trade.season);
    });

    // Recalculate team metrics based on filtered trades
    const filteredTeams = useMemo(() => {
      if (!teams) return [];

      // Create a map to track team performance from filtered trades
      const teamMetrics = new Map<string, {
        tradeCount: number;
        wins: number;
        totalMargin: number;
        totalValueGained: number;
      }>();

      // Initialize team metrics
      teams.forEach(team => {
        teamMetrics.set(team.teamName, {
          tradeCount: 0,
          wins: 0,
          totalMargin: 0,
          totalValueGained: 0
        });
      });

      // Calculate metrics from filtered trades
      filteredTrades.forEach(trade => {
        const teamAMetrics = teamMetrics.get(trade.teamA);
        const teamBMetrics = teamMetrics.get(trade.teamB);

        if (teamAMetrics) {
          teamAMetrics.tradeCount++;
          if (trade.winnerCurrent === trade.teamA) {
            teamAMetrics.wins++;
          }
          teamAMetrics.totalMargin += trade.marginCurrent || 0;
          teamAMetrics.totalValueGained += (trade.teamAValueNow || 0) - (trade.teamAValueThen || 0);
        }

        if (teamBMetrics) {
          teamBMetrics.tradeCount++;
          if (trade.winnerCurrent === trade.teamB) {
            teamBMetrics.wins++;
          }
          teamBMetrics.totalMargin += trade.marginCurrent || 0;
          teamBMetrics.totalValueGained += (trade.teamBValueNow || 0) - (trade.teamBValueThen || 0);
        }
      });

      // Create updated team objects with recalculated metrics
      return teams.map(team => {
        const metrics = teamMetrics.get(team.teamName);
        if (!metrics) return team;

        return {
          ...team,
          tradeCount: metrics.tradeCount,
          winRate: metrics.tradeCount > 0 ? metrics.wins / metrics.tradeCount : 0,
          avgMargin: metrics.tradeCount > 0 ? metrics.totalMargin / metrics.tradeCount : 0,
          totalValueGained: metrics.totalValueGained
        };
      }).sort((a, b) => b.winRate - a.winRate); // Sort by win rate descending
    }, [teams, filteredTrades]);

    // Recalculate league statistics based on filtered trades
    const filteredStats = useMemo(() => {
      if (!statistics || filteredTrades.length === 0) return statistics;

      const totalTrades = filteredTrades.length;
      const totalTradeValue = filteredTrades.reduce((sum, trade) => 
        sum + Math.max(trade.teamAValueThen || 0, trade.teamBValueThen || 0), 0
      );
      const avgTradeMargin = filteredTrades.reduce((sum, trade) => 
        sum + Math.abs(trade.marginCurrent || 0), 0
      ) / totalTrades;

      // Find most active trader
      const traderCounts = new Map<string, number>();
      filteredTrades.forEach(trade => {
        traderCounts.set(trade.teamA, (traderCounts.get(trade.teamA) || 0) + 1);
        traderCounts.set(trade.teamB, (traderCounts.get(trade.teamB) || 0) + 1);
      });
      const mostActiveTrader = [...traderCounts.entries()]
        .sort(([,a], [,b]) => b - a)[0]?.[0] || '';

      // Find biggest winner by total value gained
      const biggestWinner = filteredTeams.length > 0 
        ? filteredTeams.reduce((prev, current) => 
            (current.totalValueGained > prev.totalValueGained) ? current : prev
          ).teamName
        : '';

      // Count blockbuster trades (using original threshold or default)
      const blockbusterThreshold = 100; // Default threshold, could be configurable
      const blockbusterCount = filteredTrades.filter(trade => 
        Math.max(trade.teamAValueThen || 0, trade.teamBValueThen || 0) >= blockbusterThreshold
      ).length;

      // Calculate date range
      const tradeDates = filteredTrades.map(trade => new Date(trade.tradeDate));
      const earliest = tradeDates.length > 0 
        ? new Date(Math.min(...tradeDates.map(d => d.getTime()))).toISOString()
        : statistics.dateRange.earliest;
      const latest = tradeDates.length > 0
        ? new Date(Math.max(...tradeDates.map(d => d.getTime()))).toISOString()
        : statistics.dateRange.latest;

      return {
        totalTrades,
        totalTradeValue,
        avgTradeMargin,
        mostActiveTrader,
        biggestWinner,
        blockbusterCount,
        dateRange: { earliest, latest }
      };
    }, [statistics, filteredTrades, filteredTeams]);

    return {
      filteredTrades,
      filteredTeams,
      filteredStats,
      seasonCounts,
      availableSeasons,
      totalFilteredCount: filteredTrades.length
    };
  }, [tradeData, seasonFilter]);
};

/**
 * Hook for managing season filter state
 * Provides default filter and state management utilities
 */
export const useSeasonFilter = (availableSeasons: string[]) => {
  const [seasonFilter, setSeasonFilter] = React.useState<SeasonFilter>(() => {
    // Default to "All Seasons" if multiple seasons available, otherwise the single season
    if (availableSeasons.length > 1) {
      return {
        type: 'all',
        seasons: availableSeasons,
        label: 'All Seasons'
      };
    } else if (availableSeasons.length === 1) {
      const season = availableSeasons[0];
      const seasonNumber = season.replace('season_', '');
      return {
        type: 'individual',
        seasons: [season],
        label: `Season ${seasonNumber}`
      };
    } else {
      return {
        type: 'all',
        seasons: [],
        label: 'No Seasons Available'
      };
    }
  });

  return {
    seasonFilter,
    setSeasonFilter
  };
};

export default useSeasonMetrics;