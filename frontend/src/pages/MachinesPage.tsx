import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import {
  MachineForm, MACHINE_STATUS_META, MACHINE_CATEGORY_LABELS, ITEM_CATEGORIES,
} from '@/components/MachineForm';
import type { Machine, MachineCategory, MachineFilters, MachineKind, MachineStatus, MachinesSummary } from '@/types';
import {
  Plus, Search, Dumbbell, AlertTriangle, Wrench, CircleSlash,
  CheckCircle2, CalendarClock, ChevronRight, Package,
} from 'lucide-react';
import { imageUrl } from '@/utils/images';

const STATUS_ICON: Record<MachineStatus, React.ElementType> = {
  operational: CheckCircle2,
  maintenance: Wrench,
  out_of_service: CircleSlash,
};

export const MachinesPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';
  const canWrite = !!user && ['super_admin', 'admin', 'branch_admin'].includes(user.role);

  const [tab, setTab] = useState<MachineKind>('machine');
  const [allEquipment, setAllEquipment] = useState<Machine[]>([]);
  const [summary, setSummary] = useState<MachinesSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [filters, setFilters] = useState<MachineFilters>({ category: '', status: '', search: '' });

  const isItems = tab === 'item';

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

  // Carga ÚNICA de todo el equipamiento (máquinas + accesorios). El filtrado por
  // pestaña/categoría/estado/búsqueda se hace LOCALMENTE, así cambiar de tab,
  // teclear o cambiar filtros NO consulta Firestore (0 lecturas por interacción).
  const loadEquipment = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.getMachines({
        businessId: user?.role === 'super_admin' ? effectiveBusinessId : undefined,
        limit: 100,
      });
      if (response.success) setAllEquipment(response.data);
    } catch (err: any) {
      setError(err.message || 'Error cargando equipamiento');
    } finally {
      setLoading(false);
    }
  }, [user?.role, effectiveBusinessId]);

  useEffect(() => {
    loadEquipment();
  }, [loadEquipment]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  // Filtrado local (0 lecturas): pestaña + categoría + estado + búsqueda.
  const machines = useMemo(() => {
    const search = (filters.search ?? '').trim().toLowerCase();
    return allEquipment
      .filter((m) => {
        if ((m.kind ?? 'machine') !== tab) return false;
        if (filters.category && m.category !== filters.category) return false;
        if (filters.status && m.status !== filters.status) return false;
        if (search) {
          const haystack = `${m.name ?? ''} ${m.brand ?? ''} ${m.model ?? ''}`.toLowerCase();
          if (!haystack.includes(search)) return false;
        }
        return true;
      })
      .sort((a, b) => (a.name ?? '').toLowerCase().localeCompare((b.name ?? '').toLowerCase()));
  }, [allEquipment, tab, filters]);

  const switchTab = (next: MachineKind) => {
    if (next === tab) return;
    setTab(next);
    setFilters({ category: '', status: '', search: '' });
    setShowForm(false);
  };

  const statusCount = (s: MachineStatus) => summary?.byStatus?.[s] ?? 0;

  const isUpcoming = (machine: Machine) => {
    if (!machine.nextMaintenanceDate) return false;
    const horizon = new Date();
    horizon.setDate(horizon.getDate() + 7);
    return machine.nextMaintenanceDate <= horizon.toISOString().slice(0, 10);
  };

  const machineCards = [
    { label: 'Total', value: summary?.total ?? machines.length, icon: Dumbbell, color: 'text-primary-600 bg-primary-50' },
    { label: 'Operativas', value: statusCount('operational'), icon: CheckCircle2, color: 'text-green-600 bg-green-50' },
    { label: 'En mantenimiento', value: statusCount('maintenance'), icon: Wrench, color: 'text-yellow-600 bg-yellow-50' },
    { label: 'Fuera de servicio', value: statusCount('out_of_service'), icon: CircleSlash, color: 'text-red-600 bg-red-50' },
    { label: 'Próximos (7d)', value: summary?.upcomingMaintenance?.length ?? 0, icon: CalendarClock, color: 'text-blue-600 bg-blue-50' },
  ];

  const itemCards = [
    { label: 'Tipos de accesorio', value: summary?.items?.itemTypes ?? machines.length, icon: Dumbbell, color: 'text-primary-600 bg-primary-50' },
    { label: 'Unidades totales', value: summary?.items?.totalUnits ?? 0, icon: Package, color: 'text-blue-600 bg-blue-50' },
  ];

  const cards = isItems ? itemCards : machineCards;
  const categoryOptions = isItems ? ITEM_CATEGORIES : (Object.keys(MACHINE_CATEGORY_LABELS) as MachineCategory[]);
  const noun = isItems ? 'Accesorio' : 'Máquina';

  return (
    <div className="p-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Equipamiento</h1>
          <p className="text-gray-600 mt-1">Inventario de máquinas, pesas y accesorios</p>
        </div>
        {canWrite && (
          <button onClick={() => setShowForm(true)} className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Nuevo {noun}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 border-b mb-6">
        <button
          type="button"
          onClick={() => switchTab('machine')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            !isItems
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Máquinas
        </button>
        <button
          type="button"
          onClick={() => switchTab('item')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            isItems
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Pesas y Accesorios
        </button>
      </div>

      {/* Summary cards */}
      <div className={`grid grid-cols-2 gap-4 mb-6 ${isItems ? 'md:grid-cols-2 lg:grid-cols-2' : 'md:grid-cols-3 lg:grid-cols-5'}`}>
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
            {categoryOptions.map((c) => (
              <option key={c} value={c}>{MACHINE_CATEGORY_LABELS[c]}</option>
            ))}
          </select>
          {!isItems && (
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
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="loading-spinner h-10 w-10"></div>
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No se pudo cargar el equipamiento</h3>
          <p className="text-gray-600">{error}</p>
        </div>
      ) : machines.length === 0 ? (
        <div className="card text-center py-12">
          <Dumbbell className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {isItems ? 'No hay accesorios registrados' : 'No hay máquinas registradas'}
          </h3>
          <p className="text-gray-600 mb-6">
            {isItems
              ? 'Registra las pesas y accesorios del gimnasio para llevar su inventario.'
              : 'Registra los equipos del gimnasio para llevar su inventario y mantenimiento.'}
          </p>
          {canWrite && (
            <button onClick={() => setShowForm(true)} className="btn btn-primary">
              <Plus className="h-4 w-4 mr-2" />
              Agregar {noun}
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {machines.map((machine) => {
            const meta = MACHINE_STATUS_META[machine.status] || MACHINE_STATUS_META.operational;
            const StatusIcon = STATUS_ICON[machine.status] || CheckCircle2;
            const upcoming = isUpcoming(machine);
            const quantity = machine.quantity ?? 1;
            return (
              <Link
                key={machine.id}
                to={`/machines/${machine.id}`}
                className="group relative flex flex-col overflow-hidden rounded-xl bg-white ring-1 ring-gray-100 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg"
              >
                <div className="relative aspect-[4/3] overflow-hidden bg-gradient-to-br from-primary-50 via-white to-gray-100">
                  {machine.imageUrl ? (
                    <img
                      src={imageUrl(machine.imageUrl, 'tile')}
                      alt={machine.name}
                      loading="lazy"
                      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center">
                      {isItems ? (
                        <Package className="h-10 w-10 text-primary-300" />
                      ) : (
                        <Dumbbell className="h-10 w-10 text-primary-300" />
                      )}
                    </div>
                  )}

                  {!isItems && (
                    <span className={`badge ${meta.badge} absolute left-3 top-3 shadow-sm`}>
                      <span className={`mr-1.5 h-2 w-2 rounded-full ${meta.dot}`} />
                      {meta.label}
                    </span>
                  )}

                  {isItems && (
                    <span className="absolute right-3 top-3 rounded-full bg-white/90 px-2.5 py-0.5 text-xs font-semibold text-gray-700 shadow-sm">
                      x{quantity}
                    </span>
                  )}
                </div>

                <div className="flex flex-1 flex-col p-3">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="truncate font-semibold text-gray-900 transition-colors group-hover:text-primary-700">
                      {machine.name}
                    </h3>
                    <ChevronRight className="h-4 w-4 shrink-0 text-gray-300 transition-transform group-hover:translate-x-0.5 group-hover:text-primary-500" />
                  </div>
                  <p className="mt-0.5 truncate text-sm text-gray-500">
                    {[machine.brand, machine.model].filter(Boolean).join(' · ') || MACHINE_CATEGORY_LABELS[machine.category]}
                  </p>

                  <div className="mt-3 flex items-center justify-between border-t border-gray-50 pt-3 text-xs text-gray-500">
                    {isItems ? (
                      <>
                        <span className="inline-flex items-center">
                          <Package className="mr-1 h-3.5 w-3.5 text-gray-400" />
                          {quantity} {quantity === 1 ? 'unidad' : 'unidades'}
                        </span>
                        <span>{machine.weightKg != null ? `${machine.weightKg} kg` : '—'}</span>
                      </>
                    ) : (
                      <>
                        <span className="inline-flex items-center">
                          <StatusIcon className="mr-1 h-3.5 w-3.5 text-gray-400" />
                          {MACHINE_CATEGORY_LABELS[machine.category]}
                        </span>
                        {machine.nextMaintenanceDate && (
                          <span className={`inline-flex items-center ${upcoming ? 'text-yellow-600 font-medium' : ''}`}>
                            <CalendarClock className="mr-1 h-3.5 w-3.5" />
                            {machine.nextMaintenanceDate}
                          </span>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      <MachineForm
        open={showForm}
        kind={tab}
        businessId={effectiveBusinessId}
        onClose={() => setShowForm(false)}
        onSaved={() => {
          loadEquipment();
          loadSummary();
        }}
      />
    </div>
  );
};
