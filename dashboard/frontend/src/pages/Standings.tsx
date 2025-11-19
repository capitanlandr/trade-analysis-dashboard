import React, { useState, useEffect } from 'react';
import { Trophy, Calendar, RefreshCw } from 'lucide-react';
import DivisionTable from '../components/Tables/DivisionTable';
import TeamScheduleModal from '../components/Modals/TeamScheduleModal';
import { StandingsData, StandingsTeam } from '../types/standings';

const Standings: React.FC = () => {
  const [standingsData, setStandingsData] = useState<StandingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<StandingsTeam | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    loadStandings();
  }, []);

  const loadStandings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api-standings.json');
      if (!response.ok) {
        throw new Error('Failed to load standings data');
      }
      
      const data: StandingsData = await response.json();
      setStandingsData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load standings');
      console.error('Error loading standings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTeamClick = (team: StandingsTeam) => {
    setSelectedTeam(team);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedTeam(null);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="animate-spin mx-auto mb-4 text-blue-600" size={48} />
          <p className="text-gray-600">Loading standings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
            <p className="text-red-800 font-semibold mb-2">Error Loading Standings</p>
            <p className="text-red-600 text-sm">{error}</p>
            <button
              onClick={loadStandings}
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
            
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <Calendar size={16} className="text-gray-500" />
                <span className="text-gray-600">
                  Week {standingsData.metadata.current_week} of {standingsData.metadata.total_weeks}
                </span>
              </div>
              <div className="text-gray-500">
                Updated: {formatDate(standingsData.metadata.last_updated)}
              </div>
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
            onTeamClick={handleTeamClick}
          />
        ))}

        {/* Legend */}
        <div className="bg-white rounded-lg shadow-md p-6 mt-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Column Definitions</h3>
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
