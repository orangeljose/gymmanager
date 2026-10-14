import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from 'recharts';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { AttendanceReport } from '@/types';
import {
  ArrowLeft, Users, CalendarDays, TrendingUp, Trophy, BarChart3, AlertTriangle,
} from 'lucide-react';

const PRIMARY_600 = '#D43506';

const daysAgo = (n: number) =>
  new Date(Date.now() - n * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
const todayIso = () => new Date().toISOString().slice(0, 10);

const shortDate = (d: string) => `${d.slice(8, 10)}/${d.slice(5, 7)}`;

const QUICK_RANGES = [
  { label: '7 días', days: 7 },
  { label: '30 días', days: 30 },
  { label: '90 días', days: 90 },
];

const formatAvg = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

export const AttendanceReportPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';

  const [startDate, setStartDate] = useState(daysAgo(29));
  const [endDate, setEndDate] = useState(todayIso());
  const [report, setReport] = useState<AttendanceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scoped = user?.role === 'super_admin' && effectiveBusinessId
    ? { businessId: effectiveBusinessId }
    : {};

  const loadReport = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.getAttendanceReport(
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

  const applyQuickRange = (days: number) => {
    setEndDate(todayIso());
    setStartDate(daysAgo(days - 1));
  };

  const chartData = (report?.daily ?? []).map((d) => ({
    date: d.date,
    Asistencias: d.count,
  }));

  const peak = report?.peakDay ?? null;

  const cards = [
    {
      label: 'Total asistencias',
      value: String(report?.total ?? 0),
      sublabel: undefined,
      icon: Users,
      color: 'text-primary-600 bg-primary-50',
    },
    {
      label: 'Promedio diario',
      value: formatAvg(report?.avgDaily ?? 0),
      sublabel: undefined,
      icon: CalendarDays,
      color: 'text-blue-600 bg-blue-50',
    },
    {
      label: 'Día pico',
      value: peak ? String(peak.count) : '—',
      sublabel: peak ? shortDate(peak.date) : undefined,
      icon: TrendingUp,
      color: 'text-green-600 bg-green-50',
    },
  ];

  return (
    <div className="p-6">
      <Link to="/reports" className="btn btn-ghost btn-sm mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" /> Volver a Reportes
      </Link>

      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reporte de Asistencias</h1>
          <p className="text-gray-600 mt-1">Asistencias por período y top de asistentes</p>
        </div>
      </div>

      {/* Date range + quick selector */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
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
        <div className="flex items-center gap-2">
          {QUICK_RANGES.map((range) => (
            <button
              key={range.days}
              type="button"
              onClick={() => applyQuickRange(range.days)}
              className="btn btn-ghost btn-sm text-gray-600"
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        {cards.map((card) => (
          <div key={card.label} className="card p-4 flex items-center">
            <div className={`p-2 rounded-lg ${card.color}`}>
              <card.icon className="h-5 w-5" />
            </div>
            <div className="ml-3">
              <p className="text-2xl font-bold text-gray-900">{card.value}</p>
              <p className="text-xs text-gray-500">
                {card.label}
                {card.sublabel ? ` · ${card.sublabel}` : ''}
              </p>
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
          {chartData.length === 0 ? (
            <div className="card text-center py-12">
              <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Sin asistencias en el período</h3>
              <p className="text-gray-600">
                No hay check-ins registrados en el rango seleccionado.
              </p>
            </div>
          ) : (
            <div className="card">
              <h2 className="text-sm font-semibold text-gray-700 mb-4">Asistencias por día</h2>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={shortDate}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip
                      labelFormatter={(label: string) => shortDate(label)}
                      formatter={(value: number) => [value, 'Asistencias']}
                      cursor={{ fill: 'rgba(212, 53, 6, 0.06)' }}
                    />
                    <Bar dataKey="Asistencias" fill={PRIMARY_600} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Top attendees */}
          <div className="card">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-500" /> Top asistentes
            </h2>
            {(report?.topAttendees ?? []).length === 0 ? (
              <p className="text-gray-500 py-4 text-center">Sin datos en el período</p>
            ) : (
              <ul className="divide-y divide-gray-100">
                {(report?.topAttendees ?? []).map((attendee, idx) => (
                  <li key={attendee.clientId} className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-700 text-xs font-semibold flex items-center justify-center">
                        {idx + 1}
                      </span>
                      <span className="font-medium text-gray-900 truncate">{attendee.clientName}</span>
                    </div>
                    <span className="badge badge-info">{attendee.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AttendanceReportPage;
