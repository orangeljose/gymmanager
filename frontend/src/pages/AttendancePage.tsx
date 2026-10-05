import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  UserCheck,
  Clock,
  QrCode,
  Fingerprint,
  CalendarCheck,
  CalendarDays,
  TrendingUp,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { Client, AttendanceRecord, AttendanceStats, AttendanceMethod } from '@/types';

const PRIMARY_600 = '#D43506';

const METHOD_LABELS: Record<AttendanceMethod, string> = {
  manual: 'Manual',
  qr: 'QR',
  biometric: 'Biométrico',
};

const methodBadgeClasses: Record<AttendanceMethod, string> = {
  manual: 'bg-gray-100 text-gray-700',
  qr: 'bg-blue-100 text-blue-700',
  biometric: 'bg-green-100 text-green-700',
};

const MethodIcon: React.FC<{ method: AttendanceMethod; className?: string }> = ({ method, className }) => {
  if (method === 'qr') return <QrCode className={className} />;
  if (method === 'biometric') return <Fingerprint className={className} />;
  return <UserCheck className={className} />;
};

const shortDate = (d: string) => `${d.slice(8, 10)}/${d.slice(5, 7)}`;

const formatTime = (iso: string) => {
  if (!iso) return '--:--';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '--:--';
  return date.toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' });
};

