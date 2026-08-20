import React, { Suspense } from 'react';
import LoadingSpinner from './LoadingSpinner';
import { ComponentErrorBoundary } from '../ErrorBoundary';

interface LazyLoaderProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  componentName?: string;
}

const LazyLoader: React.FC<LazyLoaderProps> = ({ 
  children, 
  fallback,
  componentName = 'Component'
}) => {
  const defaultFallback = (
    <div className="flex items-center justify-center h-32">
      <LoadingSpinner />
      <span className="ml-3 text-gray-600">Loading {componentName}...</span>
    </div>
  );

  return (
    <ComponentErrorBoundary componentName={componentName}>
      <Suspense fallback={fallback || defaultFallback}>
        {children}
      </Suspense>
    </ComponentErrorBoundary>
  );
};

export default LazyLoader;