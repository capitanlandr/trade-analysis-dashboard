import React, { useState } from 'react';
import { DollarSign, Info, ChevronDown, ChevronUp, User } from 'lucide-react';
import { EfficiencyData } from '../../types/waiver-wire';

interface EfficiencyScoreCardProps {
  data: EfficiencyData;
  currentTeamId: number;
}

// Helper function to get score badge styling
const getScoreBadge = (zScore: number): { text: string; emoji: string; color: string } => {
  if (zScore >= 2.0) return { text: `+${zScore.toFixed(1)}σ`, emoji: '⭐', color: 'text-green-600' };
  if (zScore >= 1.0) return { text: `+${zScore.toFixed(1)}σ`, emoji: '✓', color: 'text-blue-600' };
  if (zScore >= 0) return { text: `+${zScore.toFixed(1)}σ`, emoji: '', color: 'text-gray-900' };
  if (zScore >= -1.0) return { text: `${zScore.toFixed(1)}σ`, emoji: '', color: 'text-gray-600' };
  return { text: `${zScore.toFixed(1)}σ`, emoji: '✗', color: 'text-red-600' };
};

// Helper function to get percentile label
const getPercentileLabel = (percentile: number): string => {
  if (percentile >= 95) return 'Elite (Top 5%)';
  if (percentile >= 75) return 'Above Average (Top 25%)';
  if (percentile >= 50) return 'Above Average';
  if (percentile >= 25) return 'Below Average';
  return 'Needs Improvement';
};

export const EfficiencyScoreCard: React.FC<EfficiencyScoreCardProps> = ({
  data,
  currentTeamId
}) => {
  // Default to #1 ranked team (highest WWES)
  const topTeam = [...data.manager_metrics].sort((a, b) => b.raw_wwes - a.raw_wwes)[0];
  const [showInfo, setShowInfo] = useState(false);
  const [showAllTeams, setShowAllTeams] = useState(false);
  const [selectedTeamId, setSelectedTeamId] = useState(topTeam?.roster_id || currentTeamId);
  
  const userMetric = data.manager_metrics.find(m => m.roster_id === currentTeamId);
  const selectedMetric = data.manager_metrics.find(m => m.roster_id === selectedTeamId);
  const displayMetric = selectedMetric || userMetric;
  const scoreBadge = displayMetric ? getScoreBadge(displayMetric.normalized_wwes) : null;
  const isViewingOwnTeam = selectedTeamId === currentTeamId;
  
  return (
    <div className="card">
      <div className="flex items-center mb-4">
        <DollarSign className="h-5 w-5 text-blue-600 mr-2" />
        <h3 className="text-lg font-semibold">Waiver Wire Efficiency</h3>
        
        {/* Info Icon with Tooltip */}
        <div className="relative ml-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
            className="text-gray-400 hover:text-gray-600 focus:outline-none"
            aria-label="Information about Waiver Wire Efficiency Score"
          >
            <Info className="h-4 w-4" />
          </button>
          
          {showInfo && (
            <div className="absolute z-10 w-72 sm:w-80 p-3 bg-gray-900 text-white text-xs sm:text-sm rounded-lg shadow-lg top-6 left-0 sm:left-auto sm:right-0">
              <div className="relative">
                <p className="leading-relaxed">
                  Waiver Wire Efficiency Score (WWES) measures the fantasy points gained per dollar spent.
                  It's calculated as Total Points Scored After Acquisition / (FAAB Spent + Free Agent Adds).
                  Higher scores indicate better value from waiver pickups. Z-scores show performance relative to league average.
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
      
      {displayMetric ? (
        <>
          {/* Main Score Display */}
          <div className="text-center mb-4">
            <div className={`text-5xl font-bold ${scoreBadge?.color || 'text-gray-900'}`}>
              {scoreBadge?.emoji && <span className="mr-2">{scoreBadge.emoji}</span>}
              {scoreBadge?.text || '0.0σ'}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              {getPercentileLabel(displayMetric.league_percentile)}
            </div>
          </div>
          
          {/* Score Breakdown */}
          <div className="bg-blue-50 rounded-lg p-4 mb-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="text-center">
                <div className="text-gray-600">Score</div>
                <div className="font-bold text-lg text-blue-600">{displayMetric.raw_wwes}</div>
                <div className="text-xs text-gray-500">pts/dollar</div>
              </div>
              <div className="text-center">
                <div className="text-gray-600">League Avg</div>
                <div className="font-bold text-lg text-gray-700">{data.league_stats.mean_wwes}</div>
                <div className="text-xs text-gray-500">pts/dollar</div>
              </div>
            </div>
          </div>
          
          {/* Contributing Factors */}
          <div className="space-y-2 text-sm mb-6">
            <div className="flex justify-between items-center py-1">
              <span className="text-gray-600">Points from Adds:</span>
              <span className="font-medium text-gray-900">{displayMetric.total_points_from_adds.toFixed(1)} pts</span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-gray-600">FAAB Spent:</span>
              <span className="font-medium text-gray-900">${displayMetric.faab_spent}</span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-gray-600">Free Agent Adds:</span>
              <span className="font-medium text-gray-900">{displayMetric.free_agent_count}</span>
            </div>
          </div>
          
          {/* League Rankings */}
          <div className="pt-6 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-3">League Rankings</h4>
            <div className="space-y-2">
              {data.manager_metrics
                .sort((a, b) => b.raw_wwes - a.raw_wwes)
                .slice(0, showAllTeams ? undefined : 5)
                .map((m, idx) => (
                  <div
                    key={m.roster_id}
                    onClick={() => setSelectedTeamId(m.roster_id)}
                    className={`flex justify-between items-center text-sm py-1.5 px-2 rounded cursor-pointer transition-all ${
                      m.roster_id === selectedTeamId ? 'bg-blue-100 ring-2 ring-blue-400 font-medium' :
                      'hover:bg-gray-100'
                    }`}
                  >
                    <span className="text-gray-600 truncate flex-1">
                      {idx + 1}. {m.team_name}
                    </span>
                    <span className="font-medium text-gray-900 ml-2">{m.raw_wwes}</span>
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
        </>
      ) : (
        <div className="text-center py-8 text-gray-500">
          No efficiency data available
        </div>
      )}
    </div>
  );
};