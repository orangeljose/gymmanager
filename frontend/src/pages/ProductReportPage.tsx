import React, { useCallback, useEffect, useState } from 'react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { ProductReport } from '@/types';
import { formatDollars } from '@/components/ProductForm';
import {
  TrendingUp, TrendingDown, BarChart3, AlertTriangle,
} from 'lucide-react';

const daysAgo = (n: number) =>
  new Date(Date.now() - n * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
const todayIso = () => new Date().toISOString().slice(0, 10);

const formatNet = (cents: number) =>
  `${cents < 0 ? '-' : ''}$${(Math.abs(cents) / 100).toFixed(2)}`;

export const ProductReportPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';

  const [reportStart, setReportStart] = useState(daysAgo(29));
  const [reportEnd, setReportEnd] = useState(todayIso());
  const [report, setReport] = useState<ProductReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  const scoped = user?.role === 'super_admin' && effectiveBusinessId
    ? { businessId: effectiveBusinessId }
    : {};

  const loadReport = useCallback(async () => {
    try {
      setReportLoading(true);
      setReportError(null);
      const response = await apiService.getProductsReport(
        reportStart || undefined,
        reportEnd || undefined,
        undefined,
        scoped.businessId,
      );
      if (response.success) setReport(response.data);
    } catch (err: any) {
      setReportError(err.message || 'Error cargando reporte');
    } finally {
      setReportLoading(false);
    }
  }, [reportStart, reportEnd, user?.role, effectiveBusinessId]);

  useEffect(() => { loadReport(); }, [loadReport]);

  const reportCards = [
    { label: 'Ventas totales', value: formatDollars(report?.sales.totalCents ?? 0), icon: TrendingUp, color: 'text-green-600 bg-green-50' },
    { label: 'Compras totales', value: formatDollars(report?.purchases.totalCents ?? 0), icon: TrendingDown, color: 'text-red-600 bg-red-50' },
    { label: 'Neto', value: formatNet(report?.net ?? 0), icon: BarChart3, color: 'text-primary-600 bg-primary-50' },
  ];

  const reportChartData = (report?.daily ?? []).map((d) => ({
    name: d.date,
    Ventas: d.salesCents / 100,
    Compras: d.purchasesCents / 100,
  }));

  return (
    <div className="p-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reporte de Mercancía</h1>
          <p className="text-gray-600 mt-1">Ventas (caja) vs compras de mercancía por período</p>
        </div>
      </div>

      {/* Date range */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
            <input
              type="date"
              value={reportStart}
              onChange={(e) => setReportStart(e.target.value)}
              className="input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
            <input
              type="date"
              value={reportEnd}
              onChange={(e) => setReportEnd(e.target.value)}
              className="input"
            />
          </div>
        </div>
      </div>

      {/* Report cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        {reportCards.map((card) => (
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

      {/* Chart */}
      {reportLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="loading-spinner h-10 w-10"></div>
        </div>
      ) : reportError ? (
        <div className="card text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No se pudo cargar el reporte</h3>
          <p className="text-gray-600">{reportError}</p>
        </div>
      ) : reportChartData.length === 0 ? (
        <div className="card text-center py-12">
          <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Sin movimientos en el período</h3>
          <p className="text-gray-600">
            No hay ventas ni compras registradas en el rango seleccionado.
          </p>
        </div>
      ) : (
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Ventas vs compras por día (USD)</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={reportChartData} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="Ventas" fill="#16a34a" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Compras" fill="#dc2626" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};
