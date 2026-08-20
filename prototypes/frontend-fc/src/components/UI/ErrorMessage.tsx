import React from 'react';
import { AlertCircle } from 'lucide-react';
import RetryButton from './RetryButton';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => Promise<void> | void;
  className?: string;
}

const ErrorMessage: React.FC<ErrorMessageProps> = ({ 
  title = 'Error', 
  message, 
  onRetry, 
  className = '' 
}) => {
  return (
    <div className={`bg-red-50 border border-red-200 rounded-lg p-6 ${className}`}>
      <div className="flex items-start">
        <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" />
        <div className="flex-1">
          <h3 className="text-sm font-medium text-red-800 mb-1">{title}</h3>
          <p className="text-sm text-red-700 mb-3">{message}</p>
          {onRetry && (
            <RetryButton 
              onRetry={onRetry}
              className="bg-red-100 text-red-800 hover:bg-red-200 focus:ring-red-500"
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ErrorMessage;