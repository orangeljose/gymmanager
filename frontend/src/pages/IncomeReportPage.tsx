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
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Ingresos Diarios</h3>
            <div className="text-2xl font-bold text-primary-600 mb-4">{formatCurrency(totalPeriod)}</div>
            {dailyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={dailyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tickFormatter={formatDateLabel} fontSize={11} />
                  <YAxis tickFormatter={v => `$${(v / 100).toFixed(0)}`} fontSize={11} />
                  <Tooltip formatter={(v: number) => formatCurrency(v)} labelFormatter={formatDateLabel} />
                  <Bar dataKey="amount" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-center py-8">No hay datos diarios</p>
            )}
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Por Método de Pago</h3>
            {Object.keys(methodData).length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={Object.entries(methodData).map(([k, v]) => ({ name: k, value: v.amount }))}
                    dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {Object.keys(methodData).map(k => (
                      <Cell key={k} fill={METHOD_COLORS[k] || '#6b7280'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-center py-8">No hay datos por método</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};