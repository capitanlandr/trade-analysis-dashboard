import React, { useState } from 'react';
import { TrendingUp, Info, ChevronDown, ChevronUp } from 'lucide-react';
import type { DynastyValueMetric } from '../../types/waiver-wire';

interface DynastyValueAddedCardProps {
  metrics: DynastyValueMetric[];
  currentTeamId: number;
}

export const DynastyValueAddedCard: React.FC<DynastyValueAddedCardProps> = ({
  metrics,
  currentTeamId,
}) => {
  const topTeam = [...metrics].sort((a, b) => b.net_value - a.net_value)[0];
  const [showInfo, setShowInfo] = useState(false);
  const [showAllTeams, setShowAllTeams] = useState(false);
  const [selectedTeamId, setSelectedTeamId] = useState(topTeam?.roster_id ?? currentTeamId);

  const selectedMetric = metrics.find((m) => m.roster_id === selectedTeamId);
  const userMetric = metrics.find((m) => m.roster_id === currentTeamId);
  const displayMetric = selectedMetric || userMetric;

  return (
    <div className="card relative">
      <div className="flex items-center mb-4">
        <TrendingUp className="h-5 w-5 text-teal-600 mr-2" />
        <h3 className="text-lg font-semibold">Dynasty Value Added</h3>
        <div className="ml-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
            className="text-gray-400 hover:text-gray-600 focus:outline-none"
            aria-label="Information about Dynasty Value Added"
          >
            <Info className="h-4 w-4" />
          </button>
          {showInfo && (
            <div className="absolute z-20 left-4 right-4 top-12 p-3 bg-gray-900 text-white text-xs sm:text-sm rounded-lg shadow-lg sm:left-auto sm:right-4 sm:w-80">
              <p className="leading-relaxed mb-2">
                Net long-term dynasty value you added off the wire: the summed dynasty
                trade value of every player you <strong>added</strong> minus the value of
                every player you <strong>dropped</strong> (completed moves only). Positive
                means you're building roster value from the wire; negative means you're
                shedding assets faster than you replace them.
              </p>
              <p className="leading-relaxed">
                <strong>Per Add</strong> shows the same net divided by your completed adds,
                so a high-volume churner isn't mistaken for a genuine value builder.
              </p>
              <div className="absolute -top-1 left-6 sm:left-auto sm:right-6 w-2 h-2 bg-gray-900 transform rotate-45"></div>
            </div>
          )}
        </div>
      </div>

      {displayMetric ? (
        <>
          <div className="text-center mb-4">
            <div
              className={`text-4xl font-bold ${
                displayMetric.net_value >= 0 ? 'text-teal-600' : 'text-red-600'
              }`}
            >
              {displayMetric.net_value >= 0 ? '+' : ''}
              {displayMetric.net_value.toLocaleString()}
            </div>
            <div className="text-sm text-gray-600 mt-1">{displayMetric.team_name}</div>
            <div className="text-xs text-gray-500 mt-1">Net dynasty value from the wire</div>
          </div>

          <div className="grid grid-cols-3 gap-3 text-sm mb-6">
            <div className="text-center">
              <div className="text-gray-600">Added</div>
              <div className="font-semibold text-lg text-green-700">
                +{displayMetric.add_value.toLocaleString()}
              </div>
            </div>
            <div className="text-center">
              <div className="text-gray-600">Dropped</div>
              <div className="font-semibold text-lg text-red-600">
                -{displayMetric.drop_value.toLocaleString()}
              </div>
            </div>
            <div className="text-center">
              <div className="text-gray-600">Per Add</div>
              <div className="font-semibold text-lg text-gray-900">
                {displayMetric.avg_per_add >= 0 ? '+' : ''}
                {displayMetric.avg_per_add}
              </div>
            </div>
          </div>

          <div className="pt-6 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-3">League Rankings</h4>
            <div className="space-y-2">
              {[...metrics]
                .sort((a, b) => b.net_value - a.net_value)
                .slice(0, showAllTeams ? undefined : 5)
                .map((m, idx) => (
                  <div
                    key={m.roster_id}
                    onClick={() => setSelectedTeamId(m.roster_id)}
                    className={`flex justify-between items-center text-sm py-1.5 px-2 rounded cursor-pointer transition-all ${
                      m.roster_id === selectedTeamId
                        ? 'bg-teal-100 ring-2 ring-teal-400 font-medium'
                        : 'hover:bg-gray-100'
                    }`}
                  >
                    <span className="text-gray-600 truncate flex-1">
                      {idx + 1}. {m.team_name}
                    </span>
                    <span
                      className={`font-medium ml-2 ${
                        m.net_value >= 0 ? 'text-teal-700' : 'text-red-600'
                      }`}
                    >
                      {m.net_value >= 0 ? '+' : ''}
                      {m.net_value.toLocaleString()}
                    </span>
                  </div>
                ))}
            </div>

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
        <div className="text-center py-8 text-gray-500">No dynasty value data available</div>
      )}
    </div>
  );
};
