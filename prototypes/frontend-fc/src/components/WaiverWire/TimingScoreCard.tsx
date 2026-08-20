import React, { useState } from 'react';
import { Clock, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { TimingData } from '../../types/waiver-wire';

interface TimingScoreCardProps {
  data: TimingData;
  currentTeamId: number;
}

export const TimingScoreCard: React.FC<TimingScoreCardProps> = ({
  data,
  currentTeamId
}) => {
  // Default to team with highest timing score (most proactive)
  const topTeam = [...data.manager_metrics].sort((a, b) => b.timing_score - a.timing_score)[0];
  const [showInfo, setShowInfo] = useState(false);
  const [showAllTeams, setShowAllTeams] = useState(false);
  const [selectedTeamId, setSelectedTeamId] = useState(topTeam?.roster_id || currentTeamId);
  
  const selectedMetric = data.manager_metrics.find(m => m.roster_id === selectedTeamId);
  const userMetric = data.manager_metrics.find(m => m.roster_id === currentTeamId);
  const displayMetric = selectedMetric || userMetric;
  
  if (!displayMetric) {
    return (
      <div className="card">
        <div className="flex items-center mb-4">
          <Clock className="h-5 w-5 text-purple-600 mr-2" />
          <h3 className="text-lg font-semibold">Waiver Timing Score</h3>
        </div>
        <div className="text-center py-8 text-gray-500">
          No timing data available
        </div>
      </div>
    );
  }
  
  // Get strategy badge styling
  const getStrategyBadge = (strategy: string) => {
    const badges = {
      'proactive': { bg: 'bg-green-100', text: 'text-green-800', label: 'Proactive' },
      'balanced': { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Balanced' },
      'reactive': { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Reactive' }
    };
    return badges[strategy as keyof typeof badges] || badges.balanced;
  };
  
  const strategyBadge = getStrategyBadge(displayMetric.strategy_type);
  
  // Determine if score is positive or negative
  const isPositive = displayMetric.timing_score > 0;
  const isNeutral = Math.abs(displayMetric.timing_score) <= 5;
  
  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center mb-4">
        <Clock className="h-5 w-5 text-purple-600 mr-2" />
        <h3 className="text-lg font-semibold">Waiver Timing Score</h3>
        
        {/* Info Icon with Tooltip */}
        <div className="relative ml-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
            className="text-gray-400 hover:text-gray-600 focus:outline-none"
            aria-label="Information about Waiver Timing Score"
          >
            <Info className="h-4 w-4" />
          </button>
          
          {showInfo && (
            <div className="absolute z-10 w-72 sm:w-80 p-3 bg-gray-900 text-white text-xs sm:text-sm rounded-lg shadow-lg top-6 left-0 sm:left-auto sm:right-0">
              <div className="relative">
                <p className="leading-relaxed mb-2">
                  Waiver Timing Score measures the effectiveness of your waiver timing:
                </p>
                <ul className="space-y-1 text-xs">
                  <li><span className="font-semibold text-purple-400">Early Week:</span> Tuesday-Thursday pickups</li>
                  <li><span className="font-semibold text-purple-400">Late Week:</span> Friday-Monday pickups</li>
                  <li><span className="font-semibold text-green-400">Proactive:</span> Score &gt; +5 (early week advantage)</li>
                  <li><span className="font-semibold text-orange-400">Reactive:</span> Score &lt; -5 (late week advantage)</li>
                  <li><span className="font-semibold text-blue-400">Balanced:</span> Score between -5 and +5</li>
                </ul>
                <p className="mt-2 text-xs text-gray-300">
                  Score = Early Week Avg - Late Week Avg (points per hit)
                </p>
                {/* Arrow pointer for desktop */}
                <div className="hidden sm:block absolute -top-2 right-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
                {/* Arrow pointer for mobile */}
                <div className="sm:hidden absolute -top-2 left-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Team Selector Dropdown */}
      <div className="mb-4">
        <select
          value={selectedTeamId}
          onChange={(e) => setSelectedTeamId(Number(e.target.value))}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 text-sm"
        >
          {data.manager_metrics
            .sort((a, b) => b.timing_score - a.timing_score)
            .map((m) => (
              <option key={m.roster_id} value={m.roster_id}>
                {m.team_name} ({m.timing_score > 0 ? '+' : ''}{m.timing_score})
              </option>
            ))}
        </select>
      </div>
      
      {/* Main Score Display */}
      <div className="text-center mb-4">
        <div className={`text-5xl font-bold ${
          isNeutral ? 'text-blue-600' :
          isPositive ? 'text-green-600' : 'text-orange-600'
        }`}>
          {displayMetric.timing_score > 0 ? '+' : ''}{displayMetric.timing_score}
        </div>
        <div className="text-sm text-gray-600">Timing Differential</div>
      </div>
      
      {/* Strategy Badge */}
      <div className="flex justify-center mb-6">
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${strategyBadge.bg} ${strategyBadge.text}`}>
          {strategyBadge.label} Strategy
        </span>
      </div>
      
      {/* Side-by-Side Comparison */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Early Week */}
        <div className="bg-purple-50 rounded-lg p-4">
          <div className="text-center">
            <div className="text-xs text-gray-600 mb-1">Early Week</div>
            <div className="text-xs text-gray-500 mb-2">(Tue-Thu)</div>
            <div className="text-2xl font-bold text-purple-600 mb-1">
              {displayMetric.early_avg_points}
            </div>
            <div className="text-xs text-gray-600 mb-2">avg pts/hit</div>
            <div className="text-sm font-medium text-gray-700">
              {displayMetric.early_week_hits} hits
            </div>
          </div>
        </div>
        
        {/* Late Week */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-center">
            <div className="text-xs text-gray-600 mb-1">Late Week</div>
            <div className="text-xs text-gray-500 mb-2">(Fri-Mon)</div>
            <div className="text-2xl font-bold text-gray-600 mb-1">
              {displayMetric.late_avg_points}
            </div>
            <div className="text-xs text-gray-600 mb-2">avg pts/hit</div>
            <div className="text-sm font-medium text-gray-700">
              {displayMetric.late_week_hits} hits
            </div>
          </div>
        </div>
      </div>
      
      {/* Notable Hits */}
      {(displayMetric.notable_early_hits.length > 0 || displayMetric.notable_late_hits.length > 0) && (
        <div className="mb-6 space-y-4">
          {/* Early Week Notable Hits */}
          {displayMetric.notable_early_hits.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Top Early Week Hits</h4>
              <div className="space-y-2">
                {displayMetric.notable_early_hits.map((hit, idx) => (
                  <div
                    key={`early-${idx}`}
                    className="flex justify-between items-center text-sm bg-purple-50 px-3 py-2 rounded"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900 truncate">
                        {hit.player_name}
                      </div>
                      <div className="text-xs text-gray-600">
                        Tier {hit.tier} • {hit.points} pts post-acquisition
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Late Week Notable Hits */}
          {displayMetric.notable_late_hits.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Top Late Week Hits</h4>
              <div className="space-y-2">
                {displayMetric.notable_late_hits.map((hit, idx) => (
                  <div
                    key={`late-${idx}`}
                    className="flex justify-between items-center text-sm bg-gray-50 px-3 py-2 rounded"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900 truncate">
                        {hit.player_name}
                      </div>
                      <div className="text-xs text-gray-600">
                        Tier {hit.tier} • {hit.points} pts post-acquisition
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* League Rankings */}
      <div className="pt-6 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">League Rankings</h4>
        <div className="space-y-2">
          {data.manager_metrics
            .sort((a, b) => b.timing_score - a.timing_score)
            .slice(0, showAllTeams ? undefined : 5)
            .map((m, idx) => (
              <div
                key={m.roster_id}
                onClick={() => setSelectedTeamId(m.roster_id)}
                className={`flex justify-between items-center text-sm py-1.5 px-2 rounded cursor-pointer transition-all ${
                  m.roster_id === selectedTeamId ? 'bg-purple-100 ring-2 ring-purple-400 font-medium' :
                  'hover:bg-gray-100'
                }`}
              >
                <span className="text-gray-600 truncate flex-1">
                  {idx + 1}. {m.team_name}
                </span>
                <span className={`font-medium ml-2 ${
                  m.timing_score > 5 ? 'text-green-600' :
                  m.timing_score < -5 ? 'text-orange-600' :
                  'text-blue-600'
                }`}>
                  {m.timing_score > 0 ? '+' : ''}{m.timing_score}
                </span>
              </div>
            ))}
        </div>
        
        {/* More Details Toggle Button */}
        {data.manager_metrics.length > 5 && (
          <button
            onClick={() => setShowAllTeams(!showAllTeams)}
            className="mt-3 w-full flex items-center justify-center gap-1 text-sm text-primary-600 hover:text-primary-700 font-medium focus:outline-none"
          >
            {showAllTeams ? (
              <>
                <span>Show Less</span>
                <ChevronUp className="h-4 w-4" />
              </>
            ) : (
              <>
                <span>More Details</span>
                <ChevronDown className="h-4 w-4" />
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};