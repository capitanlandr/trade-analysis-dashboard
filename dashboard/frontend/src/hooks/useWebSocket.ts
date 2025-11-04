import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

interface WebSocketHookReturn {
  isConnected: boolean;
  lastMessage: any;
  connectionError: string | null;
  refreshData: () => void;
}

export const useWebSocket = (url: string = 'http://localhost:3001'): WebSocketHookReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // Initialize socket connection
    socketRef.current = io(url, {
      transports: ['websocket', 'polling'],
      timeout: 5000,
    });

    const socket = socketRef.current;

    // Connection event handlers
    socket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setConnectionError(null);
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    });

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setConnectionError(error.message);
      setIsConnected(false);
    });

    // Custom event handlers
    socket.on('welcome', (data) => {
      console.log('Welcome message:', data);
      setLastMessage({ type: 'welcome', data });
    });

    socket.on('data-updated', (data) => {
      console.log('Data updated:', data);
      setLastMessage({ type: 'data-updated', data });
    });

    socket.on('data-error', (data) => {
      console.error('Data error:', data);
      setLastMessage({ type: 'data-error', data });
    });

    socket.on('data-status', (data) => {
      console.log('Data status:', data);
      setLastMessage({ type: 'data-status', data });
    });

    socket.on('data-refreshed', (data) => {
      console.log('Data refreshed:', data);
      setLastMessage({ type: 'data-refreshed', data });
    });

    socket.on('refresh-error', (data) => {
      console.error('Refresh error:', data);
      setLastMessage({ type: 'refresh-error', data });
    });

    // Legacy event handlers (for backward compatibility)
    socket.on('trades-updated', (data) => {
      console.log('Trades updated (legacy):', data);
      setLastMessage({ type: 'trades-updated', data });
    });

    socket.on('pipeline-status', (data) => {
      console.log('Pipeline status (legacy):', data);
      setLastMessage({ type: 'pipeline-status', data });
    });

    // Cleanup on unmount
    return () => {
      socket.disconnect();
    };
  }, [url]);

  const refreshData = () => {
    if (socketRef.current && isConnected) {
      console.log('Requesting manual data refresh...');
      socketRef.current.emit('refresh-data');
    }
  };

  return {
    isConnected,
    lastMessage,
    connectionError,
    refreshData,
  };
};