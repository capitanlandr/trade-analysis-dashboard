import React, { useState } from 'react';
import { Trophy, Calendar, RefreshCw, Star, Award, CheckCircle, XCircle } from 'lucide-react';
import DivisionTable from '../components/Tables/DivisionTable';
import TeamScheduleModal from '../components/Modals/TeamScheduleModal';
import { StandingsTeam } from '../types/standings';
import { useStandingsData, usePlayoffScenariosData } from '../services/api';

const Standings: React.FC = () => {
  const {
    data: standingsData,
    isLoading: standingsLoading,
    error: standingsError,
    refetch: refetchStandings,
  } = useStandingsData();

  const { data: playoffData } = usePlayoffScenariosData();

  const [selectedTeam, setSelectedTeam] = useState<StandingsTeam | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleTeamClick = (team: StandingsTeam) => {
    setSelectedTeam(team);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedTeam(null);
  };

  if (standingsLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="animate-spin mx-auto mb-4 text-blue-600" size={48} />
          <p className="text-gray-600">Loading standings...</p>
        </div>
      </div>
    );
  }

  if (standingsError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
            <p className="text-red-800 font-semibold mb-2">Error Loading Standings</p>
            <p className="text-red-600 text-sm">
              {standingsError instanceof Error ? standingsError.message : 'Failed to load standings'}
            </p>
            <button
              onClick={() => refetchStandings()}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!standingsData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-600">No standings data available</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <Trophy className="text-yellow-500" size={32} />
              <div>
                <h1 className="text-3xl font-bold text-gray-800">League Standings</h1>
                <p className="text-gray-600 text-sm mt-1">
                  {standingsData.metadata.season} Season
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-sm ml-auto">
              <Calendar size={16} className="text-gray-500" />
              <span className="text-gray-600">
                Through the end of Week {standingsData.metadata.current_week}
              </span>
            </div>
          </div>
        </div>

        {/* Info Banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-blue-800 text-sm">
            <strong>Tip:</strong> Click on any team name to view their complete schedule and results
          </p>
        </div>

        {/* Division Tables */}
        {standingsData.divisions.map((division) => (
          <DivisionTable
            key={division.division_id}
            division={division}
            playoffData={playoffData ?? null}
            onTeamClick={handleTeamClick}
          />
        ))}

        {/* Legend */}
        <div className="bg-white rounded-lg shadow-md p-6 mt-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Legend</h3>

          {/* Clinch Indicators */}
          {playoffData && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Playoff Status Indicators</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-purple-600">
                    <Star size={14} className="fill-purple-600" />
                    BYE
                  </span>
                  <span className="text-gray-600">Clinched First Round Bye</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-yellow-600">
                    <Award size={14} className="fill-yellow-600" />
                    DIV
                  </span>
                  <span className="text-gray-600">Clinched Division</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-600">
                    <CheckCircle size={14} />
                    PLAYOFF
                  </span>
                  <span className="text-gray-600">Clinched Playoff Spot</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-600">
                    <XCircle size={14} />
                    ELIM
                  </span>
                  <span className="text-gray-600">Eliminated from Playoffs</span>
                </div>
              </div>
            </div>
          )}

          {/* Column Definitions */}
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-700 mb-3">Column Definitions</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="font-semibold text-gray-700">Record:</span>
                <span className="text-gray-600 ml-2">Overall wins-losses</span>
              </div>
              <div>
                <span className="font-semibold text-gray-700">H2H:</span>
                <span className="text-gray-600 ml-2">Head-to-head record</span>
              </div>
              <div>
                <span className="font-semibold text-gray-700">Median:</span>
                <span className="text-gray-600 ml-2">Games above/below median score</span>
              </div>
              <div>
                <span className="font-semibold text-gray-700">Division:</span>
                <span className="text-gray-600 ml-2">Record vs division opponents</span>
              </div>
              <div>
                <span className="font-semibold text-gray-700">PF:</span>
                <span className="text-gray-600 ml-2">Points For (total scored)</span>
              </div>
              <div>
                <span className="font-semibold text-gray-700">PA:</span>
                <span className="text-gray-600 ml-2">Points Against (total allowed)</span>
              </div>
            </div>
          </div>

          {/* Tiebreaker Rules */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">Tiebreaker Rules</h4>
            <div className="text-sm text-gray-600 space-y-2">
              <p>When teams have identical records, the following tiebreakers are applied in order:</p>
              <ol className="list-decimal list-inside space-y-1 ml-2">
                <li><span className="font-semibold text-gray-700">Head-to-Head Record</span> - Winner of matchups between tied teams</li>
                <li><span className="font-semibold text-gray-700">Division Record</span> - Better record against division opponents</li>
                <li><span className="font-semibold text-gray-700">Points For (PF)</span> - Higher total points scored</li>
              </ol>
            </div>
          </div>
        </div>
      </div>

      {/* Team Schedule Modal */}
      <TeamScheduleModal
        team={selectedTeam}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </div>
  );
};

export default Standings;
