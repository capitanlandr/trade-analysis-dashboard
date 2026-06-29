import React, { useState } from 'react';
import { Target, Info, ChevronDown, ChevronUp } from 'lucide-react';

interface SignificanceManager {
  username: string;
  real_name: string;
  trades: number;
  significance: {
    wins: number;
    win_rate: number;
    p_value: number;
    direction: string;
    verdict: string;
  };
}

interface SignificanceCardProps {
  managers: SignificanceManager[];
}

const verdictLabel = (v: string, direction: string) => {
  switch (v) {
    case 'significant': return direction === 'winning'
      ? { text: 'Significant Winner', color: 'text-green-700 bg-green-100' }
      : { text: 'Significant Loser', color: 'text-red-700 bg-red-100' };
    case 'approaching': return { text: 'Approaching', color: 'text-yellow-700 bg-yellow-100' };
    case 'not_significant': return { text: 'Not Significant', color: 'text-gray-600 bg-gray-100' };
    default: return { text: v, color: 'text-gray-600 bg-gray-100' };
  }
};

export const SignificanceCard: React.FC<SignificanceCardProps> = ({ managers }) => {
  const [showInfo, setShowInfo] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [selectedManager, setSelectedManager] = useState<string>(managers[0]?.username || '');

  const sorted = [...managers].sort((a, b) => b.significance.win_rate - a.significance.win_rate);
  const selected = sorted.find(m => m.username === selectedManager) || sorted[0];

  return (
    <div className="card">
      <div className="flex items-center mb-4">
        <Target className="h-5 w-5 text-purple-600 mr-2" />
        <h3 className="text-lg font-semibold">Win Rate Significance</h3>
        <div className="relative ml-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
            className="text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <Info className="h-4 w-4" />
          </button>
          {showInfo && (
            <div className="absolute z-10 w-72 sm:w-80 p-3 bg-gray-900 text-white text-xs sm:text-sm rounded-lg shadow-lg top-6 left-0 sm:left-auto sm:right-0">
              <p className="leading-relaxed">
                Tests whether each manager's win rate could happen by pure luck (coin flip).
                The p-value shows the probability of getting this record or better by chance alone.
                Below 0.05 = statistically significant (unlikely luck). With 7-32 trades per manager,
                most records are not yet distinguishable from randomness.
              </p>
              <div className="hidden sm:block absolute -top-2 right-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
              <div className="sm:hidden absolute -top-2 left-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
            </div>
          )}
        </div>
      </div>

      {selected && (
        <>
          <div className="text-center mb-4">
            <div className="text-4xl font-bold text-purple-600">
              {selected.significance.win_rate.toFixed(0)}%
            </div>
            <div className="text-sm text-gray-600 mt-1">{selected.real_name}</div>
            <div className="mt-2">
              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${verdictLabel(selected.significance.verdict, selected.significance.direction).color}`}>
                {verdictLabel(selected.significance.verdict, selected.significance.direction).text}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 text-sm mb-6">
            <div className="text-center">
              <div className="text-gray-600">Wins</div>
              <div className="font-semibold text-lg">{selected.significance.wins}/{selected.trades}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-600">p-value</div>
              <div className="font-semibold text-lg">{selected.significance.p_value.toFixed(3)}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-600">Trades</div>
              <div className="font-semibold text-lg">{selected.trades}</div>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600">
            {selected.significance.p_value < 0.05
              ? `With ${selected.trades} trades, this win rate is statistically significant — unlikely to be luck.`
              : selected.significance.p_value < 0.15
              ? `With ${selected.trades} trades, this is suggestive but not conclusive. Need more trades to confirm.`
              : `With ${selected.trades} trades, this record is within the range of normal coin-flip variance.`
            }
          </div>
        </>
      )}

      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">League Rankings</h4>
        <div className="space-y-2">
          {sorted.slice(0, showAll ? undefined : 5).map((m, idx) => {
            return (
              <div
                key={m.username}
                onClick={() => setSelectedManager(m.username)}
                className={`flex justify-between items-center text-sm py-1.5 px-2 rounded cursor-pointer transition-all ${
                  m.username === selectedManager ? 'bg-purple-100 ring-2 ring-purple-400 font-medium' : 'hover:bg-gray-100'
                }`}
              >
                <span className="text-gray-600 truncate flex-1">
                  {idx + 1}. {m.real_name}
                </span>
                <span className="text-xs text-gray-500 mr-2">{m.significance.wins}/{m.trades}</span>
                <span className="font-medium text-gray-900">{m.significance.win_rate.toFixed(0)}%</span>
              </div>
            );
          })}
        </div>
        {sorted.length > 5 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="mt-3 w-full flex items-center justify-center gap-1 text-sm text-primary-600 hover:text-primary-700 font-medium focus:outline-none"
          >
            {showAll ? (<><span>Show Less</span><ChevronUp className="h-4 w-4" /></>) : (<><span>More Details</span><ChevronDown className="h-4 w-4" /></>)}
          </button>
        )}
      </div>
    </div>
  );
};
