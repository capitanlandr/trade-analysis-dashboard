import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { BarChart3, TrendingUp, Trophy, RefreshCw, Award, FileText, Users, Target } from 'lucide-react';
import HostingBanner from '../UI/HostingBanner';
import ChampionBanner from '../UI/ChampionBanner';
import { useStandingsData } from '../../services/api';
import { activeSeason } from '../../config/seasons';

const DashboardLayout: React.FC = () => {
  // Use centralized standings hook (goes through api-client.ts toggle)
  const { data: standingsData } = useStandingsData();

  const lastUpdate = standingsData?.metadata?.last_updated;


  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <Trophy className="h-8 w-8 text-primary-600 mr-3" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  Dynasuiiii Analytics
                </h1>
                <p className="text-sm text-gray-500">
                  Trade Analytics & League Standings
                </p>
                <p className="text-xs text-gray-400">
                  League ID:{' '}
                  <a
                    href={`https://sleeper.com/leagues/${activeSeason.leagueId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:text-primary-700 hover:underline"
                  >
                    {activeSeason.leagueId}
                  </a>
                  {' '}(Season {activeSeason.number} - {activeSeason.displayYear})
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {lastUpdate && (
                <div className="text-sm text-gray-500">
                  <span className="flex items-center">
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Last Updated: {new Date(lastUpdate).toLocaleString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit',
                      hour12: true
                    })}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hosting Migration Banner */}
      <HostingBanner />

      {/* Championship Banner */}
      <ChampionBanner />

      {/* Navigation */}
      <nav className="bg-white shadow-sm relative z-20">
        <div className="max-w-7xl mx-auto px-2 sm:px-4 lg:px-8">
          <div className="flex overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 pb-px">
            <NavItem icon={BarChart3} label="Trade Analysis" mobileLabel="Trades" href="/" />
            <NavItem icon={Award} label="Standings" mobileLabel="Standings" href="/standings" />
            <NavItem icon={TrendingUp} label="Playoff Scenarios" mobileLabel="Playoffs" href="/playoff-scenarios" />
            <NavItem icon={Target} label="Draft Order" mobileLabel="Draft" href="/draft-order" />
            <NavItem icon={FileText} label="Commish Tiers" mobileLabel="Tiers" href="/commish-tiers" />
            <NavItem icon={Users} label="Waiver Wire" mobileLabel="Waivers" href="/waiver-wire" />
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-500">
              Dynasuiiii Analytics - Built with React & TypeScript
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

interface NavItemProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  mobileLabel?: string;
  href: string;
}

const NavItem: React.FC<NavItemProps> = ({ icon: Icon, label, mobileLabel, href }) => {
  const location = useLocation();
  const isActive = location.pathname === href;
  const displayLabel = mobileLabel || label;
  
  return (
    <Link
      to={href}
      className={`flex items-center justify-center gap-1.5 px-3 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex-shrink-0 ${
        isActive
          ? 'border-primary-600 text-primary-600 bg-primary-50'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 hover:bg-gray-50'
      }`}
    >
      <Icon className="h-4 w-4 flex-shrink-0" />
      <span className="hidden md:inline">
        {label}
      </span>
      <span className="md:hidden text-xs">
        {displayLabel}
      </span>
    </Link>
  );
};

export default DashboardLayout;