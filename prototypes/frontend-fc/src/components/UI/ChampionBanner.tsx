import React, { useState } from 'react';
import { X } from 'lucide-react';

const ChampionBanner: React.FC = () => {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="bg-gradient-to-r from-yellow-50 via-amber-50 to-yellow-50 border-l-4 border-yellow-400 mt-1 mb-1 relative overflow-hidden">
      {/* Subtle shimmer effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-yellow-100/40 to-transparent animate-pulse pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 relative">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 text-3xl">
            <span role="img" aria-label="trophy">🏆</span>
          </div>

          <div className="flex-1 min-w-0">
            <div className="text-sm">
              <p className="font-bold text-amber-900 text-base">
                2025 Dynasuiiii Champion: Johnny
              </p>
              <p className="text-amber-800 mt-0.5">
                The <strong>2-Man Title Charge</strong> went on an absolute heater through
                the playoffs to claim the Season 2 championship.
                27 trades, +19,856 in value added, and a title to prove it. Congratulations, Johnny!
              </p>
            </div>
          </div>

          <button
            onClick={() => setDismissed(true)}
            className="flex-shrink-0 text-amber-400 hover:text-amber-600 transition-colors"
            aria-label="Dismiss banner"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChampionBanner;
