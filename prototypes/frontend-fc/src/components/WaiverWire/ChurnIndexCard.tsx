import React, { useState } from 'react';
import { RefreshCw, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { ChurnMetric } from '../../types/waiver-wire';

interface ChurnIndexCardProps {
  metrics: ChurnMetric[];
  currentTeamId: number;
}

export const ChurnIndexCard: React.FC<ChurnIndexCardProps> = ({
  metrics,
  currentTeamId
}) => {
  // Default to #1 ranked team (highest churn rate)
  const topTeam = [...metrics].sort((a, b) => b.overall_churn_rate - a.overall_churn_rate)[0];
  const [showInfo, setShowInfo] = useState(false);
  const [showAllTeams, setShowAllTeams] = useState(false);
  const [selectedTeamId, setSelectedTeamId] = useState(topTeam?.roster_id || currentTeamId);
  
  const selectedMetric = metrics.find(m => m.roster_id === selectedTeamId);
  const userMetric = metrics.find(m => m.roster_id === currentTeamId);
  const displayMetric = selectedMetric || userMetric;
  
  return (
    <div className="card">
      <div className="flex items-center mb-4">
        <RefreshCw className="h-5 w-5 text-orange-600 mr-2" />
        <h3 className="text-lg font-semibold">Roster Churn Index</h3>
        
        {/* Info Icon with Tooltip/Description */}
        <div className="relative ml-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
            className="text-gray-400 hover:text-gray-600 focus:outline-none"
            aria-label="Information about Roster Churn Index"
          >
            <Info className="h-4 w-4" />
          </button>
          
          {showInfo && (
            <div className="absolute z-10 w-72 sm:w-80 p-3 bg-gray-900 text-white text-xs sm:text-sm rounded-lg shadow-lg top-6 left-0 sm:left-auto sm:right-0">
              <div className="relative">
                <p className="leading-relaxed">
                  Roster Churn Index measures how actively you manage your roster.
                  It's calculated as (Total Adds + Total Drops) / (Weeks × Roster Spots) × 100%.
                  Higher rates indicate more aggressive streaming and speculation, while lower
                  rates suggest a stable core roster.
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
          <div className="text-center mb-4">
            <div className="text-4xl font-bold text-orange-600">
              {displayMetric.overall_churn_rate}%
            </div>
            <div className="text-sm text-gray-600">Weekly Churn Rate</div>
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm mb-6">
            <div className="text-center">
              <div className="text-gray-600">Total Adds</div>
              <div className="font-semibold text-lg">{displayMetric.total_adds}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-600">Total Drops</div>
              <div className="font-semibold text-lg">{displayMetric.total_drops}</div>
            </div>
          </div>
          
          {/* League Comparison */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-3">League Rankings</h4>
            <div className="space-y-2">
              {metrics
                .sort((a, b) => b.overall_churn_rate - a.overall_churn_rate)
                .slice(0, showAllTeams ? undefined : 5)
                .map((m, idx) => (
                  <div
                    key={m.roster_id}
                    onClick={() => setSelectedTeamId(m.roster_id)}
                    className={`flex justify-between items-center text-sm py-1.5 px-2 rounded cursor-pointer transition-all ${
                      m.roster_id === selectedTeamId ? 'bg-orange-100 ring-2 ring-orange-400 font-medium' :
                      'hover:bg-gray-100'
                    }`}
                  >
                    <span className="text-gray-600 truncate flex-1">
                      {idx + 1}. {m.team_name}
                    </span>
                    <span className="font-medium text-gray-900 ml-2">{m.overall_churn_rate}%</span>
                  </div>
                ))}
            </div>
            
            {/* More Details Toggle Button */}
            {metrics.length > 5 && (
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
          No churn data available
        </div>
      )}
    </div>
  );
};