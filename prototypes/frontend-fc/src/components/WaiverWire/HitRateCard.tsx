import React, { useState } from 'react';
import { Target, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { HitRateData } from '../../types/waiver-wire';

interface HitRateCardProps {
  data: HitRateData;
  currentTeamId: number;
}

export const HitRateCard: React.FC<HitRateCardProps> = ({
  data,
  currentTeamId
}) => {
  // Default to #1 ranked team (highest hit rate)
  const topTeam = [...data.manager_metrics].sort((a, b) => b.overall_hit_rate - a.overall_hit_rate)[0];
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
          <Target className="h-5 w-5 text-green-600 mr-2" />
          <h3 className="text-lg font-semibold">Waiver Hit Rate</h3>
        </div>
        <div className="text-center py-8 text-gray-500">
          No hit rate data available
        </div>
      </div>
    );
  }
  
  // Calculate tier percentages
  const tier1Pct = (displayMetric.tier1_hits / displayMetric.total_adds) * 100;
  const tier2Pct = (displayMetric.tier2_hits / displayMetric.total_adds) * 100;
  const tier3Pct = (displayMetric.tier3_hits / displayMetric.total_adds) * 100;
  const missPct = (displayMetric.misses / displayMetric.total_adds) * 100;
  
  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center mb-4">
        <Target className="h-5 w-5 text-green-600 mr-2" />
        <h3 className="text-lg font-semibold">Waiver Hit Rate</h3>
        
        {/* Info Icon with Tooltip */}
        <div className="relative ml-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
            className="text-gray-400 hover:text-gray-600 focus:outline-none"
            aria-label="Information about Waiver Hit Rate"
          >
            <Info className="h-4 w-4" />
          </button>
          
          {showInfo && (
            <div className="absolute z-10 w-72 sm:w-80 p-3 bg-gray-900 text-white text-xs sm:text-sm rounded-lg shadow-lg top-6 left-0 sm:left-auto sm:right-0">
              <div className="relative">
                <p className="leading-relaxed mb-2">
                  Waiver Hit Rate measures how often your waiver adds become valuable contributors:
                </p>
                <ul className="space-y-1 text-xs">
                  <li><span className="font-semibold text-green-400">Tier 1:</span> Started ≥50% of weeks after pickup</li>
                  <li><span className="font-semibold text-yellow-400">Tier 2:</span> Started 25-49% of weeks</li>
                  <li><span className="font-semibold text-orange-400">Tier 3:</span> Scored ≥10 pts in any week</li>
                  <li><span className="font-semibold text-gray-400">Miss:</span> None of the above</li>
                </ul>
                {/* Arrow pointer for desktop */}
                <div className="hidden sm:block absolute -top-2 right-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
                {/* Arrow pointer for mobile */}
                <div className="sm:hidden absolute -top-2 left-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Main Hit Rate Display */}
      <div className="text-center mb-4">
        <div className="text-4xl font-bold text-green-600">
          {displayMetric.overall_hit_rate}%
        </div>
        <div className="text-sm text-gray-600">Overall Hit Rate</div>
      </div>
      
      {/* Stacked Progress Bar */}
      <div className="mb-4">
        <div className="w-full h-6 flex rounded-lg overflow-hidden shadow-sm">
          {tier1Pct > 0 && (
            <div
              className="bg-green-500 transition-all duration-300 flex items-center justify-center"
              style={{ width: `${tier1Pct}%` }}
              title={`Tier 1: ${displayMetric.tier1_hits} (${tier1Pct.toFixed(1)}%)`}
            >
              {tier1Pct > 10 && (
                <span className="text-xs font-medium text-white">
                  {displayMetric.tier1_hits}
                </span>
              )}
            </div>
          )}
          {tier2Pct > 0 && (
            <div
              className="bg-yellow-500 transition-all duration-300 flex items-center justify-center"
              style={{ width: `${tier2Pct}%` }}
              title={`Tier 2: ${displayMetric.tier2_hits} (${tier2Pct.toFixed(1)}%)`}
            >
              {tier2Pct > 10 && (
                <span className="text-xs font-medium text-white">
                  {displayMetric.tier2_hits}
                </span>
              )}
            </div>
          )}
          {tier3Pct > 0 && (
            <div
              className="bg-orange-500 transition-all duration-300 flex items-center justify-center"
              style={{ width: `${tier3Pct}%` }}
              title={`Tier 3: ${displayMetric.tier3_hits} (${tier3Pct.toFixed(1)}%)`}
            >
              {tier3Pct > 10 && (
                <span className="text-xs font-medium text-white">
                  {displayMetric.tier3_hits}
                </span>
              )}
            </div>
          )}
          {missPct > 0 && (
            <div
              className="bg-gray-300 transition-all duration-300 flex items-center justify-center"
              style={{ width: `${missPct}%` }}
              title={`Misses: ${displayMetric.misses} (${missPct.toFixed(1)}%)`}
            >
              {missPct > 10 && (
                <span className="text-xs font-medium text-gray-600">
                  {displayMetric.misses}
                </span>
              )}
            </div>
          )}
        </div>
        
        {/* Legend */}
        <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded mr-1.5"></div>
            <span className="text-gray-600">Tier 1: {displayMetric.tier1_hits} ({tier1Pct.toFixed(0)}%)</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-yellow-500 rounded mr-1.5"></div>
            <span className="text-gray-600">Tier 2: {displayMetric.tier2_hits} ({tier2Pct.toFixed(0)}%)</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-orange-500 rounded mr-1.5"></div>
            <span className="text-gray-600">Tier 3: {displayMetric.tier3_hits} ({tier3Pct.toFixed(0)}%)</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-gray-300 rounded mr-1.5"></div>
            <span className="text-gray-600">Miss: {displayMetric.misses} ({missPct.toFixed(0)}%)</span>
          </div>
        </div>
      </div>
      
      {/* Notable Hits */}
      {displayMetric.notable_hits && displayMetric.notable_hits.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Top Tier 1 Hits</h4>
          <div className="space-y-2">
            {displayMetric.notable_hits.map((hit, idx) => (
              <div
                key={`${hit.player_id}-${idx}`}
                className="flex justify-between items-center text-sm bg-green-50 px-3 py-2 rounded"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900 truncate">
                    {hit.player_name}
                  </div>
                  <div className="text-xs text-gray-600">
                    Week {hit.acquisition_week} • Started {hit.weeks_started}/{hit.total_weeks_available} weeks
                  </div>
                </div>
                <div className="ml-2 flex-shrink-0">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                    {hit.weeks_started > 0 ? Math.round((hit.weeks_started / hit.total_weeks_available) * 100) : 0}% usage
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* League Rankings */}
      <div className="pt-6 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">League Rankings</h4>
        <div className="space-y-2">
          {data.manager_metrics
            .sort((a, b) => b.overall_hit_rate - a.overall_hit_rate)
            .slice(0, showAllTeams ? undefined : 5)
            .map((m, idx) => (
              <div
                key={m.roster_id}
                onClick={() => setSelectedTeamId(m.roster_id)}
                className={`flex justify-between items-center text-sm py-1.5 px-2 rounded cursor-pointer transition-all ${
                  m.roster_id === selectedTeamId ? 'bg-green-100 ring-2 ring-green-400 font-medium' :
                  'hover:bg-gray-100'
                }`}
              >
                <span className="text-gray-600 truncate flex-1">
                  {idx + 1}. {m.team_name}
                </span>
                <span className="font-medium text-gray-900 ml-2">{m.overall_hit_rate}%</span>
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