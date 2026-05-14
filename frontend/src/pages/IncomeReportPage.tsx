import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { Branch } from '@/types';
import toast from 'react-hot-toast';
import { ArrowLeft, DollarSign, Calendar, TrendingUp, CreditCard } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const METHOD_COLORS: Record<string, string> = {
  cash: '#10b981',
  card: '#6366f1',
  transfer: '#f59e0b',
  zelle: '#ec4899',
  pago_movil: '#8b5cf6',
  other: '#6b7280'
};

export const IncomeReportPage: React.FC = () => {
  const { user } = useAuth();
  const [branches, setBranches] = useState<Branch[]>([]);
  const [filterBranch, setFilterBranch] = useState<string>('');
  const [dateRange, setDateRange] = useState<'7' | '30' | '90' | 'custom'>('30');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [dailyData, setDailyData] = useState<{ date: string; amount: number; paymentsCount: number }[]>([]);
  const [methodData, setMethodData] = useState<Record<string, { amount: number; percentage: number; count: number }>>({});
  const [totalPeriod, setTotalPeriod] = useState<number>(0);

  useEffect(() => {
    loadBranches();
  }, [user?.businessId]);

  useEffect(() => {
    loadReports();
  }, [user?.businessId, filterBranch, dateRange, startDate, endDate]);

  const loadBranches = async () => {
    if (!user?.businessId) return;
    try {
      const response = await apiService.getBranches(user.businessId);
      if (response.success && response.data) {
        setBranches(response.data);
      }
    } catch (error) {
      console.error('Error loading branches:', error);
    }
  };

  const getDateRange = () => {
    const end = new Date();
    const start = new Date();
    end.setHours(23, 59, 59, 999);

    if (dateRange === 'custom' && startDate && endDate) {
      return { startDate, endDate };
    }

    if (dateRange === '7') {
      start.setDate(start.getDate() - 7);
    } else if (dateRange === '30') {
      start.setDate(start.getDate() - 30);
    } else if (dateRange === '90') {
      start.setDate(start.getDate() - 90);
    }
    start.setHours(0, 0, 0, 0);

    return {
      startDate: start.toISOString().split('T')[0],
      endDate: end.toISOString().split('T')[0]
    };
  };

  const loadReports = async () => {
    if (!user?.businessId) return;
    try {
      setLoading(true);
      const { startDate: sDate, endDate: eDate } = getDateRange();

      const [dailyRes, methodRes] = await Promise.all([
        apiService.getIncomeDailyReport(sDate, eDate, filterBranch || undefined),
        apiService.getIncomeByMethodReport(sDate, eDate, filterBranch || undefined)
      ]);

      if (dailyRes.success && dailyRes.data) {
        setDailyData(dailyRes.data.daily || []);
        setTotalPeriod(dailyRes.data.totalPeriod || 0);
      }
      if (methodRes.success && methodRes.data) {
        setMethodData(methodRes.data);
      }
    } catch (error) {
      toast.error('Error cargando reporte');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(cents / 100);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('es-VE', {
      day: '2-digit',
      month: 'short'
    });
  };

  const totalPayments = Object.values(methodData).reduce((acc, m) => acc + m.count, 0);

  const pieChartData = Object.entries(methodData)
    .filter(([_, data]) => data.count > 0)
    .map(([method, data]) => ({
      name: method.charAt(0).toUpperCase() + method.slice(1).replace('_', ' '),
      value: data.amount,
      count: data.count,
      color: METHOD_COLORS[method] || '#6b7280'
    }));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <Link to="/reports" className="btn btn-ghost btn-sm mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" />
        Volver a Reportes
      </Link>

      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reporte de Ingresos</h1>
          <p className="text-gray-600 mt-1">Resumen de pagos por período</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-500">Total del período</p>
          <p className="text-2xl font-bold text-green-600">{formatCurrency(totalPeriod)}</p>
        </div>
      </div>

      <div className="card mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <Calendar className="h-4 w-4 inline mr-1" />
              Período
            </label>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value as any)}
              className="input w-full"
            >
              <option value="7">Últimos 7 días</option>
              <option value="30">Últimos 30 días</option>
              <option value="90">Últimos 90 días</option>
              <option value="custom">Personalizado</option>
            </select>
          </div>
          {dateRange === 'custom' && (
            <>
              <div className="w-full sm:w-40">
                <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="input w-full"
                />
              </div>
              <div className="w-full sm:w-40">
                <label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="input w-full"
                />
              </div>
            </>
          )}
          <div className="w-full sm:w-48">
            <label className="block text-sm font-medium text-gray-700 mb-1">Sucursal</label>
            <select
              value={filterBranch}
              onChange={(e) => setFilterBranch(e.target.value)}
              className="input w-full"
            >
              <option value="">Todas</option>
              {branches.map((branch) => (
                <option key={branch.id} value={branch.id}>{branch.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {dailyData.length === 0 && Object.keys(methodData).length === 0 ? (
        <div className="card text-center py-12">
          <DollarSign className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Sin datos en este período</h3>
          <p className="text-gray-600">No hay pagos registrados para el período seleccionado</p>
        </div>
      ) : (
        <div className="space-y-6">
          {dailyData.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <TrendingUp className="h-5 w-5 mr-2 text-green-600" />
                Ingresos Diarios
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dailyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={formatDate}
                      tick={{ fontSize: 12 }}
                      stroke="#9ca3af"
                    />
                    <YAxis
                      tickFormatter={(value) => `$${(value / 100).toFixed(0)}`}
                      tick={{ fontSize: 12 }}
                      stroke="#9ca3af"
                    />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      labelFormatter={formatDate}
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                    />
                    <Bar dataKey="amount" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {pieChartData.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <CreditCard className="h-5 w-5 mr-2 text-purple-600" />
                Distribución por Método de Pago
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieChartData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        innerRadius={50}
                        paddingAngle={2}
                      >
                        {pieChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex flex-col justify-center">
                  <div className="grid grid-cols-2 gap-3">
                    {pieChartData.map((item) => (
                      <div key={item.name} className="flex items-center p-2 bg-gray-50 rounded-lg">
                        <div
                          className="w-3 h-3 rounded-full mr-2"
                          style={{ backgroundColor: item.color }}
                        />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900">{item.name}</p>
                          <p className="text-xs text-gray-500">
                            {formatCurrency(item.value)} ({item.count} pagos)
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 pt-4 border-t">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Total de pagos:</span>
                      <span className="font-semibold">{totalPayments}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};