import React, { useState, useMemo, memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Filter, ArrowUpDown, ArrowUp, ArrowDown, Calendar } from 'lucide-react';
import { api } from '../../services/api';

import ErrorMessage from '../UI/ErrorMessage';
import TradeDetailModal from '../Modals/TradeDetailModal';
import { ComponentErrorBoundary } from '../ErrorBoundary';
import { TableSkeleton } from '../UI/SkeletonLoader';
import { useDebounce } from '../../hooks/useDebounce';

interface Trade {
  tradeId: string;
  tradeDate: string;
  teamA: string;
  teamB: string;
  teamAReceived: string[];
  teamBReceived: string[];
  winnerCurrent: string;
  marginCurrent: number;
}

// Sortable Header Component
interface SortableHeaderProps {
  field: keyof Trade;
  label: string;
  align: 'left' | 'center' | 'right';
  onSort: (field: keyof Trade) => void;
  getSortIcon: (field: keyof Trade) => React.ReactNode;
}

const SortableHeader: React.FC<SortableHeaderProps> = ({ field, label, align, onSort, getSortIcon }) => {
  const alignClass = align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left';
  
  return (
    <th 
      className={`px-6 py-3 ${alignClass} text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors`}
      onClick={() => onSort(field)}
    >
      <div className="flex items-center justify-between">
        <span>{label}</span>
        {getSortIcon(field)}
      </div>
    </th>
  );
};

