import { useState, useEffect, useMemo, useRef } from 'react';
import { Users, AlertCircle, ChevronUp, ChevronDown, Filter, X, Search, Calendar } from 'lucide-react';
import type { WaiverWireData, WaiverWireTransaction } from '../types/waiver-wire';

type SortField = keyof WaiverWireTransaction;
type SortDirection = 'asc' | 'desc';

interface FilterState {
  type: string[];
  action: string[];
  status: string[];
  player: string;
  bid: string;
  week: string[];
  globalSearch: string;
  dateFrom: string;
  dateTo: string;
}



export default function WaiverWireAnalysis() {
  const [data, setData] = useState<WaiverWireData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Sorting state
  const [sortField, setSortField] = useState<SortField>('created_date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  
  // Filtering state
  const [filters, setFilters] = useState<FilterState>({
    type: [],
    action: [],
    status: [],
    player: '',
    bid: '',
    week: [],
    globalSearch: '',
    dateFrom: '',
    dateTo: ''
  });
  
  // Column filter dropdown state
  const [activeColumnFilter, setActiveColumnFilter] = useState<SortField | null>(null);
  const filterRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api-waiver-wire.json');
        if (!response.ok) {
          throw new Error('Failed to fetch waiver wire data');
        }
        const waiverData = await response.json();
        setData(waiverData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Get unique values for filtering
  const uniqueValues = useMemo(() => {
    if (!data?.all_transactions) return null;
    
    const teams = [...new Set(data.all_transactions.map(t => t.team_name.trim()))].sort();
    const weeks = [...new Set(data.all_transactions.map(t => t.week.toString()))].sort((a, b) => Number(a) - Number(b));
    
    return {
      types: ['waiver', 'free_agent'],
      actions: ['add', 'drop'],
      statuses: ['complete', 'failed'],
      teams,
      weeks
    };
  }, [data]);

  // Filtered and sorted data
  const processedData = useMemo(() => {
    if (!data?.all_transactions) return [];
    
    console.log('Processing data with filters:', filters, 'sort:', sortField, sortDirection);
    
    let filtered = data.all_transactions.filter(transaction => {
      // Type filter
      if (filters.type.length > 0 && !filters.type.includes(transaction.type)) {
        return false;
      }
      
      // Action filter
      if (filters.action.length > 0 && !filters.action.includes(transaction.action)) {
        return false;
      }
      
      // Status filter
      if (filters.status.length > 0 && !filters.status.includes(transaction.status)) {
        return false;
      }
      

      
      // Player filter (text search)
      if (filters.player && !transaction.player_name.toLowerCase().includes(filters.player.toLowerCase())) {
        return false;
      }
      
      // Bid filter (text search)
      if (filters.bid && !transaction.waiver_bid.toString().includes(filters.bid)) {
        return false;
      }
      
      // Week filter
      if (filters.week.length > 0 && !filters.week.includes(transaction.week.toString())) {
        return false;
      }
      
      // Global search filter (searches across all text fields)
      if (filters.globalSearch) {
        const searchTerm = filters.globalSearch.toLowerCase();
        const searchableText = [
          transaction.player_name,
          transaction.team_name,
          transaction.type,
          transaction.action,
          transaction.status,
          transaction.waiver_bid.toString(),
          transaction.week.toString(),
          transaction.notes || ''
        ].join(' ').toLowerCase();
        
        if (!searchableText.includes(searchTerm)) {
          return false;
        }
      }
      
      // Date range filter
      if (filters.dateFrom || filters.dateTo) {
        const transactionDate = new Date(transaction.created_date);
        
        if (filters.dateFrom) {
          const fromDate = new Date(filters.dateFrom);
          if (transactionDate < fromDate) {
            return false;
          }
        }
        
        if (filters.dateTo) {
          const toDate = new Date(filters.dateTo);
          toDate.setHours(23, 59, 59, 999); // Include the entire end date
          if (transactionDate > toDate) {
            return false;
          }
        }
      }
      
      return true;
    });
    
    // Sort the filtered data - Create a new array to ensure React detects the change
    const sorted = [...filtered].sort((a, b) => {
      let aValue: any = a[sortField];
      let bValue: any = b[sortField];
      
      // Handle date sorting
      if (sortField === 'created_date' || sortField === 'status_updated_date') {
        aValue = new Date(aValue as string).getTime();
        bValue = new Date(bValue as string).getTime();
      }
      
      // Handle numeric sorting (waiver_bid, week, etc.)
      if (sortField === 'waiver_bid' || sortField === 'week' || sortField === 'roster_id' || sortField === 'sequence' || sortField === 'priority') {
        aValue = Number(aValue) || 0;
        bValue = Number(bValue) || 0;
      }
      
      // Handle string sorting (convert to lowercase for case-insensitive sorting)
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }
      
      // Compare values
      if (aValue < bValue) {
        return sortDirection === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortDirection === 'asc' ? 1 : -1;
      }
      return 0;
    });
    
    console.log('Processed data length:', sorted.length, 'First few items:', sorted.slice(0, 3).map(t => ({ id: t.transaction_id, player: t.player_name, date: t.created_date })));
    
    return sorted;
  }, [data, filters, sortField, sortDirection]);

  // Sorting handler
  const handleSort = (field: SortField) => {
    console.log('Sorting by:', field, 'Current direction:', sortDirection);
    if (sortField === field) {
      const newDirection = sortDirection === 'asc' ? 'desc' : 'asc';
      setSortDirection(newDirection);
      console.log('Toggled direction to:', newDirection);
    } else {
      setSortField(field);
      setSortDirection('asc');
      console.log('New field:', field, 'Direction: asc');
    }
  };

  // Filter handlers
  const handleMultiSelectFilter = (filterType: keyof FilterState, value: string) => {
    setFilters(prev => {
      const currentValues = prev[filterType] as string[];
      const newValues = currentValues.includes(value)
        ? currentValues.filter(v => v !== value)
        : [...currentValues, value];
      
      return {
        ...prev,
        [filterType]: newValues
      };
    });
  };

  const handleTextFilter = (filterType: keyof FilterState, value: string) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
  };

  const clearFilters = () => {
    setFilters({
      type: [],
      action: [],
      status: [],
      player: '',
      bid: '',
      week: [],
      globalSearch: '',
      dateFrom: '',
      dateTo: ''
    });
  };

  const hasActiveFilters = Object.values(filters).some(filter => 
    Array.isArray(filter) ? filter.length > 0 : filter !== ''
  );

  // Close column filter when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (activeColumnFilter && !Object.values(filterRefs.current).some(ref => 
        ref?.contains(event.target as Node)
      )) {
        setActiveColumnFilter(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [activeColumnFilter]);

  // Column filter component
  const ColumnFilterDropdown = ({ field, uniqueValues: fieldValues }: { 
    field: SortField; 
    uniqueValues: string[] | null;
  }) => {
    if (activeColumnFilter !== field) return null;

    const isMultiSelect = ['type', 'action', 'status', 'team', 'week'].includes(field);
    const isTextFilter = ['player_name', 'waiver_bid'].includes(field);

    return (
      <div 
        ref={(el) => filterRefs.current[field] = el}
        className="absolute top-full left-0 mt-1 w-64 bg-white border border-gray-200 rounded-md shadow-lg z-50"
      >
        <div className="p-3">
          {isTextFilter ? (
            <div>
              <input
                type="text"
                value={field === 'player_name' ? filters.player : filters.bid}
                onChange={(e) => handleTextFilter(field === 'player_name' ? 'player' : 'bid', e.target.value)}
                placeholder={`Search ${field === 'player_name' ? 'player' : 'bid'}...`}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>
          ) : isMultiSelect && fieldValues ? (
            <div className="max-h-48 overflow-y-auto space-y-2">
              {fieldValues.map(value => {
                const filterKey = field as keyof FilterState;
                const currentValues = filters[filterKey] as string[];
                
                return (
                  <label key={value} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={currentValues.includes(value)}
                      onChange={() => handleMultiSelectFilter(filterKey, value)}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      {field === 'type' && value === 'waiver' ? 'Waiver' :
                       field === 'type' && value === 'free_agent' ? 'Free Agent' :
                       field === 'week' ? `Week ${value}` :
                       value.charAt(0).toUpperCase() + value.slice(1)}
                    </span>
                  </label>
                );
              })}
            </div>
          ) : null}
          
          <div className="mt-3 pt-3 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => {
                if (field === 'player_name') handleTextFilter('player', '');
                else if (field === 'waiver_bid') handleTextFilter('bid', '');
                else {
                  const filterKey = field as keyof FilterState;
                  setFilters(prev => ({ ...prev, [filterKey]: [] }));
                }
              }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear
            </button>
            <button
              onClick={() => setActiveColumnFilter(null)}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="text-center">
          <div className="flex items-center justify-center mb-4">
            <Users className="h-8 w-8 text-primary-600 mr-3" />
            <h1 className="text-3xl font-bold text-gray-900">
              Waiver Wire Analysis
            </h1>
          </div>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            Comprehensive view of all waiver wire and free agent transactions
          </p>
        </div>
        
        <div className="card p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading waiver wire data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div className="text-center">
          <div className="flex items-center justify-center mb-4">
            <Users className="h-8 w-8 text-primary-600 mr-3" />
            <h1 className="text-3xl font-bold text-gray-900">
              Waiver Wire Analysis
            </h1>
          </div>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            Comprehensive view of all waiver wire and free agent transactions
          </p>
        </div>
        
        <div className="card p-8 text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Error Loading Data
          </h3>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  if (!data || !data.all_transactions) {
    return (
      <div className="space-y-8">
        <div className="text-center">
          <div className="flex items-center justify-center mb-4">
            <Users className="h-8 w-8 text-primary-600 mr-3" />
            <h1 className="text-3xl font-bold text-gray-900">
              Waiver Wire Analysis
            </h1>
          </div>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            Comprehensive view of all waiver wire and free agent transactions
          </p>
        </div>
        
        <div className="card p-8 text-center">
          <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">No waiver wire data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center mb-4">
          <Users className="h-8 w-8 text-primary-600 mr-3" />
          <h1 className="text-3xl font-bold text-gray-900">
            Waiver Wire Analysis
          </h1>
        </div>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto">
          Comprehensive view of all waiver wire and free agent transactions
        </p>
      </div>

      {/* Enhanced Table with Excel-style Column Filtering */}
      <div className="card">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              All Transactions ({processedData.length} of {data.all_transactions.length})
            </h2>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <X className="h-4 w-4 mr-1" />
                Clear All Filters
              </button>
            )}
          </div>
          
          {/* Search and Date Range Controls */}
          <div className="space-y-4 mb-4">
            {/* Global Search */}
            <div className="w-full">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  value={filters.globalSearch}
                  onChange={(e) => handleTextFilter('globalSearch', e.target.value)}
                  placeholder="Search transactions..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                />
              </div>
            </div>
            
            {/* Date Range */}
            <div className="flex flex-col gap-2 sm:flex-row sm:gap-2 sm:w-auto">
              <div className="relative flex-1 min-w-0">
                <Calendar className="absolute left-2 top-1/2 transform -translate-y-1/2 h-3 w-3 sm:h-4 sm:w-4 text-gray-400" />
                <input
                  type="date"
                  value={filters.dateFrom}
                  onChange={(e) => handleTextFilter('dateFrom', e.target.value)}
                  className="w-full pl-6 sm:pl-10 pr-1 sm:pr-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 text-xs sm:text-sm"
                  placeholder="From date"
                />
              </div>
              <div className="relative flex-1 min-w-0">
                <Calendar className="absolute left-2 top-1/2 transform -translate-y-1/2 h-3 w-3 sm:h-4 sm:w-4 text-gray-400" />
                <input
                  type="date"
                  value={filters.dateTo}
                  onChange={(e) => handleTextFilter('dateTo', e.target.value)}
                  className="w-full pl-6 sm:pl-10 pr-1 sm:pr-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 text-xs sm:text-sm"
                  placeholder="To date"
                />
              </div>
            </div>
          </div>
          
          {/* Active Filter Tags */}
          {hasActiveFilters && (
            <div className="flex flex-wrap gap-2">
              {/* Type filters */}
              {filters.type.map(type => (
                <span
                  key={`type-${type}`}
                  className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                    type === 'waiver' 
                      ? 'bg-blue-100 text-blue-800' 
                      : 'bg-green-100 text-green-800'
                  }`}
                >
                  Type: {type === 'waiver' ? 'Waiver' : 'Free Agent'}
                  <button
                    onClick={() => handleMultiSelectFilter('type', type)}
                    className={`ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full focus:outline-none ${
                      type === 'waiver' ? 'hover:bg-blue-200' : 'hover:bg-green-200'
                    }`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              
              {/* Action filters */}
              {filters.action.map(action => (
                <span
                  key={`action-${action}`}
                  className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                    action === 'add' 
                      ? 'bg-emerald-100 text-emerald-800' 
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  Action: {action.charAt(0).toUpperCase() + action.slice(1)}
                  <button
                    onClick={() => handleMultiSelectFilter('action', action)}
                    className={`ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full focus:outline-none ${
                      action === 'add' ? 'hover:bg-emerald-200' : 'hover:bg-red-200'
                    }`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              
              {/* Status filters */}
              {filters.status.map(status => (
                <span
                  key={`status-${status}`}
                  className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                    status === 'complete' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  Status: {status.charAt(0).toUpperCase() + status.slice(1)}
                  <button
                    onClick={() => handleMultiSelectFilter('status', status)}
                    className={`ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full focus:outline-none ${
                      status === 'complete' ? 'hover:bg-green-200' : 'hover:bg-red-200'
                    }`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              

              
              {/* Week filters */}
              {filters.week.map(week => (
                <span
                  key={`week-${week}`}
                  className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800"
                >
                  Week: {week}
                  <button
                    onClick={() => handleMultiSelectFilter('week', week)}
                    className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-indigo-200 focus:outline-none"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              
              {/* Player text filter */}
              {filters.player && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                  Player: "{filters.player}"
                  <button
                    onClick={() => handleTextFilter('player', '')}
                    className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-orange-200 focus:outline-none"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              
              {/* Bid text filter */}
              {filters.bid && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                  Bid: "{filters.bid}"
                  <button
                    onClick={() => handleTextFilter('bid', '')}
                    className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-yellow-200 focus:outline-none"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              
              {/* Global search filter */}
              {filters.globalSearch && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                  Search: "{filters.globalSearch}"
                  <button
                    onClick={() => handleTextFilter('globalSearch', '')}
                    className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-gray-200 focus:outline-none"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              
              {/* Date range filters */}
              {filters.dateFrom && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                  From: {new Date(filters.dateFrom).toLocaleDateString()}
                  <button
                    onClick={() => handleTextFilter('dateFrom', '')}
                    className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-slate-200 focus:outline-none"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              
              {filters.dateTo && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                  To: {new Date(filters.dateTo).toLocaleDateString()}
                  <button
                    onClick={() => handleTextFilter('dateTo', '')}
                    className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-slate-200 focus:outline-none"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
            </div>
          )}
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {/* Date Column */}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <div className="flex items-center justify-between">
                    <div 
                      className="flex items-center space-x-1 cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('created_date')}
                    >
                      <span>Date</span>
                      {sortField === 'created_date' && (
                        sortDirection === 'asc' ? 
                          <ChevronUp className="h-4 w-4" /> : 
                          <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                  </div>
                </th>

                {/* Type Column */}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative">
                  <div className="flex items-center justify-between">
                    <div 
                      className="flex items-center space-x-1 cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('type')}
                    >
                      <span>Type</span>
                      {sortField === 'type' && (
                        sortDirection === 'asc' ? 
                          <ChevronUp className="h-4 w-4" /> : 
                          <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                    <button
                      onClick={() => setActiveColumnFilter(activeColumnFilter === 'type' ? null : 'type')}
                      className={`ml-2 p-1 rounded hover:bg-gray-200 ${
                        filters.type.length > 0 ? 'text-primary-600' : 'text-gray-400'
                      }`}
                    >
                      <Filter className="h-3 w-3" />
                    </button>
                  </div>
                  <ColumnFilterDropdown field="type" uniqueValues={uniqueValues?.types || null} />
                </th>

                {/* Action Column */}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative">
                  <div className="flex items-center justify-between">
                    <div 
                      className="flex items-center space-x-1 cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('action')}
                    >
                      <span>Action</span>
                      {sortField === 'action' && (
                        sortDirection === 'asc' ? 
                          <ChevronUp className="h-4 w-4" /> : 
                          <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                    <button
                      onClick={() => setActiveColumnFilter(activeColumnFilter === 'action' ? null : 'action')}
                      className={`ml-2 p-1 rounded hover:bg-gray-200 ${
                        filters.action.length > 0 ? 'text-primary-600' : 'text-gray-400'
                      }`}
                    >
                      <Filter className="h-3 w-3" />
                    </button>
                  </div>
                  <ColumnFilterDropdown field="action" uniqueValues={uniqueValues?.actions || null} />
                </th>

                {/* Status Column */}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative">
                  <div className="flex items-center justify-between">
                    <div 
                      className="flex items-center space-x-1 cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('status')}
                    >
                      <span>Status</span>
                      {sortField === 'status' && (
                        sortDirection === 'asc' ? 
                          <ChevronUp className="h-4 w-4" /> : 
                          <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                    <button
                      onClick={() => setActiveColumnFilter(activeColumnFilter === 'status' ? null : 'status')}
                      className={`ml-2 p-1 rounded hover:bg-gray-200 ${
                        filters.status.length > 0 ? 'text-primary-600' : 'text-gray-400'
                      }`}
                    >
                      <Filter className="h-3 w-3" />
                    </button>
                  </div>
                  <ColumnFilterDropdown field="status" uniqueValues={uniqueValues?.statuses || null} />
                </th>

                {/* Team Column */}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <div className="flex items-center space-x-1 cursor-pointer hover:text-gray-700"
                       onClick={() => handleSort('team_name')}>
                    <span>Team</span>
                    {sortField === 'team_name' && (
                      sortDirection === 'asc' ? 
                        <ChevronUp className="h-4 w-4" /> : 
                        <ChevronDown className="h-4 w-4" />
                    )}
                  </div>
                </th>

                {/* Player Column */}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative">
                  <div className="flex items-center justify-between">
                    <div 
                      className="flex items-center space-x-1 cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('player_name')}
                    >
                      <span>Player</span>
                      {sortField === 'player_name' && (
                        sortDirection === 'asc' ? 
                          <ChevronUp className="h-4 w-4" /> : 
                          <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                    <button
                      onClick={() => setActiveColumnFilter(activeColumnFilter === 'player_name' ? null : 'player_name')}
                      className={`ml-2 p-1 rounded hover:bg-gray-200 ${
                        filters.player ? 'text-primary-600' : 'text-gray-400'
                      }`}
                    >
                      <Search className="h-3 w-3" />
                    </button>
                  </div>
                  <ColumnFilterDropdown field="player_name" uniqueValues={null} />
                </th>

                {/* Bid Column */}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative">
                  <div className="flex items-center justify-between">
                    <div 
                      className="flex items-center space-x-1 cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('waiver_bid')}
                    >
                      <span>Bid</span>
                      {sortField === 'waiver_bid' && (
                        sortDirection === 'asc' ? 
                          <ChevronUp className="h-4 w-4" /> : 
                          <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                    <button
                      onClick={() => setActiveColumnFilter(activeColumnFilter === 'waiver_bid' ? null : 'waiver_bid')}
                      className={`ml-2 p-1 rounded hover:bg-gray-200 ${
                        filters.bid ? 'text-primary-600' : 'text-gray-400'
                      }`}
                    >
                      <Search className="h-3 w-3" />
                    </button>
                  </div>
                  <ColumnFilterDropdown field="waiver_bid" uniqueValues={null} />
                </th>

                {/* Week Column */}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider relative">
                  <div className="flex items-center justify-between">
                    <div 
                      className="flex items-center space-x-1 cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('week')}
                    >
                      <span>Week</span>
                      {sortField === 'week' && (
                        sortDirection === 'asc' ? 
                          <ChevronUp className="h-4 w-4" /> : 
                          <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                    <button
                      onClick={() => setActiveColumnFilter(activeColumnFilter === 'week' ? null : 'week')}
                      className={`ml-2 p-1 rounded hover:bg-gray-200 ${
                        filters.week.length > 0 ? 'text-primary-600' : 'text-gray-400'
                      }`}
                    >
                      <Filter className="h-3 w-3" />
                    </button>
                  </div>
                  <ColumnFilterDropdown field="week" uniqueValues={uniqueValues?.weeks || null} />
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {processedData.map((transaction, index) => (
                <tr key={`${transaction.transaction_id}-${transaction.player_id}-${transaction.action}-${index}`} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(transaction.created_date).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      transaction.type === 'waiver' 
                        ? 'bg-blue-100 text-blue-800' 
                        : 'bg-green-100 text-green-800'
                    }`}>
                      {transaction.type === 'waiver' ? 'Waiver' : 'Free Agent'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      transaction.action === 'add' 
                        ? 'bg-emerald-100 text-emerald-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {transaction.action === 'add' ? 'Add' : 'Drop'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      transaction.status === 'complete' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {transaction.status === 'complete' ? 'Complete' : 'Failed'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {transaction.team_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {transaction.player_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {transaction.waiver_bid > 0 ? `${transaction.waiver_bid}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {transaction.week}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {processedData.length === 0 && (
          <div className="text-center py-12">
            <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">No transactions match your current filters</p>
          </div>
        )}
      </div>
    </div>
  );
}