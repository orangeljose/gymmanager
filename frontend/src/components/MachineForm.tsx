import React, { useEffect, useState } from 'react';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';
import { X } from 'lucide-react';
import type { Machine, MachineCategory, MachineFormData, MachineStatus } from '@/types';

export const MACHINE_STATUS_META: Record<MachineStatus, { label: string; badge: string; dot: string }> = {
  operational: { label: 'Operativa', badge: 'bg-green-100 text-green-800', dot: 'bg-green-500' },
  maintenance: { label: 'En mantenimiento', badge: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500' },
  out_of_service: { label: 'Fuera de servicio', badge: 'bg-red-100 text-red-800', dot: 'bg-red-500' },
};

export const MACHINE_CATEGORY_LABELS: Record<MachineCategory, string> = {
  cardio: 'Cardio',
  strength: 'Fuerza',
  functional: 'Funcional',
  free_weights: 'Peso libre',
  other: 'Otro',
};

const EMPTY_FORM: MachineFormData = {
  name: '',
  brand: '',
  model: '',
  category: 'cardio',
  purchaseDate: '',
  warrantyUntil: '',
  status: 'operational',
  nextMaintenanceDate: '',
};

interface MachineFormProps {
  open: boolean;
  initial?: Machine | null;
  businessId?: string;
  onClose: () => void;
  onSaved: (machine: Machine) => void;
}

export const MachineForm: React.FC<MachineFormProps> = ({ open, initial, businessId, onClose, onSaved }) => {
  const [form, setForm] = useState<MachineFormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setForm({
        name: initial.name,
        brand: initial.brand || '',
        model: initial.model || '',
        category: initial.category,
        purchaseDate: initial.purchaseDate || '',
        warrantyUntil: initial.warrantyUntil || '',
        status: initial.status,
        nextMaintenanceDate: initial.nextMaintenanceDate || '',
      });
    } else {
      setForm(EMPTY_FORM);
    }
  }, [open, initial]);

  if (!open) return null;

  const set = <K extends keyof MachineFormData>(key: K, value: MachineFormData[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }
    try {
      setSaving(true);
      const payload: MachineFormData = {
        ...form,
        name: form.name.trim(),
        brand: form.brand?.trim() || undefined,
        model: form.model?.trim() || undefined,
        purchaseDate: form.purchaseDate || undefined,
        warrantyUntil: form.warrantyUntil || undefined,
        nextMaintenanceDate: form.nextMaintenanceDate || undefined,
      };
      const response = initial
        ? await apiService.updateMachine(initial.id, payload)
        : await apiService.createMachine({ ...payload, businessId });
      if (response.success) {
        toast.success(initial ? 'Máquina actualizada' : 'Máquina creada');
        onSaved(response.data);
        onClose();
      }
    } catch (error: any) {
      toast.error(error.message || 'Error guardando máquina');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-4 border-b sticky top-0 bg-white">
          <h3 className="text-lg font-semibold text-gray-900">
            {initial ? 'Editar Máquina' : 'Nueva Máquina'}
          </h3>
          <button onClick={onClose} className="btn btn-ghost btn-sm" type="button">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              className="input"
              placeholder="Ej: Cinta de correr #1"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Marca</label>
              <input
                type="text"
                value={form.brand || ''}
                onChange={(e) => set('brand', e.target.value)}
                className="input"
                placeholder="Ej: Life Fitness"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Modelo</label>
              <input
                type="text"
                value={form.model || ''}
                onChange={(e) => set('model', e.target.value)}
                className="input"
                placeholder="Ej: T5"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoría *</label>
              <select
                value={form.category}
                onChange={(e) => set('category', e.target.value as MachineCategory)}
                className="input"
              >
                {(Object.keys(MACHINE_CATEGORY_LABELS) as MachineCategory[]).map((c) => (
                  <option key={c} value={c}>{MACHINE_CATEGORY_LABELS[c]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select
                value={form.status}
                onChange={(e) => set('status', e.target.value as MachineStatus)}
                className="input"
              >
                {(Object.keys(MACHINE_STATUS_META) as MachineStatus[]).map((s) => (
                  <option key={s} value={s}>{MACHINE_STATUS_META[s].label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fecha de compra</label>
              <input
                type="date"
                value={form.purchaseDate || ''}
                onChange={(e) => set('purchaseDate', e.target.value)}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Garantía hasta</label>
              <input
                type="date"
                value={form.warrantyUntil || ''}
                onChange={(e) => set('warrantyUntil', e.target.value)}
                className="input"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Próximo mantenimiento</label>
            <input
              type="date"
              value={form.nextMaintenanceDate || ''}
              onChange={(e) => set('nextMaintenanceDate', e.target.value)}
              className="input"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-4 border-t">
            <button type="button" onClick={onClose} className="btn btn-outline">
              Cancelar
            </button>
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? 'Guardando...' : initial ? 'Actualizar' : 'Crear Máquina'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
