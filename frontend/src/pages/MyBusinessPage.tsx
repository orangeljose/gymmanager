import React, { useCallback, useEffect, useState } from 'react';
import { Building, Calendar, MapPin, Shield } from 'lucide-react';
import { ImageUpload } from '@/components/ImageUpload';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { Business } from '@/types';

const ROLE_LABELS: Record<string, string> = {
  super_admin: 'Super Admin',
  admin: 'Administrador',
  branch_admin: 'Encargado de Sucursal',
  cashier: 'Cajero',
  trainer: 'Entrenador',
};

const formatDate = (createdAt?: Business['createdAt']) => {
  if (!createdAt) return 'N/A';
  if (typeof createdAt === 'string') return new Date(createdAt).toLocaleDateString();
  if ('seconds' in createdAt) return new Date(createdAt.seconds * 1000).toLocaleDateString();
  return 'N/A';
};

/**
 * Vista de solo lectura del negocio actual.
 *
 * - super_admin: usa el negocio elegido en el selector del header.
 * - admin / branch_admin: usa el negocio de su usuario.
 */
export const MyBusinessPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();

  const businessId = user?.role === 'super_admin'
    ? selectedBusinessId || ''
    : user?.businessId || '';

  const [business, setBusiness] = useState<Business | null>(null);
  const [branchesCount, setBranchesCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBusiness = useCallback(async () => {
    if (!businessId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [businessRes, branchesRes] = await Promise.all([
        apiService.getBusinesses(),
        apiService.getBranches(businessId),
      ]);

      if (businessRes.success && businessRes.data) {
        const found = businessRes.data.find((b) => b.id === businessId) || null;
        setBusiness(found);
        if (!found) setError('No se encontró el negocio');
      } else {
        setError(businessRes.error?.message || 'No se pudo cargar el negocio');
      }

      if (branchesRes.success) {
        setBranchesCount((branchesRes.data || []).length);
      }
    } catch (err: any) {
      setError(err.message || 'Error cargando el negocio');
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    loadBusiness();
  }, [loadBusiness]);

  const handleLogoChange = async (url: string | null) => {
    if (!business) return;
    try {
      const response = await apiService.updateBusiness(business.id, { logo: url });
      if (response.success) {
        setBusiness({ ...business, logo: url });
      } else {
        setError(response.error?.message || 'No se pudo actualizar el logo');
      }
    } catch (err: any) {
      setError(err.message || 'No se pudo actualizar el logo');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  const header = (
    <div className="flex items-center space-x-3 mb-6">
      <div className="p-2 bg-blue-100 rounded-lg">
        <Building className="h-6 w-6 text-blue-600" />
      </div>
      <h1 className="text-2xl font-bold text-gray-900">Mi Negocio</h1>
    </div>
  );

  if (!businessId) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        {header}
        <div className="bg-white rounded-lg shadow-sm p-6 text-center text-gray-500">
          {user?.role === 'super_admin'
            ? 'Selecciona un negocio en el selector para ver sus detalles.'
            : 'Tu usuario no tiene un negocio asignado.'}
        </div>
      </div>
    );
  }

  if (error || !business) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        {header}
        <div className="bg-white rounded-lg shadow-sm p-6 text-center text-red-600">
          {error || 'No se encontró el negocio'}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {header}

      <div className="bg-white rounded-2xl shadow-sm ring-1 ring-gray-100 p-8 mb-6">
        <div className="flex flex-col items-center text-center mb-8">
          <ImageUpload
            value={business.logo}
            onChange={handleLogoChange}
            folder="businesses"
            businessId={businessId}
            variant="logo"
            shape="square"
            size="lg"
            align="center"
            label="Subir logo"
            hint="JPG, PNG o WebP · máximo 5 MB"
          />
          <h2 className="mt-5 text-2xl font-semibold text-gray-900">{business.name}</h2>
          <p className="mt-1 text-sm text-gray-500">Logo del negocio</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 border-t border-gray-100 pt-6">
          <div className="rounded-xl bg-gray-50 p-4 text-center">
            <Calendar className="mx-auto h-4 w-4 text-gray-400" />
            <p className="mt-2 text-xs text-gray-500">Creado</p>
            <p className="text-sm font-medium text-gray-900">{formatDate(business.createdAt)}</p>
          </div>

          <div className="rounded-xl bg-gray-50 p-4 text-center">
            <MapPin className="mx-auto h-4 w-4 text-gray-400" />
            <p className="mt-2 text-xs text-gray-500">Sucursales</p>
            <p className="text-sm font-medium text-gray-900">{branchesCount}</p>
          </div>

          <div className="rounded-xl bg-gray-50 p-4 text-center">
            <Shield className="mx-auto h-4 w-4 text-gray-400" />
            <p className="mt-2 text-xs text-gray-500">Rol</p>
            <p className="text-sm font-medium text-gray-900">
              {ROLE_LABELS[user?.role || ''] || user?.role}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
