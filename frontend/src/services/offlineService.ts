import Dexie, { Table } from 'dexie';
import { envConfig } from './firebase';
import type { 
  OfflineClient, 
  OfflinePayment, 
  PendingSync, 
  Client, 
  Payment 
} from '@/types';

// Database class definition
class GymManagerDB extends Dexie {
  clients!: Table<OfflineClient>;
  payments!: Table<OfflinePayment>;
  pendingSync!: Table<PendingSync>;

  constructor() {
    super('GymManagerDB');
    
    // Define schema
    this.version(1).stores({
      clients: '++id, businessId, branchId, email, name, lastViewed, status',
      payments: '++localId, clientId, businessId, branchId, registeredAt, synced',
      pendingSync: '++id, type, timestamp, retryCount'
    });
  }
}

// Initialize database
const db = new GymManagerDB();

// Offline service class
class OfflineService {
  private isOnline: boolean = navigator.onLine;
  private syncInProgress: boolean = false;
  private syncQueue: PendingSync[] = [];

  constructor() {
    // Listen for online/offline events
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.triggerSync();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });

    // Trigger initial sync if online
    if (this.isOnline) {
      setTimeout(() => this.triggerSync(), 1000);
    }
  }

  // Client operations
  async saveClientOffline(client: Client): Promise<void> {
    try {
      const offlineClient: OfflineClient = {
        ...client,
        lastViewed: new Date().toISOString()
      };
      
      await db.clients.put(offlineClient);
      console.log('Client saved offline:', client.id);
    } catch (error) {
      console.error('Error saving client offline:', error);
      throw error;
    }
  }

  async getClientOffline(clientId: string): Promise<OfflineClient | undefined> {
    try {
      return await db.clients.get(clientId);
    } catch (error) {
      console.error('Error getting client offline:', error);
      return undefined;
    }
  }

  async getClientsOffline(businessId: string, limit: number = 200): Promise<OfflineClient[]> {
    try {
      return await db.clients
        .where('businessId')
        .equals(businessId)
        .limit(limit)
        .toArray();
    } catch (error) {
      console.error('Error getting clients offline:', error);
      return [];
    }
  }

  async searchClientsOffline(businessId: string, searchTerm: string): Promise<OfflineClient[]> {
    try {
      const clients = await db.clients
        .where('businessId')
        .equals(businessId)
        .toArray();
      
      // Simple text search (case insensitive)
      const searchLower = searchTerm.toLowerCase();
      return clients.filter(client => 
        client.name.toLowerCase().includes(searchLower) ||
        client.email.toLowerCase().includes(searchLower) ||
        client.phone.includes(searchTerm)
      );
    } catch (error) {
      console.error('Error searching clients offline:', error);
      return [];
    }
  }

  // Payment operations
  async savePaymentOffline(payment: Omit<Payment, 'id' | 'syncedAt' | 'createdAt'>): Promise<string> {
    try {
      const localId = `offline_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const offlinePayment: OfflinePayment = {
        ...payment,
        localId,
        registeredAt: new Date().toISOString(),
        synced: false
      };
      
      await db.payments.put(offlinePayment);
      
      // Add to sync queue
      await this.addToSyncQueue({
        id: localId,
        type: 'payment',
        data: offlinePayment,
        timestamp: new Date().toISOString(),
        retryCount: 0
      });
      
      console.log('Payment saved offline:', localId);
      return localId;
    } catch (error) {
      console.error('Error saving payment offline:', error);
      throw error;
    }
  }

  async getPendingPayments(): Promise<OfflinePayment[]> {
    try {
      return await db.payments
        .filter(payment => !payment.synced)
        .toArray();
    } catch (error) {
      console.error('Error getting pending payments:', error);
      return [];
    }
  }

  async markPaymentSynced(localId: string, serverId: string): Promise<void> {
    try {
      await db.payments.update(localId, { 
        synced: true,
        id: serverId 
      });
      
      // Remove from sync queue
      await this.removeFromSyncQueue(localId);
      
      console.log('Payment marked as synced:', localId);
    } catch (error) {
      console.error('Error marking payment as synced:', error);
      throw error;
    }
  }

  // Sync queue operations
  private async addToSyncQueue(item: PendingSync): Promise<void> {
    try {
      await db.pendingSync.put(item);
    } catch (error) {
      console.error('Error adding to sync queue:', error);
    }
  }

  private async removeFromSyncQueue(id: string): Promise<void> {
    try {
      await db.pendingSync.delete(id);
    } catch (error) {
      console.error('Error removing from sync queue:', error);
    }
  }

  async getSyncQueue(): Promise<PendingSync[]> {
    try {
      return await db.pendingSync.toArray();
    } catch (error) {
      console.error('Error getting sync queue:', error);
      return [];
    }
  }

  // Synchronization
  async triggerSync(): Promise<void> {
    if (!this.isOnline || this.syncInProgress || !envConfig.enableOffline) {
      return;
    }

    this.syncInProgress = true;
    console.log('Starting offline synchronization...');

    try {
      const pendingItems = await this.getSyncQueue();
      
      if (pendingItems.length === 0) {
        console.log('No items to sync');
        return;
      }

      // Sync payments
      const pendingPayments = await this.getPendingPayments();
      if (pendingPayments.length > 0) {
        await this.syncPayments(pendingPayments);
      }

      console.log('Synchronization completed');
    } catch (error) {
      console.error('Error during synchronization:', error);
    } finally {
      this.syncInProgress = false;
    }
  }

  private async syncPayments(payments: OfflinePayment[]): Promise<void> {
    try {
      const { apiService } = await import('./api');
      
      // Convert to API format
      const paymentsToSync = payments.map(payment => ({
        clientId: payment.clientId,
        amount: payment.amount,
        method: payment.method,
        membershipPlanId: payment.membershipPlanId,
        branchId: payment.branchId,
        methodDetails: payment.methodDetails,
        registeredAt: payment.registeredAt,
        localId: payment.localId
      }));

      const response = await apiService.syncOfflinePayments(paymentsToSync);
      
      if (response.success && response.data) {
        // Mark successful syncs
        for (const result of response.data.results) {
          if (result.status === 'success') {
            await this.markPaymentSynced(result.localId, result.serverId);
          } else {
            // Handle failed sync - increment retry count
            await this.incrementRetryCount(result.localId);
          }
        }
      }
    } catch (error) {
      console.error('Error syncing payments:', error);
      
      // Increment retry count for all payments
      for (const payment of payments) {
        await this.incrementRetryCount(payment.localId);
      }
    }
  }

  private async incrementRetryCount(localId: string): Promise<void> {
    try {
      const item = await db.pendingSync.get(localId);
      if (item) {
        const retryCount = item.retryCount + 1;
        
        // Remove item if max retries reached (5)
        if (retryCount >= 5) {
          await this.removeFromSyncQueue(localId);
          console.warn('Max retries reached for item:', localId);
        } else {
          await db.pendingSync.update(localId, { retryCount });
        }
      }
    } catch (error) {
      console.error('Error incrementing retry count:', error);
    }
  }

  // Utility methods
  isOnlineStatus(): boolean {
    return this.isOnline;
  }

  isSyncing(): boolean {
    return this.syncInProgress;
  }

  async clearOfflineData(): Promise<void> {
    try {
      await db.clients.clear();
      await db.payments.clear();
      await db.pendingSync.clear();
      console.log('Offline data cleared');
    } catch (error) {
      console.error('Error clearing offline data:', error);
      throw error;
    }
  }

  async getOfflineStats(): Promise<{
    clientsCount: number;
    pendingPaymentsCount: number;
    syncQueueCount: number;
  }> {
    try {
      const clientsCount = await db.clients.count();
      const pendingPaymentsCount = await db.payments.filter(payment => !payment.synced).count();
      const syncQueueCount = await db.pendingSync.count();

      return {
        clientsCount,
        pendingPaymentsCount,
        syncQueueCount
      };
    } catch (error) {
      console.error('Error getting offline stats:', error);
      return {
        clientsCount: 0,
        pendingPaymentsCount: 0,
        syncQueueCount: 0
      };
    }
  }
}

export const offlineService = new OfflineService();
export default offlineService;