const RecentTradesTable: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<keyof Trade>('tradeDate');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [selectedTeam, setSelectedTeam] = useState('');
  const [maxResults, setMaxResults] = useState(20);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Debounce search term to avoid excessive filtering
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  const { 
    data: tradesData, 
    isLoading, 
    error,
    refetch 
  } = useQuery({
    queryKey: ['trades', 'recent', maxResults],
    queryFn: () => api.getTrades({ maxResults }),
  });

  const { data: teamsData } = useQuery({
    queryKey: ['teams'],
    queryFn: () => api.getTeams(),
  });

  const trades = tradesData?.data?.data?.trades || [];
  const teams = teamsData?.data?.data?.teams || [];

  // Filter and sort trades
  const filteredAndSortedTrades = useMemo(() => {
    let filteredTrades = [...trades];

    // Apply filters
    filteredTrades = filteredTrades.filter(trade => {
      const matchesSearch = 
        trade.teamA.toLowerCase().includes(debouncedSearchTerm.toLowerCase()) ||
        trade.teamB.toLowerCase().includes(debouncedSearchTerm.toLowerCase()) ||
        trade.teamAReceived.some((asset: any) => asset.toLowerCase().includes(debouncedSearchTerm.toLowerCase())) ||
        trade.teamBReceived.some((asset: any) => asset.toLowerCase().includes(debouncedSearchTerm.toLowerCase()));
      
      const matchesTeam = !selectedTeam || trade.teamA === selectedTeam || trade.teamB === selectedTeam;
      
      // Date range filtering
      const tradeDate = new Date(trade.tradeDate);
      const matchesStartDate = !startDate || tradeDate >= new Date(startDate);
      const matchesEndDate = !endDate || tradeDate <= new Date(endDate);
      
      return matchesSearch && matchesTeam && matchesStartDate && matchesEndDate;
    });

    // Apply sorting
    filteredTrades.sort((a, b) => {
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

    return filteredTrades;
  }, [trades, debouncedSearchTerm, sortField, sortDirection, selectedTeam, startDate, endDate]);

  const handleSort = (field: keyof Trade) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection(field === 'tradeDate' ? 'desc' : 'asc');
    }
  };

  const getSortIcon = (field: keyof Trade) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3 text-gray-400" />;
    return sortDirection === 'asc' 
      ? <ArrowUp className="h-3 w-3 text-primary-600" />
      : <ArrowDown className="h-3 w-3 text-primary-600" />;
  };

  const formatAssets = (assets: string[]) => {
    if (!assets || assets.length === 0) return ['No assets'];
    return assets;
  };

  const handleTradeClick = (trade: Trade) => {
    setSelectedTrade(trade);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedTrade(null);
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap gap-4 items-center bg-gray-50 p-4 rounded-lg animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-64"></div>
          <div className="h-8 bg-gray-200 rounded w-32"></div>
          <div className="h-8 bg-gray-200 rounded w-40"></div>
          <div className="h-8 bg-gray-200 rounded w-24"></div>
        </div>
        <TableSkeleton rows={6} columns={5} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to Load Trades"
        message={error instanceof Error ? error.message : 'Unknown error occurred'}
        onRetry={async () => { await refetch(); }}
      />
    );
  }



  return (
    <ComponentErrorBoundary componentName="RecentTradesTable">
      <div className="space-y-4">
        {/* Filter Controls */}
        <div className="flex flex-wrap gap-4 items-center bg-gray-50 p-4 rounded-lg">
        <div className="flex items-center space-x-2">
          <Search className="h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search trades, teams, or assets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 w-64"
          />
        </div>
        
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <select
            value={selectedTeam}
            onChange={(e) => setSelectedTeam(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Teams</option>
            {teams.map((team: any) => (
              <option key={team.sleeperUsername} value={team.sleeperUsername}>
                {team.realName}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <Calendar className="h-4 w-4 text-gray-500" />
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="Start date"
          />
          <span className="text-gray-500">to</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="End date"
          />
        </div>

        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-600">Show:</label>
          <select
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value={10}>10 trades</option>
            <option value={20}>20 trades</option>
            <option value={50}>50 trades</option>
            <option value={100}>100 trades</option>
          </select>
        </div>

        {(searchTerm || selectedTeam || startDate || endDate) && (
          <button
            onClick={() => {
              setSearchTerm('');
              setSelectedTeam('');
              setStartDate('');
              setEndDate('');
            }}
            className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-100 transition-colors"
          >
            Clear Filters
          </button>
        )}

        <div className="text-sm text-gray-500">
          Showing {filteredAndSortedTrades.length} of {trades.length} trades • Click any row for details
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <SortableHeader field="tradeDate" label="Date" align="left" onSort={handleSort} getSortIcon={getSortIcon} />
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Teams
              </th>
              <SortableHeader field="winnerCurrent" label="Winner" align="left" onSort={handleSort} getSortIcon={getSortIcon} />
              <SortableHeader field="marginCurrent" label="Margin" align="right" onSort={handleSort} getSortIcon={getSortIcon} />
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Assets Traded
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredAndSortedTrades.map((trade) => (
              <tr 
                key={trade.tradeId} 
                className="hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => handleTradeClick(trade)}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(trade.tradeDate).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {trade.teamA} ↔ {trade.teamB}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    {trade.winnerCurrent}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                  {Math.round(trade.marginCurrent)} pts
                </td>
                <td className="px-6 py-4 text-sm text-gray-900 min-w-96 max-w-md">
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs font-medium text-blue-600 mb-1">{trade.teamA} receives:</div>
                      <div className="space-y-1">
                        {formatAssets(trade.teamAReceived).map((asset: any, index: number) => (
                          <div key={index} className="text-sm text-gray-900 bg-blue-50 px-2 py-1 rounded border-l-2 border-blue-200">
                            {asset}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-green-600 mb-1">{trade.teamB} receives:</div>
                      <div className="space-y-1">
                        {formatAssets(trade.teamBReceived).map((asset: any, index: number) => (
                          <div key={index} className="text-sm text-gray-900 bg-green-50 px-2 py-1 rounded border-l-2 border-green-200">
                            {asset}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

        {/* Trade Detail Modal */}
        <TradeDetailModal
          trade={selectedTrade}
          isOpen={isModalOpen}
          onClose={handleCloseModal}
        />
      </div>
    </ComponentErrorBoundary>
  );
};

export default memo(RecentTradesTable);