import { useMemo } from 'react';
import { DollarSign, AlertCircle, Flame, Trophy, Percent, Users } from 'lucide-react';
import { useWaiverWireData } from '../services/api';

const BID_BUCKET_ORDER = ['0', '1-5', '6-10', '11-20', '21-50', '51+'];
const BID_BUCKET_LABEL: Record<string, string> = {
  '0': '$0 (free)',
  '1-5': '$1-5',
  '6-10': '$6-10',
  '11-20': '$11-20',
  '21-50': '$21-50',
  '51+': '$51+',
};

export default function FaabMarket() {
  const { data, isLoading, error } = useWaiverWireData();

  const bidStats = useMemo(() => {
    const dist = data?.bidding_patterns?.distribution;
    if (!dist) return null;
    const total = Object.values(dist).reduce((sum, n) => sum + n, 0);
    const max = Math.max(...Object.values(dist), 1);
    return { dist, total, max };
  }, [data]);

  const topContested = useMemo(() => {
    if (!data?.contested_players) return [];
    return [...data.contested_players]
      .sort((a, b) => b.total_claims - a.total_claims)
      .slice(0, 10);
  }, [data]);

  const Header = () => (
    <div className="text-center">
      <div className="flex items-center justify-center mb-4">
        <DollarSign className="h-8 w-8 text-primary-600 mr-3" />
        <h1 className="text-3xl font-bold text-gray-900">FAAB Market</h1>
      </div>
      <p className="text-lg text-gray-600 max-w-3xl mx-auto">
        How the league spends its waiver budget: bid distribution, the players everyone
        fights over, and who opens their wallet.
      </p>
    </div>
  );

  if (isLoading) {
    return (
      <div className="space-y-8">
        <Header />
        <div className="card p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading FAAB market data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <Header />
        <div className="card p-8 text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Data</h3>
          <p className="text-gray-600">{error.message}</p>
        </div>
      </div>
    );
  }

  const zeroBidRate = data?.bidding_patterns?.zero_bid_success_rate;
  const avgBid = data?.metadata?.average_waiver_bid;
  const totalBids = data?.metadata?.total_waiver_bids;

  return (
    <div className="space-y-8">
      <Header />

      {/* Key FAAB metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 rounded-lg text-green-600 bg-green-100">
              <DollarSign className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Average Bid</p>
              <p className="text-2xl font-bold text-gray-900">
                ${avgBid != null ? avgBid.toFixed(1) : '-'}
              </p>
              <p className="text-xs text-gray-500">Across all waiver claims</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 rounded-lg text-blue-600 bg-blue-100">
              <Percent className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">$0 Claim Success</p>
              <p className="text-2xl font-bold text-gray-900">
                {zeroBidRate != null ? `${zeroBidRate}%` : '-'}
              </p>
              <p className="text-xs text-gray-500">Free claims that went through</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 rounded-lg text-purple-600 bg-purple-100">
              <Trophy className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total FAAB Bid</p>
              <p className="text-2xl font-bold text-gray-900">
                ${totalBids != null ? totalBids.toLocaleString() : '-'}
              </p>
              <p className="text-xs text-gray-500">Dollars committed to claims</p>
            </div>
          </div>
        </div>
      </div>

      {/* Bid distribution + biggest spends */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bid Size Distribution */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <DollarSign className="h-5 w-5 mr-2 text-green-600" />
            Bid Size Distribution
          </h2>
          {bidStats ? (
            <div className="space-y-3">
              {BID_BUCKET_ORDER.filter((b) => bidStats.dist[b] != null).map((bucket) => {
                const count = bidStats.dist[bucket];
                const pct = bidStats.total > 0 ? (count / bidStats.total) * 100 : 0;
                return (
                  <div key={bucket}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-700 font-medium">
                        {BID_BUCKET_LABEL[bucket] ?? bucket}
                      </span>
                      <span className="text-gray-500">
                        {count} ({pct.toFixed(0)}%)
                      </span>
                    </div>
                    <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 transition-all duration-300"
                        style={{ width: `${(count / bidStats.max) * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No bid distribution available</p>
          )}
        </div>

        {/* Biggest FAAB Spends */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Flame className="h-5 w-5 mr-2 text-orange-600" />
            Biggest FAAB Spends
          </h2>
          {data?.bidding_patterns?.highest_bids?.length ? (
            <div className="space-y-2">
              {data.bidding_patterns.highest_bids.slice(0, 8).map((bid, idx) => (
                <div
                  key={`${bid.player_id}-${idx}`}
                  className="flex justify-between items-center text-sm py-2 px-3 rounded bg-gray-50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 truncate">
                      {bid.player_name}
                    </div>
                    <div className="text-xs text-gray-500 truncate">{bid.team_name}</div>
                  </div>
                  <div className="flex items-center gap-2 ml-2 flex-shrink-0">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        bid.status === 'complete'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {bid.status === 'complete' ? 'Won' : 'Lost'}
                    </span>
                    <span className="font-bold text-orange-600 text-base w-12 text-right">
                      ${bid.waiver_bid}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No bid data available</p>
          )}
        </div>
      </div>

      {/* Most contested players */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <Users className="h-5 w-5 mr-2 text-primary-600" />
          Most Contested Players
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Players the league fought over most — total claims across all managers.
        </p>
        {topContested.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Player
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Claims
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Successful
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Top Bid
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {topContested.map((p, idx) => (
                  <tr key={p.player_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                      <span className="text-gray-400 mr-2">{idx + 1}.</span>
                      {p.player_name}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                        {p.total_claims}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {p.successful_claims} / {p.total_claims}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {p.highest_bid > 0 ? `$${p.highest_bid}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No contested player data available</p>
        )}
      </div>
    </div>
  );
}
