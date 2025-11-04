import React from 'react';

interface SkeletonLoaderProps {
  className?: string;
  width?: string;
  height?: string;
  rounded?: boolean;
}

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({ 
  className = '', 
  width = 'w-full', 
  height = 'h-4',
  rounded = false 
}) => {
  return (
    <div 
      className={`
        animate-pulse bg-gray-200 
        ${width} ${height} 
        ${rounded ? 'rounded-full' : 'rounded'}
        ${className}
      `} 
    />
  );
};

// Skeleton components for specific use cases
export const TableRowSkeleton: React.FC<{ columns: number }> = ({ columns }) => (
  <tr className="animate-pulse">
    {Array.from({ length: columns }).map((_, index) => (
      <td key={index} className="px-6 py-4">
        <SkeletonLoader height="h-4" />
      </td>
    ))}
  </tr>
);

export const CardSkeleton: React.FC = () => (
  <div className="card animate-pulse">
    <div className="flex items-center mb-4">
      <SkeletonLoader width="w-8" height="h-8" rounded className="mr-3" />
      <SkeletonLoader width="w-32" height="h-6" />
    </div>
    <div className="space-y-3">
      <SkeletonLoader height="h-4" />
      <SkeletonLoader height="h-4" width="w-3/4" />
      <SkeletonLoader height="h-4" width="w-1/2" />
    </div>
  </div>
);

export const MetricCardSkeleton: React.FC = () => (
  <div className="card animate-pulse">
    <div className="flex items-center">
      <SkeletonLoader width="w-12" height="h-12" rounded className="mr-4" />
      <div className="flex-1">
        <SkeletonLoader width="w-20" height="h-4" className="mb-2" />
        <SkeletonLoader width="w-16" height="h-8" />
      </div>
    </div>
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number; columns?: number }> = ({ 
  rows = 5, 
  columns = 4 
}) => (
  <div className="overflow-x-auto">
    <table className="min-w-full divide-y divide-gray-200">
      <thead className="bg-gray-50">
        <tr>
          {Array.from({ length: columns }).map((_, index) => (
            <th key={index} className="px-6 py-3">
              <SkeletonLoader height="h-4" />
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="bg-white divide-y divide-gray-200">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <TableRowSkeleton key={rowIndex} columns={columns} />
        ))}
      </tbody>
    </table>
  </div>
);

export default SkeletonLoader;