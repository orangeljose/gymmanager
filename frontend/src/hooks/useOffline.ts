import { useState, useEffect, useCallback } from 'react';
import { offlineService } from '@/services/offlineService';

export const useOffline = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isSyncing, setIsSyncing] = useState(false);
  const [offlineStats, setOfflineStats] = useState({
    clientsCount: 0,
    pendingPaymentsCount: 0,
    syncQueueCount: 0
  });

  // Listen for online/offline events
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Update offline stats periodically
  useEffect(() => {
    const updateStats = async () => {
      try {
        const stats = await offlineService.getOfflineStats();
        setOfflineStats(stats);
      } catch (error) {
        console.error('Error updating offline stats:', error);
      }
    };

    // Initial update
    updateStats();

    // Update every 30 seconds
    const interval = setInterval(updateStats, 30000);

    return () => clearInterval(interval);
  }, []);

  // Manual sync trigger
  const triggerSync = useCallback(async () => {
    if (!isOnline) {
      return { success: false, error: 'No hay conexión a internet' };
    }

    setIsSyncing(true);
    
    try {
      await offlineService.triggerSync();
      
      // Update stats after sync
      const stats = await offlineService.getOfflineStats();
      setOfflineStats(stats);
      
      return { success: true };
    } catch (error: any) {
      console.error('Error triggering sync:', error);
      return { success: false, error: error.message || 'Error al sincronizar' };
    } finally {
      setIsSyncing(false);
    }
  }, [isOnline]);

  // Clear offline data
  const clearOfflineData = useCallback(async () => {
    try {
      await offlineService.clearOfflineData();
      setOfflineStats({
        clientsCount: 0,
        pendingPaymentsCount: 0,
        syncQueueCount: 0
      });
      return { success: true };
    } catch (error: any) {
      console.error('Error clearing offline data:', error);
      return { success: false, error: error.message || 'Error al limpiar datos offline' };
    }
  }, []);

  return {
    isOnline,
    isSyncing,
    offlineStats,
    triggerSync,
    clearOfflineData,
    hasPendingData: offlineStats.pendingPaymentsCount > 0 || offlineStats.syncQueueCount > 0
  };
};
