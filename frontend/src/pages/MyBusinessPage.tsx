import React, { useCallback, useEffect, useState } from 'react';
import { Building, Calendar, MapPin, Shield } from 'lucide-react';
import { ImageUpload } from '@/components/ImageUpload';
import { imageUrl } from '@/utils/images';
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
    <div className="p-6 max-w-2xl mx-auto">
      {header}

      <div className="bg-white rounded-lg shadow-sm p-6 mb-4">
        <div className="flex items-start gap-4 mb-4">
          {business.logo ? (
            <img
              src={imageUrl(business.logo, 'logo')}
              alt={business.name}
              className="h-20 w-20 rounded-xl object-contain bg-gray-50 ring-1 ring-gray-100"
            />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-xl bg-primary-100">
              <Building className="h-8 w-8 text-primary-600" />
            </div>
          )}
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-900">{business.name}</h2>
            <ImageUpload
              value={business.logo}
              onChange={handleLogoChange}
              folder="businesses"
              businessId={businessId}
              variant="logo"
              shape="square"
              label="Logo del negocio"
              hint="PNG con fondo transparente se ve mejor"
            />
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center space-x-3 text-sm">
            <Calendar className="h-4 w-4 text-gray-400" />
            <span className="text-gray-500">Creado:</span>
            <span className="text-gray-900 font-medium">{formatDate(business.createdAt)}</span>
          </div>

          <div className="flex items-center space-x-3 text-sm">
            <MapPin className="h-4 w-4 text-gray-400" />
            <span className="text-gray-500">Sucursales:</span>
            <span className="text-gray-900 font-medium">{branchesCount}</span>
          </div>

          <div className="flex items-center space-x-3 text-sm">
            <Shield className="h-4 w-4 text-gray-400" />
            <span className="text-gray-500">Rol:</span>
            <span className="text-gray-900 font-medium">
              {ROLE_LABELS[user?.role || ''] || user?.role}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
