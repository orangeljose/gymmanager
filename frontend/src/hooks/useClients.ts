import { useState, useEffect, useCallback } from 'react';
import { apiService } from '@/services/api';
import { offlineService } from '@/services/offlineService';
import type { Client, ClientFilters, ClientFormData } from '@/types';

export const useClients = (businessId: string) => {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    pages: 0
  });

  // Fetch clients from API
  const fetchClients = useCallback(async (filters: ClientFilters = {}) => {
    if (!businessId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getClients({
        ...filters,
        businessId,
        page: filters.page || pagination.page,
        limit: filters.limit || pagination.limit
      });

      if (response.success && response.data) {
        setClients(response.data);
        if (response.meta) {
          setPagination({
            page: response.meta.page || 1,
            limit: response.meta.limit || 20,
            total: response.meta.total || 0,
            pages: response.meta.pages || 0
          });
        }
      }
    } catch (error: any) {
      console.error('Error fetching clients:', error);
      setError(error.message || 'Error al cargar clientes');
      
      // Try to load from offline storage if online request fails
      if (offlineService.isOnlineStatus()) {
        const offlineClients = await offlineService.getClientsOffline(businessId, pagination.limit);
        if (offlineClients.length > 0) {
          setClients(offlineClients as Client[]);
          setError('Mostrando datos offline. Última sincronización: ' + new Date().toLocaleString());
        }
      }
    } finally {
      setLoading(false);
    }
  }, [businessId, pagination.page, pagination.limit]);

  // Search clients (offline first, then online)
  const searchClients = useCallback(async (searchTerm: string) => {
    if (!businessId) return;

    setLoading(true);
    setError(null);

    try {
      // First try offline search for instant results
      const offlineResults = await offlineService.searchClientsOffline(businessId, searchTerm);
      setClients(offlineResults as Client[]);

      // Then try online search
      const response = await apiService.getClients({
        businessId,
        search: searchTerm,
        limit: 50
      });

      if (response.success && response.data) {
        setClients(response.data);
        
        // Update offline cache with new results
        for (const client of response.data) {
          await offlineService.saveClientOffline(client);
        }
      }
    } catch (error: any) {
      console.error('Error searching clients:', error);
      setError(error.message || 'Error al buscar clientes');
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  // Get single client
  const getClient = useCallback(async (clientId: string) => {
    if (!businessId) return null;

    setLoading(true);
    setError(null);

    try {
      // First try offline
      const offlineClient = await offlineService.getClientOffline(clientId);
      if (offlineClient) {
        return offlineClient as Client;
      }

      // Then try online
      const response = await apiService.getClient(clientId);
      
      if (response.success && response.data) {
        // Cache client offline
        await offlineService.saveClientOffline(response.data);
        return response.data;
      }
      
      return null;
    } catch (error: any) {
      console.error('Error getting client:', error);
      setError(error.message || 'Error al obtener cliente');
      return null;
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  // Create client
  const createClient = useCallback(async (data: ClientFormData) => {
    if (!businessId) return { success: false, error: 'Business ID requerido' };

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.createClient({
        ...data,
        businessId
      });

      if (response.success && response.data) {
        // Add to local state
        setClients(prev => [response.data!, ...prev]);
        
        // Cache offline
        await offlineService.saveClientOffline(response.data);
        
        return { success: true, data: response.data };
      }
      
      return { success: false, error: 'Error al crear cliente' };
    } catch (error: any) {
      console.error('Error creating client:', error);
      const errorMessage = error.message || 'Error al crear cliente';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  // Update client
  const updateClient = useCallback(async (clientId: string, data: Partial<ClientFormData>) => {
    if (!businessId) return { success: false, error: 'Business ID requerido' };

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.updateClient(clientId, data);

      if (response.success && response.data) {
        // Update local state
        setClients(prev => 
          prev.map(client => 
            client.id === clientId ? response.data! : client
          )
        );
        
        // Update offline cache
        await offlineService.saveClientOffline(response.data);
        
        return { success: true, data: response.data };
      }
      
      return { success: false, error: 'Error al actualizar cliente' };
    } catch (error: any) {
      console.error('Error updating client:', error);
      const errorMessage = error.message || 'Error al actualizar cliente';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  // Get client payments
  const getClientPayments = useCallback(async (clientId: string) => {
    if (!businessId) return [];

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getClientPayments(clientId);
      
      if (response.success && response.data) {
        return response.data;
      }
      
      return [];
    } catch (error: any) {
      console.error('Error getting client payments:', error);
      setError(error.message || 'Error al obtener pagos del cliente');
      return [];
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  // Load initial data
  useEffect(() => {
    if (businessId) {
      fetchClients();
    }
  }, [businessId, fetchClients]);

  return {
    clients,
    loading,
    error,
    pagination,
    fetchClients,
    searchClients,
    getClient,
    createClient,
    updateClient,
    getClientPayments,
    clearError: () => setError(null)
  };
};
