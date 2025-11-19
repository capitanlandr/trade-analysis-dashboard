import React from 'react';
import { X, CheckCircle, XCircle } from 'lucide-react';
import { StandingsTeam } from '../../types/standings';

interface TeamScheduleModalProps {
  team: StandingsTeam | null;
  isOpen: boolean;
  onClose: () => void;
}

const TeamScheduleModal: React.FC<TeamScheduleModalProps> = ({ team, isOpen, onClose }) => {
  if (!isOpen || !team) return null;

  const formatRecord = (wins: number, losses: number, ties?: number) => {
    return ties ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
  };

  const completedGames = team.schedule.filter(g => g.result !== 'UPCOMING');
  const upcomingGames = team.schedule.filter(g => g.result === 'UPCOMING');

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold">{team.team_name}</h2>
              <p className="text-blue-100 mt-1">{team.owner_name}</p>
              <div className="flex gap-4 mt-3 text-sm">
                <span>Overall: {formatRecord(team.record.wins, team.record.losses, team.record.ties)}</span>
                <span>•</span>
                <span>PF: {team.points_for.toFixed(2)}</span>
                <span>•</span>
                <span>PA: {team.points_against.toFixed(2)}</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-gray-200 transition-colors"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Completed Games */}
          {completedGames.length > 0 && (
            <div className="p-6 border-b">
              <h3 className="text-lg font-semibold mb-4 text-gray-800">Completed Games</h3>
              <div className="space-y-2">
                {completedGames.map((game) => (
                  <div
                    key={game.week}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <span className="text-sm font-medium text-gray-500 w-16">
                        Week {game.week}
                      </span>
                      <span className="text-sm text-gray-700">vs {game.opponent_name}</span>
                    </div>
                    
                    <div className="flex items-center gap-4">
                      <span
                        className={`px-2 py-1 rounded text-sm font-semibold ${
                          game.result === 'W'
                            ? 'bg-green-100 text-green-800'
                            : game.result === 'L'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {game.result}
                      </span>
                      
                      <span className="text-sm font-medium text-gray-700 w-24 text-right">
                        {game.points_for.toFixed(1)} - {game.points_against.toFixed(1)}
                      </span>
                      
                      {game.beat_median !== null && (
                        <div className="w-6 flex justify-center" title={`Median: ${game.median_score.toFixed(1)}`}>
                          {game.beat_median ? (
                            <CheckCircle size={20} className="text-green-600" />
                          ) : (
                            <XCircle size={20} className="text-red-600" />
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upcoming Games */}
          {upcomingGames.length > 0 && (
            <div className="p-6">
              <h3 className="text-lg font-semibold mb-4 text-gray-800">Remaining Schedule</h3>
              <div className="space-y-2">
                {upcomingGames.map((game) => (
                  <div
                    key={game.week}
                    className="flex items-center justify-between p-3 bg-blue-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-blue-600 w-16">
                        Week {game.week}
                      </span>
                      <span className="text-sm text-gray-700">vs {game.opponent_name}</span>
                    </div>
                    <span className="text-xs text-gray-500 uppercase">Upcoming</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeamScheduleModal;
