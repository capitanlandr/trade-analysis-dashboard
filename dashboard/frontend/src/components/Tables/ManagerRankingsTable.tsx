import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Crown, Target, Search, Filter, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { api } from '../../services/api';
import LoadingSpinner from '../UI/LoadingSpinner';
import ErrorMessage from '../UI/ErrorMessage';

interface ManagerRanking {
  rank: number;
  manager: string;
  trades: number;
  totalScore: number;
  totalGained: number;
  totalLost: number;
  avgPerTrade: number;
  volatility: number;
  currentWins: number;
  currentWinRate: number;
  swingWins: number;
  swingWinRate: number;
  tradeFlips: number;
  playersNet: number;
  picksNet: number;
  assetTurnover: number;
}

// Sortable Header Component
interface SortableHeaderProps {
  field: keyof ManagerRanking;
  label: string;
  align: 'left' | 'center' | 'right';
  onSort: (field: keyof ManagerRanking) => void;
  getSortIcon: (field: keyof ManagerRanking) => React.ReactNode;
}

const SortableHeader: React.FC<SortableHeaderProps> = ({ field, label, align, onSort, getSortIcon }) => {
  const alignClass = align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left';
  
  return (
    <th 
      className={`px-3 py-3 ${alignClass} text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors`}
      onClick={() => onSort(field)}
    >
      <div className="flex items-center justify-between">
        <span>{label}</span>
        {getSortIcon(field)}
      </div>
    </th>
  );
};

const ManagerRankingsTable: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<keyof ManagerRanking>('totalScore');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [minTrades, setMinTrades] = useState(0);

  const { 
    data: teamsData, 
    isLoading, 
    error,
    refetch 
  } = useQuery({
    queryKey: ['teams', 'rankings'],
    queryFn: () => api.getTeams({ sortBy: 'totalValueGained', order: 'desc' }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <LoadingSpinner />
        <span className="ml-3 text-gray-600">Loading manager rankings...</span>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to Load Rankings"
        message={error instanceof Error ? error.message : 'Unknown error occurred'}
        onRetry={refetch}
      />
    );
  }

  const teams = teamsData?.data?.data?.teams || [];
  
  // Convert team data to manager rankings format and apply filtering/sorting
  const filteredAndSortedRankings = useMemo(() => {
    let rankings: ManagerRanking[] = teams.map((team: any) => ({
      rank: 0, // Will be set after sorting
      manager: team?.realName || 'Unknown',
      trades: team?.tradeCount || 0,
      totalScore: Math.round(team?.totalValueGained || 0),
      totalGained: Math.max(0, Math.round(team?.totalValueGained || 0)),
      totalLost: Math.max(0, Math.round(-Math.min(0, team?.totalValueGained || 0))),
      avgPerTrade: (team?.tradeCount || 0) > 0 ? Math.round((team?.totalValueGained || 0) / (team?.tradeCount || 1)) : 0,
      volatility: Math.round(team?.avgMargin || 0),
      currentWins: Math.round(((team?.winRate || 0) / 100) * (team?.tradeCount || 0)),
      currentWinRate: team?.winRate || 0,
      swingWins: 0,
      swingWinRate: 0,
      tradeFlips: 0,
      playersNet: 0,
      picksNet: 0,
      assetTurnover: 0,
    }));

    // Apply filters
    rankings = rankings.filter(ranking => {
      const matchesSearch = ranking.manager.toLowerCase().includes(searchTerm.toLowerCase());
      const meetsMinTrades = ranking.trades >= minTrades;
      return matchesSearch && meetsMinTrades;
    });

    // Apply sorting
    rankings.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc' 
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      
      const numA = Number(aVal);
      const numB = Number(bVal);
      return sortDirection === 'asc' ? numA - numB : numB - numA;
    });

    // Set ranks after sorting
    rankings.forEach((ranking, index) => {
      ranking.rank = index + 1;
    });

    return rankings;
  }, [teams, searchTerm, sortField, sortDirection, minTrades]);

  const handleSort = (field: keyof ManagerRanking) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getSortIcon = (field: keyof ManagerRanking) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3 text-gray-400" />;
    return sortDirection === 'asc' 
      ? <ArrowUp className="h-3 w-3 text-primary-600" />
      : <ArrowDown className="h-3 w-3 text-primary-600" />;
  };

  return (
    <div className="space-y-4">
      {/* Filter Controls */}
      <div className="flex flex-wrap gap-4 items-center bg-gray-50 p-4 rounded-lg">
        <div className="flex items-center space-x-2">
          <Search className="h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search managers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <label className="text-sm text-gray-600">Min Trades:</label>
          <input
            type="number"
            min="0"
            value={minTrades}
            onChange={(e) => setMinTrades(Number(e.target.value))}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm w-20 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div className="text-sm text-gray-500">
          Showing {filteredAndSortedRankings.length} of {teams.length} managers
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Rank
            </th>
            <SortableHeader field="manager" label="Manager" align="left" onSort={handleSort} getSortIcon={getSortIcon} />
            <SortableHeader field="trades" label="Trades" align="center" onSort={handleSort} getSortIcon={getSortIcon} />
            <SortableHeader field="totalScore" label="Total Score" align="right" onSort={handleSort} getSortIcon={getSortIcon} />
            <SortableHeader field="avgPerTrade" label="Avg/Trade" align="right" onSort={handleSort} getSortIcon={getSortIcon} />
            <SortableHeader field="currentWinRate" label="Win %" align="center" onSort={handleSort} getSortIcon={getSortIcon} />
            <SortableHeader field="volatility" label="Volatility" align="right" onSort={handleSort} getSortIcon={getSortIcon} />
            <SortableHeader field="currentWins" label="Wins" align="center" onSort={handleSort} getSortIcon={getSortIcon} />
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {filteredAndSortedRankings.map((ranking) => (
            <ManagerRankingRow key={ranking.manager} ranking={ranking} />
          ))}
        </tbody>
      </table>
      
      <div className="mt-4 text-sm text-gray-500">
        <p className="flex items-center">
          <Crown className="h-4 w-4 mr-1 text-yellow-500" />
          Rankings based on total value gained from trades. 
          <span className="ml-2">Volatility = average trade margin.</span>
        </p>
        </div>
      
        <div className="mt-4 text-sm text-gray-500">
          <p className="flex items-center">
            <Crown className="h-4 w-4 mr-1 text-yellow-500" />
            Rankings based on total value gained from trades. 
            <span className="ml-2">Volatility = average trade margin.</span>
          </p>
        </div>
      </div>
    </div>
  );


};

