import React, { useState } from 'react';
import { TrendingUp, Info, ChevronDown, ChevronUp } from 'lucide-react';

interface SharpeManager {
  username: string;
  real_name: string;
  trades: number;
  sharpe: {
    value: number;
    mean: number;
    std_dev: number;
    verdict: string;
  };
}

interface SharpeRatioCardProps {
  managers: SharpeManager[];
}

const verdictLabel = (v: string) => {
  switch (v) {
    case 'elite': return { text: 'Elite', color: 'text-green-700 bg-green-100' };
    case 'skilled': return { text: 'Skilled', color: 'text-blue-700 bg-blue-100' };
    case 'positive_noisy': return { text: 'Positive (Noisy)', color: 'text-yellow-700 bg-yellow-100' };
    case 'insufficient_data': return { text: 'Small Sample', color: 'text-gray-600 bg-gray-100' };
    case 'losing': return { text: 'Losing', color: 'text-red-700 bg-red-100' };
    default: return { text: v, color: 'text-gray-600 bg-gray-100' };
  }
};

export const SharpeRatioCard: React.FC<SharpeRatioCardProps> = ({ managers }) => {
  const [showInfo, setShowInfo] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [selectedManager, setSelectedManager] = useState<string>(managers[0]?.username || '');

  const sorted = [...managers].sort((a, b) => b.sharpe.value - a.sharpe.value);
  const selected = sorted.find(m => m.username === selectedManager) || sorted[0];

  return (
    <div className="card">
      <div className="flex items-center mb-4">
        <TrendingUp className="h-5 w-5 text-blue-600 mr-2" />
        <h3 className="text-lg font-semibold">Sharpe Ratio</h3>
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
              <p className="leading-relaxed mb-2">
                How much value you gain per trade relative to how wildly your results swing.
                A high Sharpe means you're consistently extracting value without big gambles.
                A low Sharpe means your results are all over the place, even if some trades were great.
              </p>
              <p className="leading-relaxed mb-1"><strong>Avg Advantage:</strong> On a typical trade, how many more dynasty points your side is worth compared to what you gave up.</p>
              <p className="leading-relaxed"><strong>Volatility:</strong> How much your trade outcomes vary. High volatility means some trades are huge wins and others are big losses.</p>
              <div className="hidden sm:block absolute -top-2 right-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
              <div className="sm:hidden absolute -top-2 left-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
            </div>
          )}
        </div>
      </div>

      {selected && (
        <>
          <div className="text-center mb-4">
            <div className="text-4xl font-bold text-blue-600">
              {selected.sharpe.value.toFixed(3)}
            </div>
            <div className="text-sm text-gray-600 mt-1">{selected.real_name}</div>
            <div className="mt-2">
              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${verdictLabel(selected.sharpe.verdict).color}`}>
                {verdictLabel(selected.sharpe.verdict).text}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm mb-6">
            <div className="text-center">
              <div className="text-gray-600">Avg Advantage</div>
              <div className="font-semibold text-lg">{selected.sharpe.mean > 0 ? '+' : ''}{Math.round(selected.sharpe.mean)}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-600">Volatility</div>
              <div className="font-semibold text-lg">{Math.round(selected.sharpe.std_dev)}</div>
            </div>
          </div>
        </>
      )}

      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">League Rankings</h4>
        <div className="space-y-2">
          {sorted.slice(0, showAll ? undefined : 5).map((m, idx) => {
            const verdict = verdictLabel(m.sharpe.verdict);
            return (
              <div
                key={m.username}
                onClick={() => setSelectedManager(m.username)}
                className={`flex justify-between items-center text-sm py-1.5 px-2 rounded cursor-pointer transition-all ${
                  m.username === selectedManager ? 'bg-blue-100 ring-2 ring-blue-400 font-medium' : 'hover:bg-gray-100'
                }`}
              >
                <span className="text-gray-600 truncate flex-1">
                  {idx + 1}. {m.real_name}
                </span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${verdict.color} mr-2`}>{verdict.text}</span>
                <span className="font-medium text-gray-900">{m.sharpe.value.toFixed(2)}</span>
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
