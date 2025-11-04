import React, { useEffect, useState } from 'react';
import { CheckCircle, X, AlertCircle, RefreshCw } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useQueryClient } from '@tanstack/react-query';

interface NotificationState {
  show: boolean;
  type: 'success' | 'error' | 'info';
  title: string;
  message: string;
  timestamp?: string;
  autoHide?: boolean;
}

const UpdateNotification: React.FC = () => {
  const { lastMessage } = useWebSocket();
  const [notification, setNotification] = useState<NotificationState | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!lastMessage) return;

    let newNotification: NotificationState | null = null;

    switch (lastMessage.type) {
      case 'data-updated':
        newNotification = {
          show: true,
          type: 'success',
          title: 'Data Updated!',
          message: `Pipeline file changed: ${lastMessage.data.changedFile}. Dashboard refreshed automatically.`,
          timestamp: lastMessage.data.timestamp,
          autoHide: true
        };
        
        // Refresh all queries
        queryClient.invalidateQueries({ queryKey: ['trades'] });
        queryClient.invalidateQueries({ queryKey: ['teams'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
        break;

      case 'data-error':
        newNotification = {
          show: true,
          type: 'error',
          title: 'Data Update Failed',
          message: `Failed to reload data: ${lastMessage.data.error}`,
          timestamp: lastMessage.data.timestamp,
          autoHide: false
        };
        break;

      case 'data-refreshed':
        newNotification = {
          show: true,
          type: 'success',
          title: 'Data Refreshed',
          message: 'Data has been manually refreshed successfully.',
          timestamp: lastMessage.data.timestamp,
          autoHide: true
        };
        
        // Refresh all queries
        queryClient.invalidateQueries({ queryKey: ['trades'] });
        queryClient.invalidateQueries({ queryKey: ['teams'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
        break;

      case 'refresh-error':
        newNotification = {
          show: true,
          type: 'error',
          title: 'Refresh Failed',
          message: `Manual refresh failed: ${lastMessage.data.error}`,
          timestamp: lastMessage.data.timestamp,
          autoHide: false
        };
        break;

      // Legacy support
      case 'trades-updated':
        newNotification = {
          show: true,
          type: 'success',
          title: 'New Trades Available!',
          message: `${lastMessage.data.newTradesCount || 'New'} trade(s) detected. Dashboard refreshed.`,
          timestamp: lastMessage.data.lastUpdate,
          autoHide: true
        };
        
        queryClient.invalidateQueries({ queryKey: ['trades'] });
        queryClient.invalidateQueries({ queryKey: ['teams'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
        break;
    }

    if (newNotification) {
      setNotification(newNotification);
      
      if (newNotification.autoHide) {
        setTimeout(() => {
          setNotification(null);
        }, 5000);
      }
    }
  }, [lastMessage, queryClient]);

  if (!notification?.show) {
    return null;
  }

  const getNotificationStyles = () => {
    switch (notification.type) {
      case 'success':
        return {
          bg: 'bg-green-50',
          border: 'border-green-200',
          icon: CheckCircle,
          iconColor: 'text-green-500',
          titleColor: 'text-green-800',
          messageColor: 'text-green-700',
          timestampColor: 'text-green-600',
          buttonColor: 'text-green-500 hover:text-green-700'
        };
      case 'error':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          icon: AlertCircle,
          iconColor: 'text-red-500',
          titleColor: 'text-red-800',
          messageColor: 'text-red-700',
          timestampColor: 'text-red-600',
          buttonColor: 'text-red-500 hover:text-red-700'
        };
      case 'info':
      default:
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          icon: RefreshCw,
          iconColor: 'text-blue-500',
          titleColor: 'text-blue-800',
          messageColor: 'text-blue-700',
          timestampColor: 'text-blue-600',
          buttonColor: 'text-blue-500 hover:text-blue-700'
        };
    }
  };

  const styles = getNotificationStyles();
  const IconComponent = styles.icon;

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm">
      <div className={`${styles.bg} ${styles.border} border rounded-lg shadow-lg p-4`}>
        <div className="flex items-start">
          <IconComponent className={`h-5 w-5 ${styles.iconColor} mt-0.5 mr-3 flex-shrink-0`} />
          <div className="flex-1">
            <h4 className={`text-sm font-medium ${styles.titleColor}`}>
              {notification.title}
            </h4>
            <p className={`text-sm ${styles.messageColor} mt-1`}>
              {notification.message}
            </p>
            {notification.timestamp && (
              <p className={`text-xs ${styles.timestampColor} mt-1`}>
                {new Date(notification.timestamp).toLocaleTimeString()}
              </p>
            )}
          </div>
          <button
            onClick={() => setNotification(null)}
            className={`ml-2 ${styles.buttonColor}`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default UpdateNotification;