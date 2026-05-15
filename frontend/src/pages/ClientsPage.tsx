import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Plus, Filter, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useClients } from '@/hooks/useClients';
import type { ClientStatus, Branch } from '@/types';
import { apiService } from '@/services/api';

export const ClientsPage: React.FC = () => {
  const { user } = useAuth();
  const { clients, loading, error, pagination, fetchClients, searchClients } = useClients(user?.businessId || '');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<ClientStatus | ''>('');
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchFilter, setBranchFilter] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    if (user?.businessId) {
      apiService.getBranches(user.businessId).then(res => {
        if (res.success && res.data) setBranches(res.data);
      });
    }
  }, [user?.businessId]);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (searchTerm.trim()) {
        searchClients(searchTerm);
      } else {
        fetchClients({ status: statusFilter || undefined, branchId: branchFilter || undefined });
      }
    }, 300);
    return () => clearTimeout(delayDebounce);
  }, [searchTerm, statusFilter, branchFilter]);

  const handleStatusFilter = (status: ClientStatus | '') => {
    setStatusFilter(status);
    fetchClients({ status: status || undefined, branchId: branchFilter || undefined, page: 1 });
  };

  const handlePageChange = (newPage: number) => {
    fetchClients({ status: statusFilter || undefined, branchId: branchFilter || undefined, page: newPage });
  };

  const getStatusBadge = (status: ClientStatus) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'expired':
        return 'bg-red-100 text-red-800';
      case 'suspended':
        return 'bg-yellow-100 text-yellow-800';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-VE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const getDaysRemaining = (membershipEnd: string) => {
    const today = new Date();
    const end = new Date(membershipEnd);
    const diff = Math.ceil((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    return diff;
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-gray-600 mt-1">{pagination.total} clientes registrados</p>
        </div>
        {(user?.role === 'super_admin' || user?.role === 'admin') && (
          <Link to="/clients/new" className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Cliente
          </Link>
        )}
      </div>

      <div className="card">
        <div className="p-4 border-b flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar por nombre, email o teléfono..."
              className="input pl-10 w-full"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn btn-outline ${showFilters ? 'bg-gray-50' : ''}`}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filtros
            {(statusFilter || branchFilter) && (
              <span className="ml-2 w-2 h-2 bg-primary-500 rounded-full" />
            )}
          </button>
        </div>

        {showFilters && (
          <div className="p-4 bg-gray-50 border-b flex flex-wrap gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select
                value={statusFilter}
                onChange={(e) => handleStatusFilter(e.target.value as ClientStatus | '')}
                className="input"
              >
                <option value="">Todos</option>
                <option value="active">Activos</option>
                <option value="expired">Vencidos</option>
                <option value="suspended">Suspendidos</option>
              </select>
            </div>
            {user?.role === 'super_admin' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sucursal</label>
                <select
                  value={branchFilter}
                  onChange={(e) => {
                    setBranchFilter(e.target.value);
                    fetchClients({ status: statusFilter || undefined, branchId: e.target.value || undefined, page: 1 });
                  }}
                  className="input"
                >
                  <option value="">Todas</option>
                  {branches.map(b => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>
            )}
            {(statusFilter || branchFilter) && (
              <div className="flex items-end">
                <button
                  onClick={() => {
                    setStatusFilter('');
                    setBranchFilter('');
                    fetchClients({ page: 1 });
                  }}
                  className="btn btn-ghost text-sm"
                >
                  Limpiar filtros
                </button>
              </div>
            )}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="loading-spinner h-10 w-10" />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-600">{error}</div>
        ) : clients.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500">No se encontraron clientes</p>
            {(user?.role === 'super_admin' || user?.role === 'admin') && (
              <Link to="/clients/new" className="btn btn-primary mt-4">
                <Plus className="h-4 w-4 mr-2" />
                Registrar primer cliente
              </Link>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cliente</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Teléfono</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Vencimiento</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {clients.map((client) => {
                    const daysRemaining = getDaysRemaining(client.membershipEnd);
                    return (
                      <tr key={client.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <Link to={`/clients/${client.id}`} className="block">
                            <div className="font-medium text-gray-900 hover:text-primary-600">{client.name}</div>
                            <div className="text-sm text-gray-500">{client.email}</div>
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700">{client.phone}</td>
                        <td className="px-4 py-3 text-sm text-gray-700">{client.membershipPlanId}</td>
                        <td className="px-4 py-3 text-sm">
                          <div className="text-gray-900">{formatDate(client.membershipEnd)}</div>
                          <div className={`text-xs ${daysRemaining < 0 ? 'text-red-600' : daysRemaining <= 7 ? 'text-yellow-600' : 'text-gray-500'}`}>
                            {daysRemaining < 0 ? `Vencido hace ${Math.abs(daysRemaining)} días` :
                              daysRemaining === 0 ? 'Vence hoy' :
                                `${daysRemaining} días restantes`}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(client.status)}`}>
                            {client.status === 'active' ? 'Activo' :
                              client.status === 'expired' ? 'Vencido' : 'Suspendido'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Link to={`/clients/${client.id}`} className="btn btn-ghost btn-sm">
                            Ver
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {pagination.pages > 1 && (
              <div className="p-4 border-t flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  Página {pagination.page} de {pagination.pages}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handlePageChange(pagination.page - 1)}
                    disabled={pagination.page <= 1}
                    className="btn btn-outline btn-sm"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handlePageChange(pagination.page + 1)}
                    disabled={pagination.page >= pagination.pages}
                    className="btn btn-outline btn-sm"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};