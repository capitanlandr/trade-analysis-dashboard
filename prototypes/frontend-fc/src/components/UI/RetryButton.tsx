import React from 'react';
import { RefreshCw } from 'lucide-react';
import { useRetry } from '../../hooks/useRetry';

interface RetryButtonProps {
  onRetry: () => Promise<void> | void;
  disabled?: boolean;
  className?: string;
  children?: React.ReactNode;
}

const RetryButton: React.FC<RetryButtonProps> = ({ 
  onRetry, 
  disabled = false, 
  className = '',
  children = 'Try Again'
}) => {
  const { execute, isRetrying, retryCount } = useRetry({ maxRetries: 2 });

  const handleRetry = async () => {
    try {
      await execute(async () => {
        const result = onRetry();
        if (result instanceof Promise) {
          await result;
        }
      });
    } catch (error) {
      console.error('Retry failed:', error);
    }
  };

  return (
    <button
      onClick={handleRetry}
      disabled={disabled || isRetrying}
      className={`
        flex items-center px-4 py-2 text-sm font-medium rounded-md
        transition-colors duration-200
        ${isRetrying 
          ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
          : 'bg-primary-600 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500'
        }
        ${className}
      `}
    >
      <RefreshCw 
        className={`h-4 w-4 mr-2 ${isRetrying ? 'animate-spin' : ''}`} 
      />
      {isRetrying ? (
        retryCount > 0 ? `Retrying... (${retryCount}/2)` : 'Retrying...'
      ) : (
        children
      )}
    </button>
  );
};

export default RetryButton;