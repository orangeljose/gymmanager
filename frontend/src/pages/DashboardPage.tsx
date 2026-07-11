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
  Building,
  Percent
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAuth } from '@/hooks/useAuth';
import { useOffline } from '@/hooks/useOffline';
import { apiService } from '@/services/api';
import type { DashboardData, Client, Branch } from '@/types';

export const DashboardPage: React.FC = () => {
  const { user, hasPermission, selectedBusinessId } = useAuth();
  const { isOnline } = useOffline();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [recentClients, setRecentClients] = useState<Client[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selectedBranchId, setSelectedBranchId] = useState<string>('all');

  useEffect(() => {
    const loadBranches = async () => {
      if (!effectiveBusinessId) return;
      
      try {
        const branchesResponse = await apiService.getBranches(effectiveBusinessId);
        if (branchesResponse.success && branchesResponse.data) {
          setBranches(branchesResponse.data);
        }
      } catch (error) {
        console.error('Error loading branches:', error);
      }
    };

    loadBranches();
  }, [effectiveBusinessId]);

  useEffect(() => {
    const loadDashboardData = async () => {
      if (!effectiveBusinessId) return;

      try {
        setLoading(true);

        const branchParam = user?.role === 'super_admin' && selectedBranchId !== 'all'
          ? { branchId: selectedBranchId }
          : {};

        const [dashboardResponse, clientsResponse] = await Promise.all([
          apiService.getDashboard(branchParam),
          apiService.getClients({ 
            businessId: effectiveBusinessId, 
            limit: 100 
          })
        ]);

        if (dashboardResponse.success && dashboardResponse.data) {
          setDashboardData(dashboardResponse.data);
        }

        if (clientsResponse.success && clientsResponse.data) {
          setRecentClients(clientsResponse.data.slice(0, 5));
        }

      } catch (error) {
        console.error('Error loading dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, [effectiveBusinessId, selectedBranchId]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount / 100);
  };

  const formatShortCurrency = (amount: number) => {
    return `$${(amount / 100).toFixed(0)}`;
  };

  const formatChartDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-VE', { day: '2-digit', month: 'short' });
  };

  const formatTooltipDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-VE', { day: '2-digit', month: 'long', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-spinner h-12 w-12"></div>
      </div>
    );
  }

  const metrics = dashboardData || {
    activeClients: 0,
    todayIncome: 0,
    overdueClients: 0,
    expiringThisWeek: 0,
    incomeChart: [],
    topPayingClients: [],
    retentionRate: 0
  };

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
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
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
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
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
              <div className="flex items-center gap-2">
                <p className="text-2xl font-bold text-gray-900">{metrics.expiringThisWeek}</p>
                {metrics.expiringThisWeek > 0 && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-red-500 text-white">
                    {metrics.expiringThisWeek}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-purple-100 rounded-full">
              <Percent className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Retención</p>
              <p className="text-2xl font-bold text-gray-900">{metrics.retentionRate}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Income Chart */}
      <div className="card mb-8">
        <div className="card-header">
          <h3 className="card-title">Ingresos Últimos 30 Días</h3>
          <p className="card-description">Total diario de pagos registrados</p>
        </div>
        <div className="card-content">
          {metrics.incomeChart.length === 0 || metrics.incomeChart.every(p => p.amount === 0) ? (
            <p className="text-gray-500 text-center py-12">No income data for this period</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={metrics.incomeChart} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={formatChartDate}
                  interval="preserveStartEnd"
                />
                <YAxis 
                  tick={{ fontSize: 11 }}
                  tickFormatter={formatShortCurrency}
                />
                <Tooltip 
                  formatter={(value: number) => [formatCurrency(value), 'Ingresos']}
                  labelFormatter={formatTooltipDate}
                />
                <Bar dataKey="amount" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Top 5 Clients */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Top Clientes</h3>
            <p className="card-description">Mayor cantidad de pagos (30 días)</p>
          </div>
          <div className="card-content">
            {metrics.topPayingClients.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Sin datos de pagos recientes</p>
            ) : (
              <div className="space-y-3">
                {metrics.topPayingClients.map((client, index) => (
                  <div key={client.clientId} className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold ${
                        index === 0 ? 'bg-yellow-100 text-yellow-700' :
                        index === 1 ? 'bg-gray-200 text-gray-600' :
                        index === 2 ? 'bg-orange-100 text-orange-700' :
                        'bg-gray-100 text-gray-500'
                      }`}>
                        {index + 1}
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-900">{client.clientName}</p>
                      </div>
                    </div>
                    <span className="text-sm font-semibold text-gray-900">
                      {client.paymentCount} pagos
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

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
