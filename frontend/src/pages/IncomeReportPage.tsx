import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { Branch } from '@/types';
import toast from 'react-hot-toast';
import { ArrowLeft, DollarSign, RefreshCw } from 'lucide-react';
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
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || "";
  const [branches, setBranches] = useState<Branch[]>([]);
  const [filterBranch, setFilterBranch] = useState<string>('');
  const [dateRange, setDateRange] = useState<'7' | '30' | '90' | 'custom'>('30');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [dailyData, setDailyData] = useState<{ date: string; amount: number; paymentsCount: number }[]>([]);
  const [methodData, setMethodData] = useState<Record<string, { amount: number; percentage: number; count: number }>>({});
  const [totalPeriod, setTotalPeriod] = useState<number>(0);

  // Filtros aplicados (solo cambian al hacer clic en "Aplicar")
  const [appliedFilter, setAppliedFilter] = useState<{ range: string; start: string; end: string; branch: string }>({
    range: '30', start: '', end: '', branch: ''
  });

  useEffect(() => {
    loadBranches();
  }, [effectiveBusinessId]);

  useEffect(() => {
    if (effectiveBusinessId) loadReports();
  }, [effectiveBusinessId, appliedFilter]);

  const loadBranches = async () => {
    if (!effectiveBusinessId) return;
    try {
      const response = await apiService.getBranches(effectiveBusinessId);
      if (response.success && response.data) {
        setBranches(response.data);
      }
    } catch (error) {
      console.error('Error loading branches:', error);
    }
  };

  const getDateRange = (range: string, start: string, end: string) => {
    const now = new Date();
    now.setHours(23, 59, 59, 999);
    const endDateStr = now.toISOString().split('T')[0];

    if (range === 'custom' && start && end) {
      return { startDate: start, endDate: end };
    }

    const days = parseInt(range) || 30;
    const startDateObj = new Date();
    startDateObj.setDate(startDateObj.getDate() - days);
    startDateObj.setHours(0, 0, 0, 0);
    return {
      startDate: startDateObj.toISOString().split('T')[0],
      endDate: endDateStr
    };
  };

  const loadReports = async () => {
    if (!effectiveBusinessId) return;
    setLoading(true);
    try {
      const { startDate: s, endDate: e } = getDateRange(appliedFilter.range, appliedFilter.start, appliedFilter.end);
      const params: any = { startDate: s, endDate: e };
      if (appliedFilter.branch) params.branchId = appliedFilter.branch;

      const [dailyRes, methodRes] = await Promise.all([
        apiService.getIncomeDailyReport(s, e, params.branchId),
        apiService.getIncomeByMethodReport(s, e, params.branchId)
      ]);

      if (dailyRes.success && dailyRes.data) {
        setDailyData(dailyRes.data.daily || []);
        setTotalPeriod(dailyRes.data.totalPeriod || 0);
      }
      if (methodRes.success && methodRes.data) {
        setMethodData(methodRes.data as any);
      }
    } catch (err) {
      toast.error('Error cargando reportes');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFilters = () => {
    setAppliedFilter({
      range: dateRange,
      start: startDate,
      end: endDate,
      branch: filterBranch
    });
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100);
  };

  const formatDateLabel = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('es-VE', { day: '2-digit', month: 'short' });
  };

  // Determinar agrupación según rango
  const getGroupLabel = () => {
    const days = parseInt(dateRange) || (startDate && endDate
      ? Math.ceil((new Date(endDate).getTime() - new Date(startDate).getTime()) / 86400000)
      : 30);
    if (days <= 30) return 'diario';
    if (days <= 90) return 'semanal';
    return 'mensual';
  };

  const groupLabel = getGroupLabel();

  // Agrupar datos diarios según el tipo
  const groupedChartData = React.useMemo(() => {
    if (dailyData.length === 0) return [];
    if (groupLabel === 'diario') return dailyData.map(d => ({ ...d, label: formatDateLabel(d.date) }));

    const groups: Record<string, { amount: number; count: number }> = {};
    dailyData.forEach(d => {
      const dObj = new Date(d.date + 'T00:00:00');
      let key: string;
      if (groupLabel === 'semanal') {
        // Agrupar por inicio de semana (lunes)
        const day = dObj.getDay() || 7;
        dObj.setDate(dObj.getDate() - day + 1);
        key = dObj.toISOString().split('T')[0];
      } else {
        // Mensual
        key = `${dObj.getFullYear()}-${String(dObj.getMonth() + 1).padStart(2, '0')}`;
      }
      if (!groups[key]) groups[key] = { amount: 0, count: 0 };
      groups[key].amount += d.amount;
      groups[key].count += d.paymentsCount || 0;
    });

    return Object.entries(groups)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, v]) => ({
        date: key,
        label: groupLabel === 'mensual'
          ? new Date(key + '-01').toLocaleDateString('es-VE', { month: 'short', year: 'numeric' })
          : `${formatDateLabel(key)} —`,
        amount: v.amount,
        paymentsCount: v.count
      }));
  }, [dailyData, groupLabel]);

  const methodEntries = Object.entries(methodData).sort(([, a], [, b]) => b.amount - a.amount);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6">
      <Link to="/reports" className="btn btn-ghost btn-sm mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" /> Volver a Reportes
      </Link>

      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 mb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Reporte de Ingresos</h1>
          <p className="text-sm text-gray-600 mt-1">Análisis de ingresos por período y método de pago</p>
        </div>
      </div>

      {/* Filtros */}
      <div className="card mb-6">
        <div className="flex flex-col sm:flex-row gap-3 mb-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-700 mb-1">Sucursal</label>
            <select
              value={filterBranch}
              onChange={e => setFilterBranch(e.target.value)}
              className="input text-sm"
            >
              <option value="">Todas</option>
              {branches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Período</label>
            <select
              value={dateRange}
              onChange={e => { setDateRange(e.target.value as any); if (e.target.value !== 'custom') { setStartDate(''); setEndDate(''); }}}
              className="input text-sm w-32"
            >
              <option value="7">7 días</option>
              <option value="30">30 días</option>
              <option value="90">90 días</option>
              <option value="custom">Personalizado</option>
            </select>
          </div>
          {dateRange === 'custom' && (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Desde</label>
                <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="input text-sm w-36" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Hasta</label>
                <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="input text-sm w-36" />
              </div>
            </>
          )}
          <div className="flex items-end">
            <button onClick={handleApplyFilters} className="btn btn-primary text-sm h-10 px-4">
              <RefreshCw className="h-4 w-4 mr-1" /> Aplicar
            </button>
          </div>
        </div>
      </div>

      {dailyData.length === 0 && Object.keys(methodData).length === 0 ? (
        <div className="card text-center py-12">
          <DollarSign className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Sin datos de ingresos</h3>
          <p className="text-gray-600">No se encontraron pagos en el período seleccionado</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Ingresos ({groupLabel})</h3>
              <span className="text-xl font-bold text-primary-600">{formatCurrency(totalPeriod)}</span>
            </div>
            {groupedChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={groupedChartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" fontSize={10} interval={groupLabel === 'diario' ? 2 : 0} />
                  <YAxis tickFormatter={v => `$${(v / 100).toFixed(0)}`} fontSize={10} />
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Bar dataKey="amount" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-center py-8">No hay datos para el período</p>
            )}
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Por Método de Pago</h3>
            {methodEntries.length > 0 ? (
              <div className="flex flex-col lg:flex-row gap-6">
                <div className="lg:w-1/2">
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie
                        data={methodEntries.map(([k, v]) => ({ name: k, value: v.amount }))}
                        dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                        {methodEntries.map(([k]) => (
                          <Cell key={k} fill={METHOD_COLORS[k] || '#6b7280'} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => formatCurrency(v)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="lg:w-1/2">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-gray-500">
                        <th className="text-left py-1 font-medium">Método</th>
                        <th className="text-right py-1 font-medium">Pagos</th>
                        <th className="text-right py-1 font-medium">Monto</th>
                        <th className="text-right py-1 font-medium">%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {methodEntries.map(([method, data]) => (
                        <tr key={method} className="border-b border-gray-100">
                          <td className="py-2 flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full" style={{ background: METHOD_COLORS[method] || '#6b7280' }} />
                            <span className="capitalize">{method.replace('_', ' ')}</span>
                          </td>
                          <td className="py-2 text-right">{data.count}</td>
                          <td className="py-2 text-right font-medium">{formatCurrency(data.amount)}</td>
                          <td className="py-2 text-right text-gray-500">{data.percentage.toFixed(1)}%</td>
                        </tr>
                      ))}
                      <tr className="font-semibold border-t border-gray-300">
                        <td className="py-2">Total</td>
                        <td className="py-2 text-right">{methodEntries.reduce((s, [, d]) => s + d.count, 0)}</td>
                        <td className="py-2 text-right">{formatCurrency(totalPeriod)}</td>
                        <td className="py-2 text-right">100%</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No hay datos por método</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};