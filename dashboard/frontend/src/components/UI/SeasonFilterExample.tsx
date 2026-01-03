import React from 'react';
import { useQuery } from '@tanstack/react-query';
import SeasonFilter from './SeasonFilter';
import { useSeasonMetrics, useSeasonFilter } from '../../hooks/useSeasonMetrics';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';
import type { TradeData } from '../../types';

/**
 * Example component demonstrating how to integrate SeasonFilter with useSeasonMetrics
 * This shows the complete pattern for season-aware data filtering
 */
const SeasonFilterExample: React.FC = () => {
  // Fetch trade data (using the existing API pattern)
  const { 
    data: tradeData, 
    isLoading, 
    error 
  } = useQuery<TradeData>({
    queryKey: ['trades'],
    queryFn: () => fetch('/api-trades.json').then(r => {
      if (!r.ok) throw new Error('Failed to fetch trade data');
      return r.json();
    }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Get available seasons from the data
  const availableSeasons = tradeData?.metadata?.seasons_included || [];
  
  // Initialize season filter state
  const { seasonFilter, setSeasonFilter } = useSeasonFilter(availableSeasons);
  
  // Calculate filtered metrics
  const {
    filteredTeams,
    filteredStats,
    seasonCounts,
    totalFilteredCount
  } = useSeasonMetrics(tradeData, seasonFilter);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <LoadingSpinner size="lg" />
        <span className="ml-3 text-gray-600">Loading trade data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to Load Trade Data"
        message={error instanceof Error ? error.message : 'Unknown error occurred'}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Season Filtering Example
        </h2>
        <p className="text-gray-600">
          This demonstrates how to use the SeasonFilter component with the useSeasonMetrics hook
          for client-side filtering of multi-season data.
        </p>
      </div>

      {/* Season Filter */}
      <div className="bg-white p-6 rounded-lg shadow">
        <SeasonFilter
          availableSeasons={availableSeasons}
          seasonCounts={seasonCounts}
          selectedFilter={seasonFilter}
          onFilterChange={setSeasonFilter}
          className="max-w-xs"
        />
      </div>

      {/* Filtered Results Summary */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Filtered Results Summary
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">
              {totalFilteredCount}
            </div>
            <div className="text-sm text-blue-800">
              Total Trades
            </div>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-green-600">
              {filteredTeams.length}
            </div>
            <div className="text-sm text-green-800">
              Active Teams
            </div>
          </div>
          
          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-purple-600">
              {seasonFilter.seasons.length}
            </div>
            <div className="text-sm text-purple-800">
              Seasons Selected
            </div>
          </div>
        </div>

        {/* Season Breakdown */}
        {seasonFilter.type !== 'all' && (
          <div className="mt-4">
            <h4 className="text-md font-medium text-gray-700 mb-2">
              Season Breakdown:
            </h4>
            <div className="space-y-1">
              {seasonFilter.seasons.map(season => (
                <div key={season} className="flex justify-between text-sm">
                  <span className="text-gray-600">
                    Season {season.replace('season_', '')}:
                  </span>
                  <span className="font-medium">
                    {seasonCounts[season] || 0} trades
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Filtered Statistics */}
      {filteredStats && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            League Statistics (Filtered)
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-600">Total Trade Value</div>
              <div className="text-xl font-bold text-gray-900">
                ${filteredStats.totalTradeValue.toLocaleString()}
              </div>
            </div>
            
            <div>
              <div className="text-sm text-gray-600">Avg Trade Margin</div>
              <div className="text-xl font-bold text-gray-900">
                {filteredStats.avgTradeMargin.toFixed(1)} pts
              </div>
            </div>
            
            <div>
              <div className="text-sm text-gray-600">Most Active Trader</div>
              <div className="text-xl font-bold text-gray-900">
                {filteredStats.mostActiveTrader || 'N/A'}
              </div>
            </div>
            
            <div>
              <div className="text-sm text-gray-600">Blockbuster Trades</div>
              <div className="text-xl font-bold text-gray-900">
                {filteredStats.blockbusterCount}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top Teams (Filtered) */}
      {filteredTeams.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Top Teams by Win Rate (Filtered)
          </h3>
          
          <div className="space-y-2">
            {filteredTeams.slice(0, 5).map((team, index) => (
              <div key={team.teamName} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="text-lg font-bold text-gray-500">
                    #{index + 1}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">
                      {team.teamName}
                    </div>
                    <div className="text-sm text-gray-600">
                      {team.tradeCount} trades
                    </div>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className="text-lg font-bold text-gray-900">
                    {(team.winRate * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600">
                    win rate
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debug Information */}
      <details className="bg-gray-50 p-4 rounded-lg">
        <summary className="cursor-pointer font-medium text-gray-700">
          Debug Information (Click to expand)
        </summary>
        <pre className="mt-2 text-xs text-gray-600 overflow-auto">
          {JSON.stringify({
            availableSeasons,
            seasonCounts,
            selectedFilter: seasonFilter,
            totalFilteredCount,
            metadataSeasons: tradeData?.metadata?.seasons_included,
            metadataTradesBySeasons: tradeData?.metadata?.trades_by_season
          }, null, 2)}
        </pre>
      </details>
    </div>
  );
};

export default SeasonFilterExample;