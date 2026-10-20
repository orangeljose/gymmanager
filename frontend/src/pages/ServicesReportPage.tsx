import React, { useCallback, useEffect, useState } from 'react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from 'recharts';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { ServiceReport, ExpenseCategory } from '@/types';
import { formatDollars } from '@/components/ProductForm';
import { EXPENSE_CATEGORY_META, EXPENSE_CATEGORIES } from '@/components/ExpenseForm';
import {
  DollarSign, Receipt, AlertTriangle, BarChart3,
} from 'lucide-react';

const daysAgo = (n: number) =>
  new Date(Date.now() - n * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
const todayIso = () => new Date().toISOString().slice(0, 10);

export const ServicesReportPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';

  const [startDate, setStartDate] = useState(daysAgo(29));
  const [endDate, setEndDate] = useState(todayIso());
  const [report, setReport] = useState<ServiceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scoped = user?.role === 'super_admin' && effectiveBusinessId
    ? { businessId: effectiveBusinessId }
    : {};

  const loadReport = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.getExpensesReport(
        startDate || undefined,
        endDate || undefined,
        undefined,
        scoped.businessId,
      );
      if (response.success) setReport(response.data);
    } catch (err: any) {
      setError(err.message || 'Error cargando reporte');
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, user?.role, effectiveBusinessId]);

  useEffect(() => { loadReport(); }, [loadReport]);

  const dailyData = (report?.daily ?? []).map((d) => ({
    name: d.date,
    Total: d.totalCents / 100,
  }));

  const categoryEntries = (EXPENSE_CATEGORIES as ExpenseCategory[])
    .map((cat) => ({ cat, amount: report?.byCategory?.[cat] ?? 0 }))
    .filter((e) => e.amount > 0)
    .sort((a, b) => b.amount - a.amount);

  const cards = [
    { label: 'Total', value: formatDollars(report?.totalCents ?? 0), icon: DollarSign, color: 'text-green-600 bg-green-50' },
    { label: 'N° servicios', value: String(report?.count ?? 0), icon: Receipt, color: 'text-primary-600 bg-primary-50' },
  ];

  return (
    <div className="p-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reporte de Servicios</h1>
          <p className="text-gray-600 mt-1">Egresos y servicios por período y categoría</p>
        </div>
      </div>

      {/* Date range */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="input"
            />
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {cards.map((card) => (
          <div key={card.label} className="card p-4 flex items-center">
            <div className={`p-2 rounded-lg ${card.color}`}>
              <card.icon className="h-5 w-5" />
            </div>
            <div className="ml-3">
              <p className="text-2xl font-bold text-gray-900">{card.value}</p>
              <p className="text-xs text-gray-500">{card.label}</p>
            </div>
          </div>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="loading-spinner h-10 w-10"></div>
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No se pudo cargar el reporte</h3>
          <p className="text-gray-600">{error}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Chart by day */}
          {dailyData.length === 0 ? (
            <div className="card text-center py-12">
              <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Sin egresos en el período</h3>
              <p className="text-gray-600">
                No hay servicios registrados en el rango seleccionado.
              </p>
            </div>
          ) : (
            <div className="card">
              <h2 className="text-sm font-semibold text-gray-700 mb-4">Egresos por día (USD)</h2>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dailyData} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="Total" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Breakdown by category */}
          {categoryEntries.length > 0 && (
            <div className="card">
              <h2 className="text-sm font-semibold text-gray-700 mb-4">Por categoría</h2>
              <div className="space-y-2">
                {categoryEntries.map(({ cat, amount }) => {
                  const meta = EXPENSE_CATEGORY_META[cat];
                  return (
                    <div key={cat} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                      <span className={`badge ${meta.badge}`}>{meta.label}</span>
                      <span className="font-semibold text-gray-900">{formatDollars(amount)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