interface ManagerRankingRowProps {
  ranking: ManagerRanking;
}

const ManagerRankingRow: React.FC<ManagerRankingRowProps> = ({ ranking }) => {
  const getRankBadge = (rank: number) => {
    if (rank === 1) return <Crown className="h-4 w-4 text-yellow-500" />;
    if (rank === 2) return <span className="text-gray-400 font-bold">2</span>;
    if (rank === 3) return <span className="text-amber-600 font-bold">3</span>;
    return <span className="text-gray-600">{rank}</span>;
  };

  const getScoreColor = (score: number) => {
    if (score > 1000) return 'text-green-700 font-semibold';
    if (score > 0) return 'text-green-600';
    if (score > -1000) return 'text-red-600';
    return 'text-red-700 font-semibold';
  };

  const getWinRateColor = (winRate: number) => {
    if (winRate >= 60) return 'text-green-700';
    if (winRate >= 50) return 'text-green-600';
    if (winRate >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-3 py-4 whitespace-nowrap">
        <div className="flex items-center justify-center">
          {getRankBadge(ranking.rank)}
        </div>
      </td>
      <td className="px-4 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="font-medium text-gray-900">
            {ranking.manager}
          </div>
          {ranking.rank <= 3 && (
            <Target className="h-3 w-3 ml-2 text-primary-500" />
          )}
        </div>
      </td>
      <td className="px-3 py-4 whitespace-nowrap text-center text-sm text-gray-900">
        {ranking.trades}
      </td>
      <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
        <span className={getScoreColor(ranking.totalScore)}>
          {ranking.totalScore > 0 ? '+' : ''}{ranking.totalScore.toLocaleString()}
        </span>
      </td>
      <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
        <span className={getScoreColor(ranking.avgPerTrade)}>
          {ranking.avgPerTrade > 0 ? '+' : ''}{ranking.avgPerTrade}
        </span>
      </td>
      <td className="px-3 py-4 whitespace-nowrap text-center text-sm">
        <span className={getWinRateColor(ranking.currentWinRate)}>
          {ranking.currentWinRate.toFixed(0)}%
        </span>
      </td>
      <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-gray-900">
        {ranking.volatility.toLocaleString()}
      </td>
      <td className="px-3 py-4 whitespace-nowrap text-center text-sm text-gray-900">
        {ranking.currentWins}
      </td>
    </tr>
  );
};

export default ManagerRankingsTable;