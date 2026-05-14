import { useState, useEffect, useCallback } from 'react';
import { apiService } from '@/services/api';
import type { PaymentAccount, PaymentAccountType } from '@/types';

export const usePaymentAccounts = (businessId: string) => {
  const [accounts, setAccounts] = useState<PaymentAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAccounts = useCallback(async (type?: PaymentAccountType, activeOnly = true) => {
    if (!businessId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getPaymentAccounts({ businessId, type, isActive: activeOnly });
      if (response.success && response.data) {
        setAccounts(response.data);
      }
    } catch (err: any) {
      setError(err.message || 'Error cargando cuentas');
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    if (businessId) fetchAccounts();
  }, [businessId, fetchAccounts]);

  return { accounts, loading, error, fetchAccounts, clearError: () => setError(null) };
};