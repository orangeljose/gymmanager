import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import { MachineForm, MACHINE_STATUS_META, MACHINE_CATEGORY_LABELS } from '@/components/MachineForm';
import type { Machine, MachineCategory, MachineFilters, MachineStatus, MachinesSummary } from '@/types';
import {
  Plus, Search, Dumbbell, AlertTriangle, Wrench, CircleSlash,
  CheckCircle2, CalendarClock, ChevronRight
} from 'lucide-react';

const STATUS_ICON: Record<MachineStatus, React.ElementType> = {
  operational: CheckCircle2,
  maintenance: Wrench,
  out_of_service: CircleSlash,
};

export const MachinesPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';
  const canWrite = !!user && ['super_admin', 'admin', 'branch_admin'].includes(user.role);

  const [machines, setMachines] = useState<Machine[]>([]);
  const [summary, setSummary] = useState<MachinesSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [filters, setFilters] = useState<MachineFilters>({ category: '', status: '', search: '' });

  const loadSummary = useCallback(async () => {
    try {
      const response = await apiService.getMachinesSummary(
        user?.role === 'super_admin' && effectiveBusinessId ? { businessId: effectiveBusinessId } : {}
      );
      if (response.success) setSummary(response.data);
    } catch {
      /* el resumen es accesorio; no bloquea la lista */
    }
  }, [user?.role, effectiveBusinessId]);

  const loadMachines = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.getMachines({
        ...filters,
        businessId: user?.role === 'super_admin' ? effectiveBusinessId : undefined,
        limit: 100,
      });
      if (response.success) setMachines(response.data);
    } catch (err: any) {
      setError(err.message || 'Error cargando máquinas');
    } finally {
      setLoading(false);
    }
  }, [filters, user?.role, effectiveBusinessId]);

  useEffect(() => {
    loadMachines();
  }, [loadMachines]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const statusCount = (s: MachineStatus) => summary?.byStatus?.[s] ?? 0;

  const isUpcoming = (machine: Machine) => {
    if (!machine.nextMaintenanceDate) return false;
    const horizon = new Date();
    horizon.setDate(horizon.getDate() + 7);
    return machine.nextMaintenanceDate <= horizon.toISOString().slice(0, 10);
  };

  const cards = [
    { label: 'Total', value: summary?.total ?? machines.length, icon: Dumbbell, color: 'text-primary-600 bg-primary-50' },
    { label: 'Operativas', value: statusCount('operational'), icon: CheckCircle2, color: 'text-green-600 bg-green-50' },
    { label: 'En mantenimiento', value: statusCount('maintenance'), icon: Wrench, color: 'text-yellow-600 bg-yellow-50' },
    { label: 'Fuera de servicio', value: statusCount('out_of_service'), icon: CircleSlash, color: 'text-red-600 bg-red-50' },
    { label: 'Próximos (7d)', value: summary?.upcomingMaintenance?.length ?? 0, icon: CalendarClock, color: 'text-blue-600 bg-blue-50' },
  ];

  return (
    <div className="p-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Máquinas</h1>
          <p className="text-gray-600 mt-1">Inventario de equipos y seguimiento de mantenimiento</p>
        </div>
        {canWrite && (
          <button onClick={() => setShowForm(true)} className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Nueva Máquina
          </button>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
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

      {/* Filters */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="relative lg:col-span-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              className="input pl-9"
              placeholder="Buscar por nombre, marca o modelo..."
            />
          </div>
          <select
            value={filters.category}
            onChange={(e) => setFilters((prev) => ({ ...prev, category: e.target.value as MachineCategory | '' }))}
            className="input"
          >
            <option value="">Todas las categorías</option>
            {(Object.keys(MACHINE_CATEGORY_LABELS) as MachineCategory[]).map((c) => (
              <option key={c} value={c}>{MACHINE_CATEGORY_LABELS[c]}</option>
            ))}
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value as MachineStatus | '' }))}
            className="input"
          >
            <option value="">Todos los estados</option>
            {(Object.keys(MACHINE_STATUS_META) as MachineStatus[]).map((s) => (
              <option key={s} value={s}>{MACHINE_STATUS_META[s].label}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="loading-spinner h-10 w-10"></div>
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No se pudieron cargar las máquinas</h3>
          <p className="text-gray-600">{error}</p>
        </div>
      ) : machines.length === 0 ? (
        <div className="card text-center py-12">
          <Dumbbell className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay máquinas registradas</h3>
          <p className="text-gray-600 mb-6">Registra los equipos del gimnasio para llevar su inventario y mantenimiento.</p>
          {canWrite && (
            <button onClick={() => setShowForm(true)} className="btn btn-primary">
              <Plus className="h-4 w-4 mr-2" />
              Agregar Máquina
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {machines.map((machine) => {
            const meta = MACHINE_STATUS_META[machine.status] || MACHINE_STATUS_META.operational;
            const StatusIcon = STATUS_ICON[machine.status] || CheckCircle2;
            const upcoming = isUpcoming(machine);
            return (
              <Link
                key={machine.id}
                to={`/machines/${machine.id}`}
                className="card relative hover:shadow-lg transition-shadow border-l-4 border-l-primary-500 block"
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center min-w-0">
                    <div className="p-2 rounded-lg bg-primary-50 text-primary-600">
                      <Dumbbell className="h-5 w-5" />
                    </div>
                    <div className="ml-3 min-w-0">
                      <h3 className="font-medium text-gray-900 truncate">{machine.name}</h3>
                      <p className="text-sm text-gray-500 truncate">
                        {[machine.brand, machine.model].filter(Boolean).join(' · ') || MACHINE_CATEGORY_LABELS[machine.category]}
                      </p>
                    </div>
                  </div>
                  <span className={`badge ${meta.badge} whitespace-nowrap`}>
                    <span className={`mr-1.5 h-2 w-2 rounded-full ${meta.dot}`} />
                    {meta.label}
                  </span>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="inline-flex items-center text-gray-500">
                    <StatusIcon className="h-4 w-4 mr-1 text-gray-400" />
                    {MACHINE_CATEGORY_LABELS[machine.category]}
                  </span>
                  {machine.nextMaintenanceDate && (
                    <span className={`inline-flex items-center ${upcoming ? 'text-yellow-600 font-medium' : 'text-gray-500'}`}>
                      <CalendarClock className="h-4 w-4 mr-1" />
                      {machine.nextMaintenanceDate}
                    </span>
                  )}
                </div>

                <ChevronRight className="absolute right-3 bottom-3 h-4 w-4 text-gray-300" />
              </Link>
            );
          })}
        </div>
      )}

      <MachineForm
        open={showForm}
        businessId={effectiveBusinessId}
        onClose={() => setShowForm(false)}
        onSaved={() => {
          loadMachines();
          loadSummary();
        }}
      />
    </div>
  );
};
