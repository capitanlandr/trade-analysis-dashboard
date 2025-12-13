import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { BarChart3, TrendingUp, Trophy, RefreshCw, Award, FileText, Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

const DashboardLayout: React.FC = () => {
  // Fetch standings data to get last update time
  const { data: standingsData } = useQuery({
    queryKey: ['standings'],
    queryFn: () => fetch('/api-standings.json').then(res => res.json()),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

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
                    href="https://sleeper.com/leagues/1180814327660371968"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:text-primary-700 hover:underline"
                  >
                    1180814327660371968
                  </a>
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

      {/* Navigation */}
      <nav className="bg-white shadow-sm relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex overflow-x-auto scrollbar-hide space-x-1 sm:space-x-8">
            <NavItem icon={BarChart3} label="Trade Analysis" mobileLabel="Trade Analysis" href="/" />
            <NavItem icon={Award} label="Standings" mobileLabel="Standings" href="/standings" />
            <NavItem icon={TrendingUp} label="Playoff Scenarios" mobileLabel="Playoff Scenarios" href="/playoff-scenarios" />
            <NavItem icon={FileText} label="Commish Tiers" mobileLabel="Commish Tiers" href="/commish-tiers" />
            <NavItem icon={Users} label="Waiver Wire Analysis" mobileLabel="Waiver Wire" href="/waiver-wire" />
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
      className={`flex flex-col xs:flex-row items-center justify-center xs:justify-start px-2 xs:px-3 py-3 xs:py-4 text-xs xs:text-sm font-medium border-b-2 transition-colors whitespace-nowrap min-w-0 ${
        isActive
          ? 'border-primary-600 text-primary-600 bg-primary-50'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 hover:bg-gray-50'
      }`}
    >
      <Icon className="h-4 w-4 xs:mr-2 flex-shrink-0" />
      <span className="hidden sm:inline text-sm leading-tight">
        {label}
      </span>
      <span className="sm:hidden text-[10px] leading-tight text-center mt-1">
        {displayLabel}
      </span>
    </Link>
  );
};

export default DashboardLayout;