import React from 'react';
import { X, Calendar, Users, TrendingUp, Award } from 'lucide-react';

interface AssetDetail {
  name: string;
  type: string;
  value_then: number;
  value_now: number;
  pick_label?: string;  // Exact pick position for 2026 picks (e.g., "1.12")
}

interface Trade {
  tradeId: string;
  tradeDate: string;
  teamA: string;
  teamB: string;
  teamAReceived: string[];
  teamBReceived: string[];
  teamAAssets?: AssetDetail[];
  teamBAssets?: AssetDetail[];
  teamAValueThen?: number;
  teamAValueNow?: number;
  teamBValueThen?: number;
  teamBValueNow?: number;
  winnerAtTrade?: string;
  winnerCurrent: string;
  marginAtTrade?: number;
  marginCurrent: number;
}

interface TradeDetailModalProps {
  trade: Trade | null;
  isOpen: boolean;
  onClose: () => void;
}

const TradeDetailModal: React.FC<TradeDetailModalProps> = ({ trade, isOpen, onClose }) => {
  if (!isOpen || !trade) return null;

  const formatAssets = (assets: string[]) => {
    if (!assets || assets.length === 0) return ['No assets'];
    return assets;
  };

  const formatDate = (dateString: string) => {
    // Parse as local date to avoid timezone offset issues
    const [year, month, day] = dateString.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  // @ts-ignore - Unused but kept for potential future use
  const parseAssetName = (name: string) => {
    // Check if the asset contains FAAB (e.g., "DJ Giddens | $1 FAAB")
    if (name.includes('|') && name.includes('FAAB')) {
      const parts = name.split('|').map(p => p.trim());
      const playerName = parts[0];
      const faabMatch = parts[1].match(/\$(\d+)\s*FAAB/);
      const faabAmount = faabMatch ? parseInt(faabMatch[1]) : 0;
      
      return [
        { name: playerName, isFAAB: false },
        { name: `$${faabAmount} FAAB`, value: faabAmount, isFAAB: true }
      ];
    }
    
    // Regular asset without FAAB
    return [{ name, isFAAB: false }];
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <Users className="h-6 w-6 text-primary-600" />
            <h2 className="text-xl font-semibold text-gray-900">Trade Details</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Trade Overview */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center space-x-2">
                <Calendar className="h-4 w-4 text-gray-500" />
                <div>
                  <div className="text-sm text-gray-500">Trade Date</div>
                  <div className="font-medium">{formatDate(trade.tradeDate)}</div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <Award className="h-4 w-4 text-gray-500" />
                <div>
                  <div className="text-sm text-gray-500">Winner</div>
                  <div className="flex items-center gap-3">
                    {trade.winnerAtTrade && (
                      <div className="text-sm">
                        <span className="text-gray-500">At trade: </span>
                        <span className="font-medium text-blue-600">{trade.winnerAtTrade}</span>
                      </div>
                    )}
                    <div className="text-sm">
                      <span className="text-gray-500">Current: </span>
                      <span className="font-medium text-green-600">{trade.winnerCurrent}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2 md:col-span-2">
                <TrendingUp className="h-4 w-4 text-gray-500" />
                <div className="flex-1">
                  <div className="text-sm text-gray-500 mb-1">Margin</div>
                  <div className="flex items-center gap-4">
                    {trade.marginAtTrade !== undefined && (
                      <div className="flex-1">
                        <div className="text-xs text-gray-500">At Trade</div>
                        <div className="font-medium text-blue-600">{Math.round(trade.marginAtTrade)} pts</div>
                      </div>
                    )}
                    <div className="flex-1">
                      <div className="text-xs text-gray-500">Current</div>
                      <div className="font-medium text-green-600">{Math.round(trade.marginCurrent)} pts</div>
                    </div>
                    {trade.marginAtTrade !== undefined && (
                      <div className="flex-1">
                        <div className="text-xs text-gray-500">Change</div>
                        <div className={`font-medium ${(trade.marginCurrent - trade.marginAtTrade) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {(trade.marginCurrent - trade.marginAtTrade) > 0 ? '+' : ''}{Math.round(trade.marginCurrent - trade.marginAtTrade)} pts
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Teams and Assets */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Team A */}
            <div className="border border-blue-200 rounded-lg p-4 bg-blue-50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-blue-800">{trade.teamA}</h3>
                <div className="text-sm text-blue-600 font-medium">Received</div>
              </div>
              
              <div className="space-y-2">
                {trade.teamAAssets && trade.teamAAssets.length > 0 ? (
                  <ul className="space-y-2">
                    {trade.teamAAssets.map((asset, assetIndex) => (
                      <li key={assetIndex} className="bg-white p-3 rounded border-l-4 border-blue-400">
                        <div className="flex justify-between items-start mb-1">
                          <div className="flex flex-col">
                            <span className="font-medium text-gray-900">{asset.name}</span>
                            {asset.pick_label && (
                              <span className="text-xs text-blue-600 font-medium mt-0.5">
                                Pick {asset.pick_label}
                              </span>
                            )}
                          </div>
                          <span className="text-sm text-gray-600 font-semibold ml-2">
                            {Math.round(asset.value_now)}
                          </span>
                        </div>
                        <div className="flex gap-4 text-xs text-gray-500">
                          <span>At trade: {Math.round(asset.value_then)}</span>
                          <span className={asset.value_now - asset.value_then > 0 ? 'text-green-600' : asset.value_now - asset.value_then < 0 ? 'text-red-600' : ''}>
                            {asset.value_now - asset.value_then > 0 ? '+' : ''}{Math.round(asset.value_now - asset.value_then)}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  formatAssets(trade.teamAReceived).map((asset, index) => (
                    <div key={index} className="bg-white p-3 rounded border-l-4 border-blue-400">
                      <div className="font-medium text-gray-900">{asset}</div>
                    </div>
                  ))
                )}
              </div>
              
              <div className="mt-4 pt-3 border-t border-blue-200">
                <div className="flex justify-between items-center text-sm mb-1">
                  <span className="text-blue-600">
                    Total: {trade.teamAAssets?.length || formatAssets(trade.teamAReceived).length} asset{(trade.teamAAssets?.length || formatAssets(trade.teamAReceived).length) !== 1 ? 's' : ''}
                  </span>
                  <span className="text-blue-600 font-bold">
                    {Math.round(trade.teamAValueNow || 0)}
                  </span>
                </div>
                {trade.teamAValueThen !== undefined && (
                  <div className="flex justify-between items-center text-xs text-gray-500">
                    <span>At trade value:</span>
                    <div className="flex items-center gap-2">
                      <span>{Math.round(trade.teamAValueThen)}</span>
                      <span className={`font-semibold ${(trade.teamAValueNow || 0) - trade.teamAValueThen > 0 ? 'text-green-600' : (trade.teamAValueNow || 0) - trade.teamAValueThen < 0 ? 'text-red-600' : ''}`}>
                        ({(trade.teamAValueNow || 0) - trade.teamAValueThen > 0 ? '+' : ''}{Math.round((trade.teamAValueNow || 0) - trade.teamAValueThen)})
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Team B */}
            <div className="border border-green-200 rounded-lg p-4 bg-green-50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-green-800">{trade.teamB}</h3>
                <div className="text-sm text-green-600 font-medium">Received</div>
              </div>
              
              <div className="space-y-2">
                {trade.teamBAssets && trade.teamBAssets.length > 0 ? (
                  <ul className="space-y-2">
                    {trade.teamBAssets.map((asset, assetIndex) => (
                      <li key={assetIndex} className="bg-white p-3 rounded border-l-4 border-green-400">
                        <div className="flex justify-between items-start mb-1">
                          <div className="flex flex-col">
                            <span className="font-medium text-gray-900">{asset.name}</span>
                            {asset.pick_label && (
                              <span className="text-xs text-green-600 font-medium mt-0.5">
                                Pick {asset.pick_label}
                              </span>
                            )}
                          </div>
                          <span className="text-sm text-gray-600 font-semibold ml-2">
                            {Math.round(asset.value_now)}
                          </span>
                        </div>
                        <div className="flex gap-4 text-xs text-gray-500">
                          <span>At trade: {Math.round(asset.value_then)}</span>
                          <span className={asset.value_now - asset.value_then > 0 ? 'text-green-600' : asset.value_now - asset.value_then < 0 ? 'text-red-600' : ''}>
                            {asset.value_now - asset.value_then > 0 ? '+' : ''}{Math.round(asset.value_now - asset.value_then)}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  formatAssets(trade.teamBReceived).map((asset, index) => (
                    <div key={index} className="bg-white p-3 rounded border-l-4 border-green-400">
                      <div className="font-medium text-gray-900">{asset}</div>
                    </div>
                  ))
                )}
              </div>
              
              <div className="mt-4 pt-3 border-t border-green-200">
                <div className="flex justify-between items-center text-sm mb-1">
                  <span className="text-green-600">
                    Total: {trade.teamBAssets?.length || formatAssets(trade.teamBReceived).length} asset{(trade.teamBAssets?.length || formatAssets(trade.teamBReceived).length) !== 1 ? 's' : ''}
                  </span>
                  <span className="text-green-600 font-bold">
                    {Math.round(trade.teamBValueNow || 0)}
                  </span>
                </div>
                {trade.teamBValueThen !== undefined && (
                  <div className="flex justify-between items-center text-xs text-gray-500">
                    <span>At trade value:</span>
                    <div className="flex items-center gap-2">
                      <span>{Math.round(trade.teamBValueThen)}</span>
                      <span className={`font-semibold ${(trade.teamBValueNow || 0) - trade.teamBValueThen > 0 ? 'text-green-600' : (trade.teamBValueNow || 0) - trade.teamBValueThen < 0 ? 'text-red-600' : ''}`}>
                        ({(trade.teamBValueNow || 0) - trade.teamBValueThen > 0 ? '+' : ''}{Math.round((trade.teamBValueNow || 0) - trade.teamBValueThen)})
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Trade Summary */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-2">Trade Summary</h4>
            <p className="text-gray-700">
              On {formatDate(trade.tradeDate)}, <span className="font-medium text-blue-600">{trade.teamA}</span> and{' '}
              <span className="font-medium text-green-600">{trade.teamB}</span> completed a trade involving{' '}
              {formatAssets(trade.teamAReceived).length + formatAssets(trade.teamBReceived).length} total assets.
              {trade.winnerCurrent && (
                <>
                  {' '}Currently, <span className="font-medium text-green-600">{trade.winnerCurrent}</span> is winning this trade by{' '}
                  <span className="font-medium">{Math.round(trade.marginCurrent)} points</span>.
                </>
              )}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default TradeDetailModal;