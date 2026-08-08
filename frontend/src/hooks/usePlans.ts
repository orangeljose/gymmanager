import { useState, useEffect, useCallback } from 'react';
import { apiService } from '@/services/api';
import type { MembershipPlan } from '@/types';

export const usePlans = (businessId: string) => {
  const [plans, setPlans] = useState<MembershipPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPlans = useCallback(async (activeOnly = true) => {
    if (!businessId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getPlans({ businessId, isActive: activeOnly });
      if (response.success && response.data) {
        setPlans(response.data);
      }
    } catch (err: any) {
      setError(err.message || 'Error cargando planes');
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    if (businessId) fetchPlans();
  }, [businessId, fetchPlans]);

  return { plans, loading, error, fetchPlans, setPlans, clearError: () => setError(null) };
};