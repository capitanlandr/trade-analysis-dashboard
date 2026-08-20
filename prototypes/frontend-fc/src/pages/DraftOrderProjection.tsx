import React, { useState } from 'react';
import {
  isLockedPick
} from '../types/draft-order';
import { useDraftOrderData } from '../services/api';

const DraftOrderProjection: React.FC = () => {
  const { data, isLoading, error } = useDraftOrderData();
  const [selectedRound, setSelectedRound] = useState(1);

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="space-y-3">
            {[...Array(12)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-900 font-semibold mb-2">Draft Order Not Available</h3>
          <p className="text-red-700 text-sm">{error instanceof Error ? error.message : 'Unknown error'}</p>
          <p className="text-red-600 text-sm mt-2">
            Draft order data will be available once playoff results are processed.
          </p>
        </div>
      </div>
    );
  }

  if (!data) return <div className="p-8">No data available</div>;

  // Get all rounds
  const allRounds = [
    { number: 1, picks: data.draft_order.round_1 || [] },
    { number: 2, picks: data.draft_order.round_2 || [] },
    { number: 3, picks: data.draft_order.round_3 || [] },
    { number: 4, picks: data.draft_order.round_4 || [] },
  ];

  const getNextUpdateMessage = (throughWeek: number): string => {
    if (throughWeek >= 17) {
      return 'All picks finalized';
    } else if (throughWeek >= 16) {
      return 'Next update: After Week 17 Championship & 3rd Place games';
    } else if (throughWeek >= 15) {
      return 'Next update: After Week 16 Semifinals';
    } else {
      return 'Next update: After Week 15 Wild Card round';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">2026 Draft Order Projection</h1>
        <p className="text-gray-600">
          Playoff results through Week {data.through_week} • {getNextUpdateMessage(data.through_week)}
        </p>
      </div>

      {/* Round Selector */}
      <div className="mb-6 flex space-x-2">
        {allRounds.map(round => (
          <button
            key={round.number}
            onClick={() => setSelectedRound(round.number)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              selectedRound === round.number
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
            }`}
          >
            Round {round.number}
          </button>
        ))}
      </div>

      {/* Draft Order Table for Selected Round */}
      <div className="mb-8">
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Draft Position
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Original Owner
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Current Owner
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {allRounds.find(r => r.number === selectedRound)?.picks.map((pick, idx) => (
                  <tr key={pick.pick_label} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-bold text-gray-900">{pick.pick_label}</div>
                    </td>

                    {isLockedPick(pick) ? (
                      <>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900">
                            {pick.original_owner.team_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            {pick.original_owner.description}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900">
                            {pick.current_owner.team_name}
                          </div>
                          {pick.traded && (
                            <span className="text-xs text-orange-600 font-semibold">TRADED</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center">
                            <span className="text-green-600 mr-2">&#10003;</span>
                            <span className="text-sm text-gray-900 font-medium">Locked</span>
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-500 italic">TBD</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-500 italic">TBD</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-start">
                            <span className="text-yellow-600 mr-2 mt-0.5">&#8987;</span>
                            <div className="flex-1">
                              <div className="text-sm text-gray-900 font-medium mb-2">Pending - {pick.pending_game}</div>
                              <div className="space-y-1.5">
                                {pick.scenarios.map((scenario, sIdx) => (
                                  <div key={sIdx} className="text-xs">
                                    <span className="text-gray-700">
                                      <span className="font-semibold">Origin:</span> {scenario.team_name} /
                                      <span className="font-semibold"> Current:</span> {scenario.current_owner_team_name}
                                      {scenario.traded && <span className="ml-1 text-orange-600 font-semibold">(TRADED)</span>}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-3">Legend</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="flex items-center space-x-2">
            <span className="text-green-600 text-lg">&#10003;</span>
            <span className="text-blue-900">Locked - Pick finalized</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-yellow-600 text-lg">&#8987;</span>
            <span className="text-blue-900">Pending - Awaiting result</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-lg">&#127942;</span>
            <span className="text-blue-900">Winner scenario</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-lg">&#128148;</span>
            <span className="text-blue-900">Loser scenario</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DraftOrderProjection;
