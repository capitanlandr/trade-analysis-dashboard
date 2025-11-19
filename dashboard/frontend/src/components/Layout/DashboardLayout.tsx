import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { BarChart3, TrendingUp, Trophy, RefreshCw, Award } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../services/api';

const DashboardLayout: React.FC = () => {
  const { data: statusData } = useQuery({
    queryKey: ['status'],
    queryFn: () => api.status(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const lastUpdate = (statusData?.data as any)?.lastDataUpdate;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Trophy className="h-8 w-8 text-primary-600 mr-3" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  Dynasuiiii Analytics
                </h1>
                <p className="text-sm text-gray-500">
                  Trade Analytics & League Standings
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {lastUpdate && (
                <div className="text-sm text-gray-500">
                  <span className="flex items-center">
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Updated: {new Date(lastUpdate).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <NavItem icon={BarChart3} label="Overview" href="/" />
            <NavItem icon={Award} label="Standings" href="/standings" />
            <NavItem icon={TrendingUp} label="Playoff Scenarios" href="/playoff-scenarios" />
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
  href: string;
}

const NavItem: React.FC<NavItemProps> = ({ icon: Icon, label, href }) => {
  const location = useLocation();
  const isActive = location.pathname === href;
  
  return (
    <Link
      to={href}
      className={`flex items-center px-3 py-4 text-sm font-medium border-b-2 transition-colors ${
        isActive
          ? 'border-primary-600 text-primary-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
      }`}
    >
      <Icon className="h-4 w-4 mr-2" />
      {label}
    </Link>
  );
};

export default DashboardLayout;