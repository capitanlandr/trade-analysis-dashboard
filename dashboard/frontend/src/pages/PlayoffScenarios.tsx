import React, { useMemo } from 'react';
import { PlayoffScenario } from '../types/playoff-scenarios';
import { usePlayoffScenariosData } from '../services/api';

const PlayoffScenarios: React.FC = () => {
  const { data: rawData, isLoading, error } = usePlayoffScenariosData();

  // Sort results by current seed (nulls at the end) -- derived from query data
  const data = useMemo(() => {
    if (!rawData) return null;
    const sortedResults = [...rawData.results].sort((a, b) => {
      if (a.current_seed === null && b.current_seed === null) return 0;
      if (a.current_seed === null) return 1;
      if (b.current_seed === null) return -1;
      return a.current_seed - b.current_seed;
    });
    return { ...rawData, results: sortedResults };
  }, [rawData]);

  if (isLoading) return <div className="p-8">Loading playoff scenarios...</div>;
  if (error) return <div className="p-8 text-red-600">Error: {error instanceof Error ? error.message : 'Unknown error'}</div>;
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
                  Projected Seed
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Current Seed
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
                    {scenario.current_seed || 'N/A'}
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

      <div className="mt-6 space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">How to Read This</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li><strong>Projected Seed:</strong> Most likely playoff seed based on {data.num_simulations.toLocaleString()} simulations of remaining games</li>
            <li><strong>Current Seed:</strong> Playoff seed if the season ended today (based on current standings)</li>
            <li><strong>Playoff %:</strong> Probability of making top 6 (3 division winners + 3 wildcards)</li>
            <li><strong>Division %:</strong> Probability of winning your division (automatic playoff berth)</li>
            <li><strong>Bye Week %:</strong> Probability of getting top 2 seed (skip wild card round)</li>
          </ul>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Simulation Methodology</h3>
          <div className="text-sm text-gray-700 space-y-2">
            <p>
              These probabilities are calculated by running {data.num_simulations.toLocaleString()} Monte Carlo simulations
              of all remaining regular season games. Each simulation:
            </p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Randomly determines the outcome of each remaining matchup (win/loss for each team)</li>
              <li>Calculates final standings using official playoff tiebreaker rules:
                <ul className="list-disc list-inside ml-6 mt-1 space-y-0.5">
                  <li>Overall win/loss record</li>
                  <li>Head-to-head record</li>
                  <li>Division record</li>
                  <li>Total points scored</li>
                  <li>Points against (lower is better)</li>
                </ul>
              </li>
              <li>Determines playoff seeding (3 division winners + 3 wildcards by record)</li>
              <li>Records which teams made playoffs, won divisions, and earned byes</li>
            </ol>
            <p className="mt-2">
              The percentages represent how often each outcome occurred across all simulations.
              For example, a 75% playoff probability means the team made the playoffs in 75% of the simulated scenarios.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlayoffScenarios;