export const AttendancePage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';

  const [searchTerm, setSearchTerm] = useState('');
  const [clients, setClients] = useState<Client[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [registering, setRegistering] = useState(false);

  const [stats, setStats] = useState<AttendanceStats | null>(null);
  const [todayRecords, setTodayRecords] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const searchClients = useCallback(async (term: string) => {
    if (!term || term.length < 2) {
      setClients([]);
      setShowDropdown(false);
      return;
    }
    setSearching(true);
    try {
      const response = await apiService.getClients({
        search: term,
        limit: 10,
        businessId: effectiveBusinessId || undefined,
      });
      if (response.success && response.data) {
        setClients(response.data);
        setShowDropdown(response.data.length > 0);
      }
    } catch (err) {
      console.error('Error searching clients:', err);
      setClients([]);
    } finally {
      setSearching(false);
    }
  }, [effectiveBusinessId]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => searchClients(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm, searchClients]);

  const loadToday = useCallback(async () => {
    try {
      const response = await apiService.getAttendance({
        businessId: effectiveBusinessId || undefined,
        limit: 50,
      });
      setTodayRecords(response.data || []);
    } catch (err) {
      console.error('Error loading attendance:', err);
    }
  }, [effectiveBusinessId]);

  const loadStats = useCallback(async () => {
    try {
      const response = await apiService.getAttendanceStats({
        businessId: effectiveBusinessId || undefined,
      });
      setStats(response.data || null);
    } catch (err) {
      console.error('Error loading attendance stats:', err);
    }
  }, [effectiveBusinessId]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([loadToday(), loadStats()]);
    setLoading(false);
  }, [loadToday, loadStats]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleSelectClient = (client: Client) => {
    setSelectedClient(client);
    setSearchTerm('');
    setClients([]);
    setShowDropdown(false);
  };

  const handleRegister = async () => {
    if (!selectedClient) return;
    setRegistering(true);
    try {
      const response = await apiService.registerAttendance({
        clientId: selectedClient.id,
        method: 'manual',
      });
      if (response.data?.alreadyCheckedIn) {
        toast('Ya registrado hoy', { icon: '⚠️' });
      } else {
        toast.success(`Asistencia registrada: ${selectedClient.name}`);
      }
      setSelectedClient(null);
      await Promise.all([loadToday(), loadStats()]);
    } catch (err: any) {
      toast.error(err?.message || 'Error al registrar la asistencia');
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Asistencia</h1>
        <p className="text-gray-600 mt-1">
          Registra el ingreso de clientes y consulta las estadísticas del día
        </p>
      </div>

      {/* Check-in */}
      <div className="card mb-6">
        <div className="card-header">
          <h3 className="card-title flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-primary-600" />
            Registrar Asistencia
          </h3>
          <p className="card-description">
            Busca al cliente y confirma su ingreso. Un cliente solo puede registrar una asistencia por día.
          </p>
        </div>
        <div className="card-content">
          {!selectedClient ? (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onFocus={() => { if (clients.length > 0) setShowDropdown(true); }}
                placeholder="Buscar cliente por nombre, email o teléfono..."
                className="input pl-10"
                autoFocus
              />
              {searching && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="loading-spinner h-4 w-4" />
                </div>
              )}

              {showDropdown && clients.length > 0 && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {clients.map((client) => (
                    <button
                      key={client.id}
                      type="button"
                      onClick={() => handleSelectClient(client)}
                      className="w-full text-left px-4 py-3 hover:bg-primary-50 border-b border-gray-100 last:border-b-0 flex items-center justify-between"
                    >
                      <div>
                        <p className="font-medium text-gray-900">{client.name}</p>
                        <p className="text-sm text-gray-500">{client.email}</p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        client.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {client.status === 'active' ? 'Al día' : 'Vencido'}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {!searching && searchTerm.length >= 2 && clients.length === 0 && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg p-4 text-center text-gray-500">
                  No se encontraron clientes
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-primary-50 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <div className="h-11 w-11 rounded-full bg-primary-600 flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-lg font-semibold">
                    {selectedClient.name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="font-semibold text-gray-900">{selectedClient.name}</p>
                  <p className="text-sm text-gray-600">{selectedClient.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedClient(null)}
                  className="btn btn-ghost btn-sm text-gray-600"
                  disabled={registering}
                >
                  Cambiar
                </button>
                <button
                  onClick={handleRegister}
                  disabled={registering}
                  className="btn btn-primary inline-flex items-center gap-2"
                >
                  <UserCheck className="h-5 w-5" />
                  {registering ? 'Registrando...' : 'Registrar Asistencia'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <StatCard
          label="Hoy"
          value={stats?.today ?? 0}
          icon={<CalendarCheck className="h-6 w-6" />}
          accent="bg-primary-600"
        />
        <StatCard
          label="Esta semana"
          value={stats?.week ?? 0}
          icon={<TrendingUp className="h-6 w-6" />}
          accent="bg-blue-500"
        />
        <StatCard
          label="Este mes"
          value={stats?.month ?? 0}
          icon={<CalendarDays className="h-6 w-6" />}
          accent="bg-green-600"
        />
      </div>

      {/* 7-day chart */}
      <div className="card mb-6">
        <div className="card-header">
          <h3 className="card-title">Asistencias últimos 7 días</h3>
        </div>
        <div className="card-content">
          <div style={{ width: '100%', height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.series7 ?? []} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                <XAxis dataKey="date" tickFormatter={shortDate} fontSize={12} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  labelFormatter={(label: string) => shortDate(label)}
                  formatter={(value: number) => [value, 'Asistencias']}
                  cursor={{ fill: 'rgba(212, 53, 6, 0.06)' }}
                />
                <Bar dataKey="count" fill={PRIMARY_600} radius={[4, 4, 0, 0]} name="Asistencias" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Today's list */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="card-title">Check-ins de hoy</h3>
          <span className="badge badge-info">{todayRecords.length}</span>
        </div>
        <div className="card-content">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="loading-spinner h-8 w-8" />
            </div>
          ) : todayRecords.length === 0 ? (
            <div className="text-center py-10">
              <UserCheck className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-600 mb-1">Sin asistencias todavía</h3>
              <p className="text-gray-500">Registra el primer check-in del día.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {todayRecords.map((record) => (
                <li key={record.id} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-9 w-9 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                      <span className="text-primary-700 font-medium">
                        {(record.clientName || '?').charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900 truncate">{record.clientName}</p>
                      <p className="text-xs text-gray-500">
                        Registrado por {record.registeredByName || '—'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${methodBadgeClasses[record.method] || methodBadgeClasses.manual}`}>
                      <MethodIcon method={record.method} className="h-3 w-3" />
                      {METHOD_LABELS[record.method] || record.method}
                    </span>
                    <span className="inline-flex items-center gap-1 text-sm text-gray-600 w-16 justify-end">
                      <Clock className="h-4 w-4 text-gray-400" />
                      {formatTime(record.checkInAt)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

interface StatCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  accent: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon, accent }) => (
  <div className="card">
    <div className="card-content flex items-center gap-4">
      <div className={`h-12 w-12 rounded-lg flex items-center justify-center text-white ${accent}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  </div>
);

export default AttendancePage;
