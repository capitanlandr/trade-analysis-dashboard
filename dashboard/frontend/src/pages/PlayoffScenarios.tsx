import React, { useState, useEffect } from 'react';
import { PlayoffScenariosData, PlayoffScenario } from '../types/playoff-scenarios';

const PlayoffScenarios: React.FC = () => {
  const [data, setData] = useState<PlayoffScenariosData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api-playoff-scenarios.json')
      .then(res => res.json())
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-8">Loading playoff scenarios...</div>;
  if (error) return <div className="p-8 text-red-600">Error: {error}</div>;
  if (!data) return <div className="p-8">No data available</div>;

  const getStatusBadge = (scenario: PlayoffScenario) => {
    if (scenario.clinched_playoff) {
      return <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-semibold">CLINCHED</span>;
    }
    if (scenario.eliminated) {
      return <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs font-semibold">ELIMINATED</span>;
    }
    return null;
  };

  const getProbabilityColor = (prob: number): string => {
    if (prob >= 95) return 'text-green-600 font-bold';
    if (prob >= 75) return 'text-green-500';
    if (prob >= 50) return 'text-yellow-600';
    if (prob >= 25) return 'text-orange-500';
    if (prob > 0) return 'text-red-500';
    return 'text-gray-400';
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Playoff Scenarios</h1>
        <p className="text-gray-600">
          Based on {data.num_simulations.toLocaleString()} simulated outcomes of remaining games
        </p>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Seed
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Team
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Division
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Record
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Playoff %
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Division %
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Bye Week %
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.results.map((scenario, idx) => (
                <tr key={scenario.team_name} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {scenario.most_likely_seed || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {scenario.team_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {scenario.division}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-900">
                    {scenario.current_record}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm text-center ${getProbabilityColor(scenario.playoff_probability)}`}>
                    {scenario.playoff_probability.toFixed(1)}%
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm text-center ${getProbabilityColor(scenario.division_winner_probability)}`}>
                    {scenario.division_winner_probability.toFixed(1)}%
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm text-center ${getProbabilityColor(scenario.bye_week_probability)}`}>
                    {scenario.bye_week_probability.toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                    {getStatusBadge(scenario)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">How to Read This</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li><strong>Playoff %:</strong> Chance of making top 6 (3 division winners + 3 wildcards)</li>
          <li><strong>Division %:</strong> Chance of winning your division (automatic playoff berth)</li>
          <li><strong>Bye Week %:</strong> Chance of getting top 2 seed (skip wild card round)</li>
          <li><strong>Projected Seed:</strong> Most likely playoff seed based on current standings</li>
        </ul>
      </div>
    </div>
  );
};

export default PlayoffScenarios;
