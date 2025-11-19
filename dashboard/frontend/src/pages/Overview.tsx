import React, { memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, Users, TrendingUp, Trophy, Calendar, DollarSign } from 'lucide-react';
import { api } from '../services/api';

import ErrorMessage from '../components/UI/ErrorMessage';
import SimpleManagerRankingsTable from '../components/Tables/SimpleManagerRankingsTable';
import RecentTradesTable from '../components/Tables/RecentTradesTable';
import { ComponentErrorBoundary } from '../components/ErrorBoundary';
import { MetricCardSkeleton, CardSkeleton } from '../components/UI/SkeletonLoader';

const Overview: React.FC = () => {
  const { 
    data: statsData, 
    isLoading: statsLoading, 
    error: statsError,
    refetch: refetchStats 
  } = useQuery({
    queryKey: ['stats', 'summary'],
    queryFn: async () => {
      console.log('Fetching stats summary...');
      try {
        const result = await api.getStatsSummary();
        console.log('Stats API result:', result);
        return result;
      } catch (error) {
        console.error('Stats API error:', error);
        throw error;
      }
    },
    retry: 3,
    retryDelay: 1000,
  });

  const { 
    isLoading: tradesLoading
  } = useQuery({
    queryKey: ['trades', 'recent'],
    queryFn: () => api.getTrades({ maxResults: 10 }),
  });



  // Enhanced logging
  console.log('Overview state:', {
    statsLoading,
    tradesLoading,
    statsError: statsError?.message,
    hasStatsData: !!statsData
  });

  if (statsLoading || tradesLoading) {
    return (
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">League Overview</h1>
          <p className="text-gray-600 mt-2">
            Your fantasy football trade analysis dashboard
          </p>
        </div>

        {/* Loading Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, index) => (
            <MetricCardSkeleton key={index} />
          ))}
        </div>

        {/* Loading League Leaders */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CardSkeleton />
          <CardSkeleton />
        </div>

        {/* Loading Tables */}
        <div className="space-y-6">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  if (statsError) {
    return (
      <ErrorMessage
        title="Failed to Load Dashboard"
        message={statsError instanceof Error ? statsError.message : 'Unknown error occurred'}
        onRetry={() => { refetchStats(); }}
      />
    );
  }

  // Extract stats - now consistent between dev and prod
  // Both return: { success: true, data: { overview: {...} } }
  const stats = (statsData as any)?.data;
  
  // Debug logging
  console.log('Overview Debug:', {
    statsData,
    stats,
    totalTrades: stats?.overview?.totalTrades,
    totalValue: stats?.overview?.totalTradeValue,
    mostActive: stats?.overview?.mostActiveTrader
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">League Overview</h1>
        <p className="text-gray-600 mt-2">
          Your fantasy football trade analysis dashboard
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Trades"
          value={stats?.overview?.totalTrades || 0}
          icon={BarChart3}
          color="blue"
        />
        <MetricCard
          title="Placeholder 1"
          value="TBD"
          icon={DollarSign}
          color="green"
        />
        <MetricCard
          title="Placeholder 2"
          value="TBD"
          icon={Users}
          color="yellow"

        />
        <MetricCard
          title="Avg Margin"
          value={Math.round(stats?.overview?.avgTradeMargin || 0)}
          icon={TrendingUp}
          color="purple"
          subtitle="Points per trade"
        />
      </div>

      {/* League Leaders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Users className="h-5 w-5 mr-2 text-primary-600" />
            League Leaders
          </h2>
          <div className="space-y-4">
            <LeaderItem
              label="Most Active Trader"
              value={stats?.overview?.mostActiveTrader || 'N/A'}
              subtitle={`${stats?.teamRankings?.byTradeCount?.[0]?.tradeCount || 0} trades`}
            />
            <LeaderItem
              label="Trade Season"
              value={(() => {
                const start = stats?.overview?.dateRange?.earliest;
                const end = stats?.overview?.dateRange?.latest;
                if (!start || !end) return 'N/A';
                
                const formatDate = (dateStr: string) => {
                  const [year, month, day] = dateStr.split('-').map(Number);
                  const date = new Date(year, month - 1, day);
                  const monthName = date.toLocaleDateString('en-US', { month: 'long' });
                  const dayNum = date.getDate();
                  const suffix = dayNum === 1 || dayNum === 21 || dayNum === 31 ? 'st' :
                                 dayNum === 2 || dayNum === 22 ? 'nd' :
                                 dayNum === 3 || dayNum === 23 ? 'rd' : 'th';
                  return `${monthName} ${dayNum}${suffix}, ${year}`;
                };
                
                return `${formatDate(start)} to ${formatDate(end)}`;
              })()}
              subtitle="Active trading period"
            />
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <TrendingUp className="h-5 w-5 mr-2 text-green-600" />
            Top Performers
          </h2>
          <div className="space-y-3">
            {stats?.teamRankings?.byValueGained?.slice(0, 3).map((team: any, index: number) => (
              <TopPerformerItem key={team.realName} team={team} rank={index + 1} />
            )) || (
              <p className="text-gray-500 text-center py-8">Loading top performers...</p>
            )}
          </div>
        </div>
      </div>

      {/* Manager Rankings Table */}
      <ComponentErrorBoundary componentName="Manager Rankings Section">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Trophy className="h-5 w-5 mr-2 text-primary-600" />
            Manager Trade Skill Rankings
          </h2>
          <div className="overflow-x-auto">
            <SimpleManagerRankingsTable />
          </div>
        </div>
      </ComponentErrorBoundary>

      {/* Recent Trades */}
      <ComponentErrorBoundary componentName="Recent Trades Section">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Calendar className="h-5 w-5 mr-2 text-primary-600" />
            Recent Trades
          </h2>
          <RecentTradesTable />
        </div>
      </ComponentErrorBoundary>
    </div>
  );
};

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  color: 'blue' | 'green' | 'yellow' | 'purple';
  subtitle?: string;
}

const MetricCard: React.FC<MetricCardProps> = memo(({ title, value, icon: Icon, color, subtitle }) => {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-100',
    green: 'text-green-600 bg-green-100',
    yellow: 'text-yellow-600 bg-yellow-100',
    purple: 'text-purple-600 bg-purple-100',
  };

  return (
    <div className="card">
      <div className="flex items-center">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
});

interface LeaderItemProps {
  label: string;
  value: string;
  subtitle: string;
}

const LeaderItem: React.FC<LeaderItemProps> = memo(({ label, value, subtitle }) => (
  <div className="flex justify-between items-center">
    <div>
      <p className="text-sm font-medium text-gray-900">{label}</p>
      <p className="text-xs text-gray-500">{subtitle}</p>
    </div>
    <p className="text-sm font-semibold text-primary-600">{value}</p>
  </div>
));

interface TopPerformerItemProps {
  team: any;
  rank: number;
}

const TopPerformerItem: React.FC<TopPerformerItemProps> = memo(({ team, rank }) => {
  const getRankIcon = (rank: number) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
  };
  
  return (
    <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
      <div>
        <p className="text-sm font-medium text-gray-900 flex items-center">
          <span className="mr-2">{getRankIcon(rank)}</span>
          {team.realName}
        </p>
        <p className="text-xs text-gray-500">{team.tradeCount} trades</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold text-green-700">
          +{team.totalValueGained.toLocaleString()} pts
        </p>
        <p className="text-xs text-gray-500">
          {team.winRate.toFixed(0)}% win rate
        </p>
      </div>
    </div>
  );
});



export default memo(Overview);