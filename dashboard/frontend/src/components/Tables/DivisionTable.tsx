import React, { useMemo, useState } from 'react';
import { Division, StandingsTeam, StandingsSortConfig } from '../../types/standings';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

interface DivisionTableProps {
  division: Division;
  onTeamClick: (team: StandingsTeam) => void;
}

const DivisionTable: React.FC<DivisionTableProps> = ({ division, onTeamClick }) => {
  const [sortConfig, setSortConfig] = useState<StandingsSortConfig>({
    field: 'rank',
    direction: 'asc'
  });

  const formatRecord = (wins: number, losses: number, ties?: number) => {
    return ties ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
  };

  const sortedTeams = useMemo(() => {
    const teams = [...division.teams];
    
    teams.sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortConfig.field) {
        case 'rank':
          aValue = a.rank;
          bValue = b.rank;
          break;
        case 'teamName':
          aValue = a.team_name.toLowerCase();
          bValue = b.team_name.toLowerCase();
          break;
        case 'ownerName':
          aValue = a.owner_name.toLowerCase();
          bValue = b.owner_name.toLowerCase();
          break;
        case 'record':
          aValue = a.record.wins;
          bValue = b.record.wins;
          break;
        case 'medianRecord':
          aValue = a.median_record.wins;
          bValue = b.median_record.wins;
          break;
        case 'divisionRecord':
          aValue = a.division_record.wins;
          bValue = b.division_record.wins;
          break;
        case 'pointsFor':
          aValue = a.points_for;
          bValue = b.points_for;
          break;
        case 'pointsAgainst':
          aValue = a.points_against;
          bValue = b.points_against;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return teams;
  }, [division.teams, sortConfig]);

  const handleSort = (field: StandingsSortConfig['field']) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const SortIcon = ({ field }: { field: StandingsSortConfig['field'] }) => {
    if (sortConfig.field !== field) {
      return <ArrowUpDown size={14} className="text-gray-400" />;
    }
    return sortConfig.direction === 'asc' 
      ? <ArrowUp size={14} className="text-blue-600" />
      : <ArrowDown size={14} className="text-blue-600" />;
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden mb-6">
      {/* Division Header */}
      <div className="bg-gradient-to-r from-gray-700 to-gray-800 text-white px-6 py-3">
        <h2 className="text-xl font-bold">{division.division_name}</h2>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th 
                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('rank')}
              >
                <div className="flex items-center gap-1">
                  Rank
                  <SortIcon field="rank" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('teamName')}
              >
                <div className="flex items-center gap-1">
                  Team
                  <SortIcon field="teamName" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('ownerName')}
              >
                <div className="flex items-center gap-1">
                  Owner
                  <SortIcon field="ownerName" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('record')}
              >
                <div className="flex items-center gap-1">
                  Record
                  <SortIcon field="record" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                H2H
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('medianRecord')}
              >
                <div className="flex items-center gap-1">
                  Median
                  <SortIcon field="medianRecord" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('divisionRecord')}
              >
                <div className="flex items-center gap-1">
                  Division
                  <SortIcon field="divisionRecord" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('pointsFor')}
              >
                <div className="flex items-center justify-end gap-1">
                  PF
                  <SortIcon field="pointsFor" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('pointsAgainst')}
              >
                <div className="flex items-center justify-end gap-1">
                  PA
                  <SortIcon field="pointsAgainst" />
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sortedTeams.map((team, index) => (
              <tr 
                key={team.roster_id}
                className={`hover:bg-blue-50 transition-colors cursor-pointer ${
                  index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                }`}
                onClick={() => onTeamClick(team)}
              >
                <td className="px-4 py-3 text-sm font-medium text-gray-900">
                  {team.rank}
                </td>
                <td className="px-4 py-3 text-sm font-semibold text-blue-600 hover:text-blue-800">
                  {team.team_name}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  {team.owner_name}
                </td>
                <td className="px-4 py-3 text-sm font-medium text-gray-900">
                  {formatRecord(team.record.wins, team.record.losses, team.record.ties)}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  {formatRecord(team.matchup_record.wins, team.matchup_record.losses, team.matchup_record.ties)}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  <span className={team.median_record.wins > team.median_record.losses ? 'text-green-600 font-medium' : ''}>
                    {formatRecord(team.median_record.wins, team.median_record.losses)}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  {formatRecord(team.division_record.wins, team.division_record.losses, team.division_record.ties)}
                </td>
                <td className="px-4 py-3 text-sm text-right font-medium text-gray-900">
                  {team.points_for.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="px-4 py-3 text-sm text-right text-gray-700">
                  {team.points_against.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DivisionTable;
