import React, { useState } from 'react';
import { Users, Info, ChevronDown, ChevronUp } from 'lucide-react';

interface OpponentData {
  opponent: string;
  opponent_name: string;
  net_advantage: number;
  trade_count: number;
  avg_per_trade: number;
}

interface OpponentManager {
  username: string;
  real_name: string;
  trades: number;
  net_advantage: number;
  opponent_adjusted: {
    unique_opponents: number;
    positive_matchups: number;
    top_opponent_concentration_pct: number;
    opponents: OpponentData[];
  };
}

interface OpponentAdjustedCardProps {
  managers: OpponentManager[];
}

export const OpponentAdjustedCard: React.FC<OpponentAdjustedCardProps> = ({ managers }) => {
  const [showInfo, setShowInfo] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [selectedManager, setSelectedManager] = useState<string>(managers[0]?.username || '');

  const sorted = [...managers].sort((a, b) => b.net_advantage - a.net_advantage);
  const selected = sorted.find(m => m.username === selectedManager) || sorted[0];

  // `card relative` anchors the info tooltip to the card, not the small button.
  return (
    <div className="card relative">
      <div className="flex items-center mb-4">
        <Users className="h-5 w-5 text-emerald-600 mr-2" />
        <h3 className="text-lg font-semibold">Opponent Breakdown</h3>
        <div className="ml-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
            className="text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <Info className="h-4 w-4" />
          </button>
          {/* Inset to the card's width; see SharpeRatioCard for why the original
              left-0/sm:right-0 pair ran off-screen at both breakpoints. */}
          {showInfo && (
            <div className="absolute z-20 left-4 right-4 top-12 p-3 bg-gray-900 text-white text-xs sm:text-sm rounded-lg shadow-lg sm:left-auto sm:right-4 sm:w-80">
              <p className="leading-relaxed mb-2">
                Shows who you're winning and losing value against when you trade.
                Are you extracting value from many different opponents, or is your edge really
                just coming from one person you keep fleecing?
              </p>
              <p className="leading-relaxed"><strong>Top opponent = X% of total:</strong> What percentage of your overall advantage (or losses) comes from trades with a single person. If one opponent accounts for most of your gains, your success depends on that matchup more than your own skill.</p>
              <div className="absolute -top-1 left-6 sm:left-auto sm:right-6 w-2 h-2 bg-gray-900 transform rotate-45"></div>
            </div>
          )}
        </div>
      </div>

      {selected && (
        <>
          <div className="text-center mb-4">
            <div className="text-4xl font-bold text-emerald-600">
              {selected.opponent_adjusted.positive_matchups}/{selected.opponent_adjusted.unique_opponents}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              {selected.real_name} — Winning Matchups
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Top opponent = {Math.abs(selected.opponent_adjusted.top_opponent_concentration_pct).toFixed(0)}% of total
            </div>
          </div>

          <div className="space-y-2 mb-4">
            {selected.opponent_adjusted.opponents.slice(0, 4).map((opp) => (
              <div key={opp.opponent} className="flex justify-between items-center text-sm py-1 px-2 rounded bg-gray-50">
                <span className="text-gray-700 truncate flex-1">{opp.opponent_name}</span>
                <span className="text-xs text-gray-500 mx-2">{opp.trade_count} trades</span>
                <span className={`font-medium ${opp.net_advantage >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                  {opp.net_advantage >= 0 ? '+' : ''}{Math.round(opp.net_advantage)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Select Manager</h4>
        <div className="space-y-2">
          {sorted.slice(0, showAll ? undefined : 5).map((m, idx) => (
            <div
              key={m.username}
              onClick={() => setSelectedManager(m.username)}
              className={`flex justify-between items-center text-sm py-1.5 px-2 rounded cursor-pointer transition-all ${
                m.username === selectedManager ? 'bg-emerald-100 ring-2 ring-emerald-400 font-medium' : 'hover:bg-gray-100'
              }`}
            >
              <span className="text-gray-600 truncate flex-1">
                {idx + 1}. {m.real_name}
              </span>
              <span className="text-xs text-gray-500 mr-2">
                {m.opponent_adjusted.positive_matchups}/{m.opponent_adjusted.unique_opponents}
              </span>
              <span className={`font-medium ${m.net_advantage >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                {m.net_advantage >= 0 ? '+' : ''}{Math.round(m.net_advantage)}
              </span>
            </div>
          ))}
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
