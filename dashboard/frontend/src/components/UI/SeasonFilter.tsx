import React from 'react';
import { ChevronDownIcon } from 'lucide-react';
import type { SeasonFilter } from '../../types';

interface SeasonFilterProps {
  availableSeasons: string[];
  seasonCounts: Record<string, number>;
  selectedFilter: SeasonFilter;
  onFilterChange: (filter: SeasonFilter) => void;
  className?: string;
}

const SeasonFilter: React.FC<SeasonFilterProps> = ({
  availableSeasons,
  seasonCounts,
  selectedFilter,
  onFilterChange,
  className = ''
}) => {
  const [isOpen, setIsOpen] = React.useState(false);

  // Generate filter options
  const filterOptions: SeasonFilter[] = React.useMemo(() => {
    const options: SeasonFilter[] = [];

    // All Seasons option
    const totalCount = Object.values(seasonCounts).reduce((sum, count) => sum + count, 0);
    options.push({
      type: 'all',
      seasons: availableSeasons,
      label: `All Seasons (${totalCount})`
    });

    // Individual season options
    availableSeasons.forEach(season => {
      const count = seasonCounts[season] || 0;
      const seasonNumber = season.replace('season_', '');
      options.push({
        type: 'individual',
        seasons: [season],
        label: `Season ${seasonNumber} (${count})`
      });
    });

    // Season combination options (if more than one season available)
    if (availableSeasons.length > 1) {
      // Add common combinations like "Season 2 + Season 3"
      for (let i = 0; i < availableSeasons.length - 1; i++) {
        for (let j = i + 1; j < availableSeasons.length; j++) {
          const seasons = [availableSeasons[i], availableSeasons[j]];
          const combinedCount = seasons.reduce((sum, season) => sum + (seasonCounts[season] || 0), 0);
          const seasonNumbers = seasons.map(s => s.replace('season_', '')).join(' + ');
          options.push({
            type: 'combination',
            seasons,
            label: `Season ${seasonNumbers} (${combinedCount})`
          });
        }
      }
    }

    return options;
  }, [availableSeasons, seasonCounts]);

  const handleOptionSelect = (option: SeasonFilter) => {
    onFilterChange(option);
    setIsOpen(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent, option?: SeasonFilter) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (option) {
        handleOptionSelect(option);
      } else {
        setIsOpen(!isOpen);
      }
    } else if (event.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div className={`relative ${className}`}>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Season Filter
      </label>
      
      <div className="relative">
        <button
          type="button"
          className="relative w-full bg-white border border-gray-300 rounded-md shadow-sm pl-3 pr-10 py-2 text-left cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
          onClick={() => setIsOpen(!isOpen)}
          onKeyDown={(e) => handleKeyDown(e)}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          aria-label="Select season filter"
        >
          <span className="block truncate">
            {selectedFilter.label}
          </span>
          <span className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
            <ChevronDownIcon 
              className={`h-5 w-5 text-gray-400 transition-transform duration-200 ${
                isOpen ? 'transform rotate-180' : ''
              }`} 
              aria-hidden="true" 
            />
          </span>
        </button>

        {isOpen && (
          <div className="absolute z-10 mt-1 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm">
            {filterOptions.map((option, index) => (
              <div
                key={`${option.type}-${option.seasons.join('-')}`}
                className={`cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-primary-50 focus:bg-primary-50 ${
                  option.type === selectedFilter.type && 
                  JSON.stringify(option.seasons) === JSON.stringify(selectedFilter.seasons)
                    ? 'bg-primary-100 text-primary-900'
                    : 'text-gray-900'
                }`}
                onClick={() => handleOptionSelect(option)}
                onKeyDown={(e) => handleKeyDown(e, option)}
                role="option"
                tabIndex={0}
                aria-selected={
                  option.type === selectedFilter.type && 
                  JSON.stringify(option.seasons) === JSON.stringify(selectedFilter.seasons)
                }
              >
                <span className="block truncate font-normal">
                  {option.label}
                </span>
                
                {/* Visual separator between option types */}
                {index === 0 && filterOptions.length > 1 && (
                  <div className="absolute bottom-0 left-0 right-0 h-px bg-gray-200" />
                )}
                {option.type === 'individual' && 
                 index < filterOptions.length - 1 && 
                 filterOptions[index + 1].type === 'combination' && (
                  <div className="absolute bottom-0 left-0 right-0 h-px bg-gray-200" />
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Click outside to close */}
      {isOpen && (
        <div
          className="fixed inset-0 z-0"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
    </div>
  );
};

export default SeasonFilter;