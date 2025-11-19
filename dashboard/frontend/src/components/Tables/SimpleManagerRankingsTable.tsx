import React, { useState, useMemo, memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Filter, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { api } from '../../services/api';

import ErrorMessage from '../UI/ErrorMessage';
import { Team, TeamSortField, SortConfig } from '../../types/team';
import { ComponentErrorBoundary } from '../ErrorBoundary';
import { TableSkeleton } from '../UI/SkeletonLoader';
import { useDebounce } from '../../hooks/useDebounce';

const SimpleManagerRankingsTable: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [minTrades, setMinTrades] = useState(0);
  const [performanceTier, setPerformanceTier] = useState<'all' | 'winners' | 'losers'>('all');
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'totalValueGained',
    direction: 'desc'
  });

  // Debounce search term to avoid excessive filtering
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  const { 
    data: teamsData, 
    isLoading, 
    error,
    refetch 
  } = useQuery({
    queryKey: ['teams'],
    queryFn: () => api.getTeams(),
  });

  // Safely extract and validate teams data
  // Both dev and prod now return: { success: true, data: { teams: [...] } }
  const rawTeams = teamsData?.data?.teams || [];
  
  // Safely normalize team data with proper type checking
  // MUST be called before any early returns to maintain hook order
  const teams: Team[] = useMemo(() => {
    return rawTeams.map((team: any): Team => ({
      sleeperUsername: String(team?.sleeperUsername || ''),
      realName: String(team?.realName || 'Unknown'),
      tradeCount: Number(team?.tradeCount) || 0,
      totalValueGained: Number(team?.totalValueGained) || 0,
      winRate: Number(team?.winRate) || 0,
    }));
  }, [rawTeams]);

  // Safe filtering and sorting with proper error handling
  // MUST be called before any early returns to maintain hook order
  const processedTeams = useMemo(() => {
    try {
      // Filter teams with multiple criteria
      let filteredTeams = teams.filter((team) => {
        // Search term filter (using debounced value)
        const matchesSearch = !debouncedSearchTerm || 
          team.realName.toLowerCase().includes(debouncedSearchTerm.toLowerCase());
        
        // Minimum trades filter
        const meetsMinTrades = team.tradeCount >= minTrades;
        
        // Performance tier filter
        const meetsPerformanceTier = (() => {
          switch (performanceTier) {
            case 'winners':
              return team.totalValueGained > 0;
            case 'losers':
              return team.totalValueGained < 0;
            case 'all':
            default:
              return true;
          }
        })();
        
        return matchesSearch && meetsMinTrades && meetsPerformanceTier;
      });

      // Sort teams with safe comparison
      filteredTeams.sort((a, b) => {
        const aVal = a[sortConfig.field];
        const bVal = b[sortConfig.field];
        
        // Handle string comparison
        if (typeof aVal === 'string' && typeof bVal === 'string') {
          const comparison = aVal.localeCompare(bVal);
          return sortConfig.direction === 'asc' ? comparison : -comparison;
        }
        
        // Handle numeric comparison
        const numA = Number(aVal) || 0;
        const numB = Number(bVal) || 0;
        const comparison = numA - numB;
        return sortConfig.direction === 'asc' ? comparison : -comparison;
      });

      return filteredTeams;
    } catch (error) {
      console.error('Error processing teams data:', error);
      return [];
    }
  }, [teams, debouncedSearchTerm, minTrades, performanceTier, sortConfig]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap gap-4 items-center bg-gray-50 p-4 rounded-lg animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48"></div>
          <div className="h-8 bg-gray-200 rounded w-32"></div>
          <div className="h-8 bg-gray-200 rounded w-40"></div>
        </div>
        <TableSkeleton rows={8} columns={5} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to Load Rankings"
        message={error instanceof Error ? error.message : 'Unknown error occurred'}
        onRetry={async () => { await refetch(); }}
      />
    );
  }

  // Sorting handlers
  const handleSort = (field: TeamSortField) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  const getSortIcon = (field: TeamSortField) => {
    if (sortConfig.field !== field) {
      return <ArrowUpDown className="h-3 w-3 text-gray-400" />;
    }
    return sortConfig.direction === 'asc' 
      ? <ArrowUp className="h-3 w-3 text-primary-600" />
      : <ArrowDown className="h-3 w-3 text-primary-600" />;
  };

  return (
    <ComponentErrorBoundary componentName="SimpleManagerRankingsTable">
      <div className="space-y-4">
        {/* Advanced Filter Controls */}
        <div className="flex flex-wrap gap-4 items-center bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center space-x-2">
          <Search className="h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search managers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 w-48"
          />
        </div>
        
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <label className="text-sm text-gray-600">Min trades:</label>
          <input
            type="number"
            min="0"
            value={minTrades}
            onChange={(e) => setMinTrades(Number(e.target.value))}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm w-20 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-600">Performance:</label>
          <select
            value={performanceTier}
            onChange={(e) => setPerformanceTier(e.target.value as 'all' | 'winners' | 'losers')}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Managers</option>
            <option value="winners">Winners Only (+)</option>
            <option value="losers">Losers Only (-)</option>
          </select>
        </div>

        {(searchTerm || minTrades > 0 || performanceTier !== 'all') && (
          <button
            onClick={() => {
              setSearchTerm('');
              setMinTrades(0);
              setPerformanceTier('all');
            }}
            className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-100 transition-colors"
          >
            Clear Filters
          </button>
        )}

        <div className="text-sm text-gray-500">
          Showing {processedTeams.length} of {teams.length} managers
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rank
              </th>
              <th 
                className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('realName')}
              >
                <div className="flex items-center justify-between">
                  <span>Manager</span>
                  {getSortIcon('realName')}
                </div>
              </th>
              <th 
                className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('tradeCount')}
              >
                <div className="flex items-center justify-between">
                  <span>Trades</span>
                  {getSortIcon('tradeCount')}
                </div>
              </th>
              <th 
                className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('totalValueGained')}
              >
                <div className="flex items-center justify-between">
                  <span>Total Score</span>
                  {getSortIcon('totalValueGained')}
                </div>
              </th>
              <th 
                className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('winRate')}
              >
                <div className="flex items-center justify-between">
                  <span>Win Rate</span>
                  {getSortIcon('winRate')}
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {processedTeams.map((team, index) => (
              <tr key={team.sleeperUsername || index} className="hover:bg-gray-50">
                <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                  #{index + 1}
                </td>
                <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {team.realName}
                </td>
                <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900 text-center">
                  {team.tradeCount}
                </td>
                <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                  <span className={`font-medium ${team.totalValueGained >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {team.totalValueGained >= 0 ? '+' : ''}{Math.round(team.totalValueGained)}
                  </span>
                </td>
                <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900 text-center">
                  <span className={`font-medium ${team.winRate >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                    {Math.round(team.winRate)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </div>
    </ComponentErrorBoundary>
  );
};

export default memo(SimpleManagerRankingsTable);