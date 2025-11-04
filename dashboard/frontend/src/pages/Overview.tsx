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
    queryFn: () => api.getStatsSummary(),
  });

  const { 
    isLoading: tradesLoading
  } = useQuery({
    queryKey: ['trades', 'recent'],
    queryFn: () => api.getTrades({ maxResults: 10 }),
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

  const stats = statsData?.data?.data;

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
          title="Total Value"
          value={`$${((stats?.overview?.totalTradeValue || 0) / 1000).toFixed(1)}K`}
          icon={DollarSign}
          color="green"
        />
        <MetricCard
          title="Active Traders"
          value={stats?.teamRankings?.byTradeCount?.length || 0}
          icon={Users}
          color="yellow"
          subtitle="Managers with trades"
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
              subtitle={`${stats?.overview?.totalTrades || 0} total trades`}
            />
            <LeaderItem
              label="Biggest Winner"
              value={stats?.overview?.biggestWinner || 'N/A'}
              subtitle="Highest total value gained"
            />
            <LeaderItem
              label="Trade Season"
              value={`${stats?.overview?.dateRange?.earliest || ''} to ${stats?.overview?.dateRange?.latest || ''}`}
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