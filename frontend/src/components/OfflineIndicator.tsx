import React from 'react';
import { Wifi, WifiOff, AlertCircle, RefreshCw } from 'lucide-react';
import { useOffline } from '@/hooks/useOffline';

export const OfflineIndicator: React.FC = () => {
  const { isOnline, isSyncing, hasPendingData, triggerSync } = useOffline();

  if (isOnline && !hasPendingData) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {/* Offline indicator */}
      {!isOnline && (
        <div className="bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2 animate-slide-up">
          <WifiOff className="h-4 w-4" />
          <span className="text-sm font-medium">Sin conexión</span>
        </div>
      )}

      {/* Pending data indicator */}
      {isOnline && hasPendingData && (
        <div className="bg-yellow-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2 animate-slide-up">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm font-medium">Datos pendientes de sincronizar</span>
          <button
            onClick={() => triggerSync()}
            disabled={isSyncing}
            className="ml-2 p-1 hover:bg-yellow-600 rounded transition-colors disabled:opacity-50"
            title="Sincronizar ahora"
          >
            <RefreshCw className={`h-3 w-3 ${isSyncing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      )}

      {/* Syncing indicator */}
      {isSyncing && (
        <div className="bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2 animate-slide-up">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span className="text-sm font-medium">Sincronizando...</span>
        </div>
      )}

      {/* Online but with pending data */}
      {isOnline && !isSyncing && hasPendingData && (
        <div className="bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2 animate-slide-up">
          <Wifi className="h-4 w-4" />
          <span className="text-sm font-medium">Conectado</span>
        </div>
      )}
    </div>
  );
};
