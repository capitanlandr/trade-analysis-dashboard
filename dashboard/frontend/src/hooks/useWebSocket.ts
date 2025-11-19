// Disabled - using static JSON files like prod
interface WebSocketHookReturn {
  isConnected: boolean;
  lastMessage: any;
  connectionError: string | null;
  refreshData: () => void;
}

export const useWebSocket = (): WebSocketHookReturn => {
  return {
    isConnected: false,
    lastMessage: null,
    connectionError: null,
    refreshData: () => {
      console.log('Refresh disabled - run update_dashboard.py to regenerate data');
      window.location.reload();
    },
  };
};