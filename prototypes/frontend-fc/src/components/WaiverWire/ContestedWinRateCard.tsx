import React, { useState } from 'react';
import { Swords, Info, ChevronDown, ChevronUp } from 'lucide-react';
import type { ContestedWinMetric } from '../../types/waiver-wire';

interface ContestedWinRateCardProps {
  data: { contestedCount: number; valueThreshold: number; managers: ContestedWinMetric[] };
  currentTeamId: number;
}

const MIN_RELIABLE_ATTEMPTS = 5;

export const ContestedWinRateCard: React.FC<ContestedWinRateCardProps> = ({
  data,
  currentTeamId,
}) => {
  const { contestedCount, valueThreshold, managers } = data;
  const topTeam = [...managers].sort((a, b) => b.rate - a.rate)[0];
  const [showInfo, setShowInfo] = useState(false);
  const [showAllTeams, setShowAllTeams] = useState(false);
  const [selectedTeamId, setSelectedTeamId] = useState(topTeam?.roster_id ?? currentTeamId);

  const selectedMetric = managers.find((m) => m.roster_id === selectedTeamId);
  const userMetric = managers.find((m) => m.roster_id === currentTeamId);
  const displayMetric = selectedMetric || userMetric;

  return (
    <div className="card relative">
      <div className="flex items-center mb-4">
        <Swords className="h-5 w-5 text-rose-600 mr-2" />
        <h3 className="text-lg font-semibold">Contested Blue-Chip Win Rate</h3>
        <div className="ml-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
            className="text-gray-400 hover:text-gray-600 focus:outline-none"
            aria-label="Information about Contested Blue-Chip Win Rate"
          >
            <Info className="h-4 w-4" />
          </button>
          {showInfo && (
            <div className="absolute z-20 left-4 right-4 top-12 p-3 bg-gray-900 text-white text-xs sm:text-sm rounded-lg shadow-lg sm:left-auto sm:right-4 sm:w-80">
              <p className="leading-relaxed mb-2">
                How often you win the players the league is fighting over that are also
                worth holding long term. The contested pool is every player claimed by{' '}
                <strong>2+ teams</strong> whose dynasty value is at least{' '}
                <strong>{valueThreshold}</strong> (the league median add value) —{' '}
                {contestedCount} players in all.
              </p>
              <p className="leading-relaxed text-gray-300">
                Rate = your completed waiver adds of that pool ÷ your total claims
                (won + lost) on it. Restricting to high-value players keeps this from being
                a redraft streaming stat. Fewer than {MIN_RELIABLE_ATTEMPTS} attempts are
                flagged as small samples.
              </p>
              <div className="absolute -top-1 left-6 sm:left-auto sm:right-6 w-2 h-2 bg-gray-900 transform rotate-45"></div>
            </div>
          )}
        </div>
      </div>

      {displayMetric ? (
        <>
          <div className="text-center mb-4">
            <div className="text-5xl font-bold text-rose-600">
              {displayMetric.rate.toFixed(0)}%
            </div>
            <div className="text-sm text-gray-600 mt-1">{displayMetric.team_name}</div>
            <div className="text-xs text-gray-500 mt-1">
              Won {displayMetric.won} of {displayMetric.attempts} contested claims
              {displayMetric.attempts < MIN_RELIABLE_ATTEMPTS && (
                <span className="ml-1 text-amber-600 font-medium">• small sample</span>
              )}
            </div>
          </div>

          <div className="bg-rose-50 rounded-lg p-4 mb-6">
            <div className="w-full h-3 bg-rose-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-rose-500 transition-all duration-300"
                style={{ width: `${Math.min(100, displayMetric.rate)}%` }}
              />
            </div>
            <div className="text-xs text-gray-600 mt-2 text-center">
              {contestedCount} contested blue-chip players • value ≥ {valueThreshold}
            </div>
          </div>

          <div className="pt-6 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-3">League Rankings</h4>
            <div className="space-y-2">
              {[...managers]
                .sort((a, b) => b.rate - a.rate)
                .slice(0, showAllTeams ? undefined : 5)
                .map((m, idx) => (
                  <div
                    key={m.roster_id}
                    onClick={() => setSelectedTeamId(m.roster_id)}
                    className={`flex justify-between items-center text-sm py-1.5 px-2 rounded cursor-pointer transition-all ${
                      m.roster_id === selectedTeamId
                        ? 'bg-rose-100 ring-2 ring-rose-400 font-medium'
                        : 'hover:bg-gray-100'
                    }`}
                  >
                    <span className="text-gray-600 truncate flex-1">
                      {idx + 1}. {m.team_name}
                    </span>
                    <span className="text-xs text-gray-400 mr-2">
                      {m.won}/{m.attempts}
                      {m.attempts < MIN_RELIABLE_ATTEMPTS && '*'}
                    </span>
                    <span className="font-medium text-gray-900">{m.rate.toFixed(0)}%</span>
                  </div>
                ))}
            </div>
            {managers.length > 5 && (
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
            <p className="text-xs text-gray-400 mt-2">
              * fewer than {MIN_RELIABLE_ATTEMPTS} contested attempts — small sample
            </p>
          </div>
        </>
      ) : (
        <div className="text-center py-8 text-gray-500">No contested-claim data available</div>
      )}
    </div>
  );
};
