import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Users, 
  DollarSign, 
  AlertTriangle, 
  Calendar,
  TrendingUp,
  CreditCard,
  UserCheck,
  Building
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useOffline } from '@/hooks/useOffline';
import { apiService } from '@/services/api';
import type { DashboardMetrics, Client, Branch } from '@/types';

export const DashboardPage: React.FC = () => {
  const { user, hasPermission } = useAuth();
  const { isOnline } = useOffline();
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    activeClients: 0,
    todayIncome: 0,
    overdueClients: 0,
    expiringThisWeek: 0
  });
  const [loading, setLoading] = useState(true);
  const [recentClients, setRecentClients] = useState<Client[]>([]);
  const [expiringClients, setExpiringClients] = useState<Client[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selectedBranchId, setSelectedBranchId] = useState<string>('all');

  useEffect(() => {
    const loadBranches = async () => {
      if (!user?.businessId) return;
      
      try {
        const branchesResponse = await apiService.getBranches(user.businessId);
        if (branchesResponse.success && branchesResponse.data) {
          setBranches(branchesResponse.data);
        }
      } catch (error) {
        console.error('Error loading branches:', error);
      }
    };

    loadBranches();
  }, [user?.businessId]);

  useEffect(() => {
    const loadDashboardData = async () => {
      if (!user?.businessId) return;

      try {
        setLoading(true);
        
        // Determinar el filtro a usar
        const paymentFilter = user.role === 'super_admin' 
          ? {
              ...(selectedBranchId !== 'all' ? { branchId: selectedBranchId } : { businessId: user.businessId }),
              startDate: new Date().toISOString().split('T')[0],
              endDate: new Date().toISOString().split('T')[0]
            }
          : {
              ...(user.branchId ? { branchId: user.branchId } : { businessId: user.businessId }),
              startDate: new Date().toISOString().split('T')[0],
              endDate: new Date().toISOString().split('T')[0]
            };

        // Load metrics (you would need to create these endpoints)
        const [clientsResponse, paymentsResponse] = await Promise.all([
          apiService.getClients({ 
            businessId: user.businessId, 
            status: 'active', 
            limit: 100 
          }),
          apiService.getPaymentReport(paymentFilter)
        ]);

        if (clientsResponse.success && clientsResponse.data) {
          const activeClients = clientsResponse.data.length;
          const expiringThisWeek = clientsResponse.data.filter(client => {
            const membershipEnd = new Date(client.membershipEnd);
            const oneWeekFromNow = new Date();
            oneWeekFromNow.setDate(oneWeekFromNow.getDate() + 7);
            return membershipEnd <= oneWeekFromNow && membershipEnd > new Date();
          }).length;

          setMetrics(prev => ({
            ...prev,
            activeClients,
            expiringThisWeek
          }));

          // Get recent clients (last 5)
          setRecentClients(clientsResponse.data.slice(0, 5));
          setExpiringClients(clientsResponse.data
            .filter(client => {
              const membershipEnd = new Date(client.membershipEnd);
              const oneWeekFromNow = new Date();
              oneWeekFromNow.setDate(oneWeekFromNow.getDate() + 7);
              return membershipEnd <= oneWeekFromNow && membershipEnd > new Date();
            })
            .slice(0, 3)
          );
        }

        if (paymentsResponse.success && paymentsResponse.data) {
          const todayIncome = paymentsResponse.data.summary?.totalAmount || 0;
          setMetrics(prev => ({ ...prev, todayIncome }));
        }

      } catch (error) {
        console.error('Error loading dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, [user?.businessId, selectedBranchId]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN'
    }).format(amount / 100); // Convert from cents to pesos
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-MX', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const getDaysUntilExpiry = (membershipEnd: string) => {
    const today = new Date();
    const expiry = new Date(membershipEnd);
    const diffTime = expiry.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-spinner h-12 w-12"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-8">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-2">
              Bienvenido, {user?.name}! Aquí está el resumen de tu gimnasio.
            </p>
          </div>
          
          {/* Branch Selector for Super Admin */}
          {user?.role === 'super_admin' && branches.length > 0 && (
            <div className="flex items-center space-x-2">
              <Building className="h-5 w-5 text-gray-500" />
              <select
                value={selectedBranchId}
                onChange={(e) => setSelectedBranchId(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={!isOnline}
              >
                <option value="all">Todas las sedes</option>
                {branches.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        
        {/* Offline Warning Message */}
        {!isOnline && (
          <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <p className="text-sm text-yellow-800">
                Estás trabajando sin conexión. Algunos datos pueden no estar actualizados y las acciones se sincronizarán cuando recuperes la conexión.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-green-100 rounded-full">
              <Users className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Clientes Activos</p>
              <p className="text-2xl font-bold text-gray-900">{metrics.activeClients}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-blue-100 rounded-full">
              <DollarSign className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Ingresos Hoy</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(metrics.todayIncome)}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-red-100 rounded-full">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Morosos</p>
              <p className="text-2xl font-bold text-gray-900">{metrics.overdueClients}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-yellow-100 rounded-full">
              <Calendar className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Vencen esta Semana</p>
              <p className="text-2xl font-bold text-gray-900">{metrics.expiringThisWeek}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Clients */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Clientes Recientes</h3>
            <p className="card-description">Últimos clientes registrados</p>
          </div>
          <div className="card-content">
            {recentClients.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No hay clientes recientes</p>
            ) : (
              <div className="space-y-4">
                {recentClients.map((client) => (
                  <div key={client.id} className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="h-8 w-8 bg-primary-100 rounded-full flex items-center justify-center">
                        <span className="text-primary-600 text-xs font-medium">
                          {client.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-900">{client.name}</p>
                        <p className="text-xs text-gray-500">{client.email}</p>
                      </div>
                    </div>
                    <Link
                      to={`/clients/${client.id}`}
                      className="text-primary-600 hover:text-primary-800 text-sm font-medium"
                    >
                      Ver
                    </Link>
                  </div>
                ))}
              </div>
            )}
            <div className="card-footer pt-4">
              <Link
                to="/clients"
                className="btn btn-outline btn-sm w-full"
              >
                Ver todos los clientes
              </Link>
            </div>
          </div>
        </div>

        {/* Expiring Soon */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Membresías por Vencer</h3>
            <p className="card-description">Próximos vencimientos</p>
          </div>
          <div className="card-content">
            {expiringClients.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No hay membresías por vencer</p>
            ) : (
              <div className="space-y-4">
                {expiringClients.map((client) => {
                  const daysUntilExpiry = getDaysUntilExpiry(client.membershipEnd);
                  return (
                    <div key={client.id} className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="h-8 w-8 bg-yellow-100 rounded-full flex items-center justify-center">
                          <Calendar className="h-4 w-4 text-yellow-600" />
                        </div>
                        <div className="ml-3">
                          <p className="text-sm font-medium text-gray-900">{client.name}</p>
                          <p className="text-xs text-gray-500">
                            Vence: {formatDate(client.membershipEnd)}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`
                          inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold
                          ${daysUntilExpiry <= 3 ? 'badge-error' : 'badge-warning'}
                        `}>
                          {daysUntilExpiry} días
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            <div className="card-footer pt-4">
              <Link
                to="/reports/solvency"
                className="btn btn-outline btn-sm w-full"
              >
                Ver reporte de morosidad
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      {hasPermission('write_payments') && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Acciones Rápidas</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              to="/clients/new"
              className="card hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-center space-x-3">
                <UserCheck className="h-8 w-8 text-primary-600" />
                <div>
                  <p className="font-medium text-gray-900">Nuevo Cliente</p>
                  <p className="text-sm text-gray-600">Registrar un nuevo cliente</p>
                </div>
              </div>
            </Link>

            <Link
              to="/payments/new"
              className="card hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-center space-x-3">
                <CreditCard className="h-8 w-8 text-primary-600" />
                <div>
                  <p className="font-medium text-gray-900">Registrar Pago</p>
                  <p className="text-sm text-gray-600">Cobrar membresía</p>
                </div>
              </div>
            </Link>

            <Link
              to="/reports"
              className="card hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-center space-x-3">
                <TrendingUp className="h-8 w-8 text-primary-600" />
                <div>
                  <p className="font-medium text-gray-900">Ver Reportes</p>
                  <p className="text-sm text-gray-600">Análisis y estadísticas</p>
                </div>
              </div>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};
