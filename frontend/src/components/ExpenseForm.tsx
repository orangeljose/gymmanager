import React, { useEffect, useState } from 'react';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';
import { X } from 'lucide-react';
import type { Expense, ExpenseCategory, ExpenseFormData } from '@/types';

// Etiquetas y colores de badge por categoría de egreso (tema GoatGym).
export const EXPENSE_CATEGORY_META: Record<ExpenseCategory, { label: string; badge: string }> = {
  payroll: { label: 'Nómina', badge: 'bg-purple-100 text-purple-800' },
  supplies: { label: 'Insumos', badge: 'bg-blue-100 text-blue-800' },
  services: { label: 'Servicios', badge: 'bg-teal-100 text-teal-800' },
  rent: { label: 'Alquiler', badge: 'bg-orange-100 text-orange-800' },
  maintenance: { label: 'Mantenimiento', badge: 'bg-yellow-100 text-yellow-800' },
  other: { label: 'Otro', badge: 'bg-gray-100 text-gray-800' },
};

export const EXPENSE_CATEGORIES = Object.keys(EXPENSE_CATEGORY_META) as ExpenseCategory[];

/** centavos → dólares con 2 decimales */
export const formatDollars = (cents: number): string =>
  `$${((cents || 0) / 100).toFixed(2)}`;

const todayIso = () => new Date().toISOString().slice(0, 10);

interface ExpenseFormState {
  category: ExpenseCategory;
  amount: string;   // dólares, tal como lo teclea el usuario
  description: string;
  date: string;
}

const emptyForm = (): ExpenseFormState => ({
  category: 'supplies',
  amount: '',
  description: '',
  date: todayIso(),
});

interface ExpenseFormProps {
  open: boolean;
  initial?: Expense | null;
  businessId?: string;
  onClose: () => void;
  onSaved: (expense: Expense) => void;
}

export const ExpenseForm: React.FC<ExpenseFormProps> = ({
  open, initial, businessId, onClose, onSaved,
}) => {
  const [form, setForm] = useState<ExpenseFormState>(emptyForm());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setForm({
        category: initial.category,
        amount: (initial.amountCents / 100).toFixed(2),
        description: initial.description || '',
        date: initial.date || todayIso(),
      });
    } else {
      setForm(emptyForm());
    }
  }, [open, initial]);

  if (!open) return null;

  const set = <K extends keyof ExpenseFormState>(key: K, value: ExpenseFormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const dollars = Number(form.amount);
    if (!Number.isFinite(dollars) || dollars <= 0) {
      toast.error('El monto debe ser mayor que 0');
      return;
    }
    if (!form.date) {
      toast.error('La fecha es obligatoria');
      return;
    }

    const payload: ExpenseFormData = {
      category: form.category,
      amountCents: Math.round(dollars * 100),
      description: form.description.trim() || undefined,
      date: form.date,
    };

    try {
      setSaving(true);
      const response = initial
        ? await apiService.updateExpense(initial.id, payload)
        : await apiService.createExpense({ ...payload, businessId });

      if (response.success) {
        toast.success(initial ? 'Egreso actualizado' : 'Egreso registrado');
        onSaved(response.data);
        onClose();
      }
    } catch (error: any) {
      toast.error(error.message || 'Error guardando egreso');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-4 border-b sticky top-0 bg-white">
          <h3 className="text-lg font-semibold text-gray-900">
            {initial ? 'Editar Egreso' : 'Registrar Egreso'}
          </h3>
          <button onClick={onClose} className="btn btn-ghost btn-sm" type="button">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoría *</label>
              <select
                value={form.category}
                onChange={(e) => set('category', e.target.value as ExpenseCategory)}
                className="input"
              >
                {EXPENSE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{EXPENSE_CATEGORY_META[c].label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Monto (USD) *</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={form.amount}
                onChange={(e) => set('amount', e.target.value)}
                className="input"
                placeholder="Ej: 150.00"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Fecha *</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => set('date', e.target.value)}
              className="input"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
            <textarea
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              className="input h-24 py-2"
              placeholder="Detalle opcional del egreso"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-4 border-t">
            <button type="button" onClick={onClose} className="btn btn-outline">
              Cancelar
            </button>
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? 'Guardando...' : initial ? 'Actualizar' : 'Registrar Egreso'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
