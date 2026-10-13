import React, { useCallback, useEffect, useState } from 'react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from 'recharts';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';
import {
  ExpenseForm, EXPENSE_CATEGORY_META, EXPENSE_CATEGORIES, formatDollars,
} from '@/components/ExpenseForm';
import type { Expense, ExpenseCategory, ExpenseFilters, ExpenseSummary } from '@/types';
import {
  Plus, Search, TrendingDown, Pencil, Trash2, CalendarRange, AlertTriangle, Receipt,
} from 'lucide-react';

const LIMIT = 20;

export const ExpensesPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';
  const canWrite = !!user && ['super_admin', 'admin', 'branch_admin'].includes(user.role);

  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [summary, setSummary] = useState<ExpenseSummary | null>(null);
  const [meta, setMeta] = useState({ total: 0, page: 1, limit: LIMIT, pages: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<ExpenseFilters>({
    category: '', startDate: '', endDate: '', search: '',
  });

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);

  const scoped = user?.role === 'super_admin' && effectiveBusinessId
    ? { businessId: effectiveBusinessId }
    : {};

  const loadSummary = useCallback(async () => {
    try {
      const response = await apiService.getExpensesSummary(scoped);
      if (response.success) setSummary(response.data);
    } catch {
      /* el resumen es accesorio; no bloquea la lista */
    }
  }, [user?.role, effectiveBusinessId]);

  const loadExpenses = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.getExpenses({
        ...scoped,
        category: filters.category || undefined,
        startDate: filters.startDate || undefined,
        endDate: filters.endDate || undefined,
        search: filters.search || undefined,
        page,
        limit: LIMIT,
      });
      if (response.success) {
        setExpenses(response.data);
        if (response.meta) {
          setMeta({
            total: response.meta.total ?? 0,
            page: response.meta.page ?? page,
            limit: response.meta.limit ?? LIMIT,
            pages: response.meta.pages ?? 0,
          });
        }
      }
    } catch (err: any) {
      setError(err.message || 'Error cargando egresos');
    } finally {
      setLoading(false);
    }
  }, [user?.role, effectiveBusinessId, filters, page]);

  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadExpenses(); }, [loadExpenses]);

  // Reinicia a la página 1 al cambiar cualquier filtro.
  const updateFilter = (patch: Partial<ExpenseFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  };

  const openCreate = () => { setEditing(null); setShowForm(true); };
  const openEdit = (expense: Expense) => { setEditing(expense); setShowForm(true); };

  const handleDelete = async (expense: Expense) => {
    const label = `${EXPENSE_CATEGORY_META[expense.category].label} · ${formatDollars(expense.amountCents)}`;
    if (!window.confirm(`¿Eliminar el egreso "${label}"? Esta acción no se puede deshacer.`)) return;
    try {
      const response = await apiService.deleteExpense(expense.id);
      if (response.success) {
        toast.success('Egreso eliminado');
        loadExpenses();
        loadSummary();
      }
    } catch (err: any) {
      toast.error(err.message || 'Error eliminando egreso');
    }
  };

  const statCards = [
    { label: 'Hoy', value: summary?.today ?? 0, icon: TrendingDown, color: 'text-primary-600 bg-primary-50' },
    { label: 'Últimos 7 días', value: summary?.week ?? 0, icon: CalendarRange, color: 'text-blue-600 bg-blue-50' },
    { label: 'Últimos 30 días', value: summary?.month ?? 0, icon: Receipt, color: 'text-green-600 bg-green-50' },
  ];

  const chartData = EXPENSE_CATEGORIES.map((c) => ({
    name: EXPENSE_CATEGORY_META[c].label,
    value: (summary?.byCategory?.[c] ?? 0) / 100,
  })).filter((d) => d.value > 0);

  const hasFilters = !!(filters.category || filters.startDate || filters.endDate || filters.search);

  return (
    <div className="p-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Egresos</h1>
          <p className="text-gray-600 mt-1">Gastos del negocio por categoría</p>
        </div>
        {canWrite && (
          <button onClick={openCreate} className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Registrar Egreso
          </button>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        {statCards.map((card) => (
          <div key={card.label} className="card p-4 flex items-center">
            <div className={`p-2 rounded-lg ${card.color}`}>
              <card.icon className="h-5 w-5" />
            </div>
            <div className="ml-3">
              <p className="text-2xl font-bold text-gray-900">{formatDollars(card.value)}</p>
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
              onChange={(e) => updateFilter({ search: e.target.value })}
              className="input pl-9"
              placeholder="Buscar por descripción..."
            />
          </div>
          <select
            value={filters.category}
            onChange={(e) => updateFilter({ category: e.target.value as ExpenseCategory | '' })}
            className="input"
          >
            <option value="">Todas las categorías</option>
            {EXPENSE_CATEGORIES.map((c) => (
              <option key={c} value={c}>{EXPENSE_CATEGORY_META[c].label}</option>
            ))}
          </select>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => updateFilter({ startDate: e.target.value })}
              className="input"
              title="Desde"
            />
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => updateFilter({ endDate: e.target.value })}
              className="input"
              title="Hasta"
            />
          </div>
        </div>
      </div>

      {/* By-category chart */}
      {chartData.length > 0 && (
        <div className="card mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Egresos por categoría (USD)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => formatDollars(Number(value) * 100)} />
                <Bar dataKey="value" fill="#F73F08" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="loading-spinner h-10 w-10"></div>
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No se pudieron cargar los egresos</h3>
          <p className="text-gray-600">{error}</p>
        </div>
      ) : expenses.length === 0 ? (
        <div className="card text-center py-12">
          <TrendingDown className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {hasFilters ? 'No hay egresos para estos filtros' : 'No hay egresos registrados'}
          </h3>
          <p className="text-gray-600 mb-6">
            Registra los gastos del negocio para llevar el control financiero.
          </p>
          {canWrite && (
            <button onClick={openCreate} className="btn btn-primary">
              <Plus className="h-4 w-4 mr-2" />
              Registrar Egreso
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-left">
                <tr>
                  <th className="px-4 py-3 font-medium">Fecha</th>
                  <th className="px-4 py-3 font-medium">Categoría</th>
                  <th className="px-4 py-3 font-medium hidden sm:table-cell">Descripción</th>
                  <th className="px-4 py-3 font-medium text-right">Monto</th>
                  {canWrite && <th className="px-4 py-3 font-medium text-right">Acciones</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {expenses.map((expense) => {
                  const meta = EXPENSE_CATEGORY_META[expense.category];
                  return (
                    <tr key={expense.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{expense.date}</td>
                      <td className="px-4 py-3">
                        <span className={`badge ${meta.badge}`}>{meta.label}</span>
                      </td>
                      <td className="px-4 py-3 text-gray-600 hidden sm:table-cell">
                        {expense.description || '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-900 whitespace-nowrap">
                        {formatDollars(expense.amountCents)}
                      </td>
                      {canWrite && (
                        <td className="px-4 py-3">
                          <div className="flex justify-end space-x-1">
                            <button
                              onClick={() => openEdit(expense)}
                              className="p-2 rounded-md text-gray-500 hover:bg-primary-50 hover:text-primary-600"
                              title="Editar"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDelete(expense)}
                              className="p-2 rounded-md text-gray-500 hover:bg-red-50 hover:text-red-600"
                              title="Eliminar"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {meta.pages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-gray-500">
                Página {meta.page} de {meta.pages} · {meta.total} egresos
              </p>
              <div className="flex space-x-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={meta.page <= 1}
                  className="btn btn-secondary btn-sm"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(meta.pages, p + 1))}
                  disabled={meta.page >= meta.pages}
                  className="btn btn-secondary btn-sm"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </>
      )}

      <ExpenseForm
        open={showForm}
        initial={editing}
        businessId={effectiveBusinessId}
        onClose={() => setShowForm(false)}
        onSaved={() => {
          loadExpenses();
          loadSummary();
        }}
      />
    </div>
  );
};
