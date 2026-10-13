import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import { MachineForm, MACHINE_STATUS_META, MACHINE_CATEGORY_LABELS } from '@/components/MachineForm';
import toast from 'react-hot-toast';
import type {
  Machine, MachineMaintenance, MachineMaintenanceFormData,
  MachineMaintenanceStatus, MachineMaintenanceType, MachineResolvedStatus,
} from '@/types';
import {
  ArrowLeft, Dumbbell, Edit2, Trash2, Wrench, CalendarClock, X,
  AlertTriangle, Tag, Shield, Calendar, CheckCircle2, Package, Weight,
} from 'lucide-react';

const TYPE_META: Record<MachineMaintenanceType, { label: string; badge: string }> = {
  preventive: { label: 'Preventivo', badge: 'bg-blue-100 text-blue-800' },
  repair: { label: 'Reparación', badge: 'bg-orange-100 text-orange-800' },
};

const MT_STATUS_LABEL: Record<MachineMaintenanceStatus, string> = {
  scheduled: 'Programado',
  in_progress: 'En progreso',
  completed: 'Completado',
};

const emptyMaintForm = (): MachineMaintenanceFormData => ({
  type: 'preventive',
  status: 'completed',
  date: new Date().toISOString().slice(0, 10),
  description: '',
  costCents: undefined,
  technician: '',
  resolvedStatus: undefined,
  nextMaintenanceDate: '',
});

export const MachineDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const canWrite = !!user && ['super_admin', 'admin', 'branch_admin'].includes(user.role);

  const [machine, setMachine] = useState<Machine | null>(null);
  const [history, setHistory] = useState<MachineMaintenance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showEdit, setShowEdit] = useState(false);
  const [showMaint, setShowMaint] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [savingMaint, setSavingMaint] = useState(false);
  const [maintForm, setMaintForm] = useState<MachineMaintenanceFormData>(emptyMaintForm());
  const [costInput, setCostInput] = useState('');

  const loadMachine = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const [machineRes, historyRes] = await Promise.all([
        apiService.getMachine(id),
        apiService.getMachineMaintenance(id, { limit: 100 }),
      ]);
      if (machineRes.success) setMachine(machineRes.data);
      if (historyRes.success) setHistory(historyRes.data);
    } catch (err: any) {
      setError(err.message || 'Error cargando la máquina');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadMachine();
  }, [loadMachine]);

  const openMaintModal = () => {
    setMaintForm(emptyMaintForm());
    setCostInput('');
    setShowMaint(true);
  };

  const handleAddMaintenance = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;

    const isRepairCompleted = maintForm.type === 'repair' && maintForm.status === 'completed';
    if (isRepairCompleted && !maintForm.resolvedStatus) {
      toast.error('Una reparación completada requiere el estado resultante');
      return;
    }

    const parsedCost = costInput.trim() ? Math.round(parseFloat(costInput) * 100) : undefined;
    if (parsedCost !== undefined && (isNaN(parsedCost) || parsedCost < 0)) {
      toast.error('Costo inválido');
      return;
    }

    const payload: MachineMaintenanceFormData = {
      type: maintForm.type,
      status: maintForm.status,
      date: maintForm.date,
      description: maintForm.description?.trim() || undefined,
      technician: maintForm.technician?.trim() || undefined,
      costCents: parsedCost,
      resolvedStatus: isRepairCompleted ? maintForm.resolvedStatus : undefined,
      nextMaintenanceDate: maintForm.type === 'preventive' && maintForm.nextMaintenanceDate
        ? maintForm.nextMaintenanceDate : undefined,
    };

    try {
      setSavingMaint(true);
      const response = await apiService.addMachineMaintenance(id, payload);
      if (response.success) {
        toast.success('Mantenimiento registrado');
        setShowMaint(false);
        await loadMachine();
      }
    } catch (err: any) {
      toast.error(err.message || 'Error registrando mantenimiento');
    } finally {
      setSavingMaint(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    try {
      const response = await apiService.deleteMachine(id);
      if (response.success) {
        toast.success('Máquina eliminada');
        navigate('/machines');
      }
    } catch (err: any) {
      toast.error(err.message || 'Error eliminando máquina');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  if (error || !machine) {
    return (
      <div className="p-6">
        <div className="card text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Máquina no encontrada</h3>
          <p className="text-gray-600 mb-6">{error || 'El equipo que buscas no existe.'}</p>
          <Link to="/machines" className="btn btn-primary">Volver a Equipamiento</Link>
        </div>
      </div>
    );
  }

  const meta = MACHINE_STATUS_META[machine.status] || MACHINE_STATUS_META.operational;
  const isRepairCompleted = maintForm.type === 'repair' && maintForm.status === 'completed';
  const isItem = (machine.kind ?? 'machine') === 'item';
  const noun = isItem ? 'accesorio' : 'máquina';

  return (
    <div className="p-6">
      <Link to="/machines" className="inline-flex items-center text-sm text-gray-500 hover:text-primary-600 mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" /> Volver a Equipamiento
      </Link>

      {/* Ficha */}
      <div className="card mb-6 border-l-4 border-l-primary-500">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
          <div className="flex items-start">
            <div className="p-3 rounded-lg bg-primary-50 text-primary-600">
              <Dumbbell className="h-7 w-7" />
            </div>
            <div className="ml-4">
              <h1 className="text-2xl font-bold text-gray-900">{machine.name}</h1>
              <p className="text-gray-500 mt-1">
                {[machine.brand, machine.model].filter(Boolean).join(' · ') || MACHINE_CATEGORY_LABELS[machine.category]}
              </p>
              {!isItem && (
                <span className={`badge ${meta.badge} mt-2`}>
                  <span className={`mr-1.5 h-2 w-2 rounded-full ${meta.dot}`} />
                  {meta.label}
                </span>
              )}
            </div>
          </div>

          {canWrite && (
            <div className="flex space-x-2">
              <button onClick={() => setShowEdit(true)} className="btn btn-outline btn-sm">
                <Edit2 className="h-4 w-4 mr-1" /> Editar
              </button>
              <button onClick={() => setConfirmDelete(true)} className="btn btn-ghost btn-sm text-red-600 hover:text-red-800">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-4 border-t">
          <div className="flex items-center text-sm">
            <Tag className="h-4 w-4 mr-2 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Categoría</p>
              <p className="text-gray-900">{MACHINE_CATEGORY_LABELS[machine.category]}</p>
            </div>
          </div>
          <div className="flex items-center text-sm">
            <Calendar className="h-4 w-4 mr-2 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Compra</p>
              <p className="text-gray-900">{machine.purchaseDate || '—'}</p>
            </div>
          </div>
          {isItem ? (
            <>
              <div className="flex items-center text-sm">
                <Package className="h-4 w-4 mr-2 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-500">Cantidad</p>
                  <p className="text-gray-900">{machine.quantity ?? 1}</p>
                </div>
              </div>
              <div className="flex items-center text-sm">
                <Weight className="h-4 w-4 mr-2 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-500">Peso</p>
                  <p className="text-gray-900">{machine.weightKg != null ? `${machine.weightKg} kg` : '—'}</p>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center text-sm">
                <Shield className="h-4 w-4 mr-2 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-500">Garantía</p>
                  <p className="text-gray-900">{machine.warrantyUntil || '—'}</p>
                </div>
              </div>
              <div className="flex items-center text-sm">
                <CalendarClock className="h-4 w-4 mr-2 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-500">Próximo mantenimiento</p>
                  <p className="text-gray-900">{machine.nextMaintenanceDate || 'No programado'}</p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Historial (sólo máquinas: los accesorios no tienen mantenimiento) */}
      {!isItem && (
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Historial de mantenimiento</h2>
          {canWrite && (
            <button onClick={openMaintModal} className="btn btn-primary btn-sm">
              <Wrench className="h-4 w-4 mr-2" /> Registrar Mantenimiento
            </button>
          )}
        </div>

        {history.length === 0 ? (
          <div className="text-center py-10">
            <Wrench className="h-10 w-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">Sin registros de mantenimiento aún.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4 font-medium">Fecha</th>
                  <th className="py-2 pr-4 font-medium">Tipo</th>
                  <th className="py-2 pr-4 font-medium">Estado</th>
                  <th className="py-2 pr-4 font-medium">Descripción</th>
                  <th className="py-2 pr-4 font-medium">Técnico</th>
                  <th className="py-2 pr-4 font-medium text-right">Costo</th>
                </tr>
              </thead>
              <tbody>
                {history.map((rec) => {
                  const tmeta = TYPE_META[rec.type] || TYPE_META.preventive;
                  return (
                    <tr key={rec.id} className="border-b last:border-0">
                      <td className="py-3 pr-4 whitespace-nowrap text-gray-900">{rec.date}</td>
                      <td className="py-3 pr-4">
                        <span className={`badge ${tmeta.badge}`}>{tmeta.label}</span>
                      </td>
                      <td className="py-3 pr-4 text-gray-600">
                        <span className="inline-flex items-center">
                          {rec.status === 'completed' && <CheckCircle2 className="h-3.5 w-3.5 mr-1 text-green-500" />}
                          {MT_STATUS_LABEL[rec.status] || rec.status}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-gray-600 max-w-xs truncate">{rec.description || '—'}</td>
                      <td className="py-3 pr-4 text-gray-600">{rec.technician || '—'}</td>
                      <td className="py-3 pr-4 text-right text-gray-900 whitespace-nowrap">
                        {rec.costCents != null ? `$${(rec.costCents / 100).toFixed(2)}` : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      )}

      {/* Edit modal */}
      <MachineForm
        open={showEdit}
        initial={machine}
        onClose={() => setShowEdit(false)}
        onSaved={(updated) => setMachine((prev) => ({ ...(prev as Machine), ...updated }))}
      />

      {/* Maintenance modal (sólo máquinas) */}
      {!isItem && showMaint && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-4 border-b">
              <h3 className="text-lg font-semibold text-gray-900">Registrar Mantenimiento</h3>
              <button onClick={() => setShowMaint(false)} className="btn btn-ghost btn-sm" type="button">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleAddMaintenance} className="p-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tipo *</label>
                  <select
                    value={maintForm.type}
                    onChange={(e) => setMaintForm((p) => ({ ...p, type: e.target.value as MachineMaintenanceType }))}
                    className="input"
                  >
                    <option value="preventive">Preventivo</option>
                    <option value="repair">Reparación</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Estado *</label>
                  <select
                    value={maintForm.status}
                    onChange={(e) => setMaintForm((p) => ({ ...p, status: e.target.value as MachineMaintenanceStatus }))}
                    className="input"
                  >
                    <option value="scheduled">Programado</option>
                    <option value="in_progress">En progreso</option>
                    <option value="completed">Completado</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fecha *</label>
                <input
                  type="date"
                  value={maintForm.date}
                  onChange={(e) => setMaintForm((p) => ({ ...p, date: e.target.value }))}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
                <textarea
                  value={maintForm.description || ''}
                  onChange={(e) => setMaintForm((p) => ({ ...p, description: e.target.value }))}
                  className="input"
                  rows={2}
                  placeholder="Detalle del trabajo realizado..."
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Técnico</label>
                  <input
                    type="text"
                    value={maintForm.technician || ''}
                    onChange={(e) => setMaintForm((p) => ({ ...p, technician: e.target.value }))}
                    className="input"
                    placeholder="Nombre del técnico"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Costo</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={costInput}
                    onChange={(e) => setCostInput(e.target.value)}
                    className="input"
                    placeholder="0.00"
                  />
                </div>
              </div>

              {isRepairCompleted && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Estado resultante de la máquina *</label>
                  <select
                    value={maintForm.resolvedStatus || ''}
                    onChange={(e) => setMaintForm((p) => ({ ...p, resolvedStatus: e.target.value as MachineResolvedStatus }))}
                    className="input"
                    required
                  >
                    <option value="">Selecciona...</option>
                    <option value="operational">Operativa</option>
                    <option value="out_of_service">Fuera de servicio</option>
                  </select>
                </div>
              )}

              {maintForm.type === 'preventive' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Próximo mantenimiento (opcional)
                  </label>
                  <input
                    type="date"
                    value={maintForm.nextMaintenanceDate || ''}
                    onChange={(e) => setMaintForm((p) => ({ ...p, nextMaintenanceDate: e.target.value }))}
                    className="input"
                  />
                  <p className="text-xs text-gray-500 mt-1">Si se deja vacío, se programará a 90 días.</p>
                </div>
              )}

              <div className="flex justify-end space-x-2 pt-4 border-t">
                <button type="button" onClick={() => setShowMaint(false)} className="btn btn-outline">
                  Cancelar
                </button>
                <button type="submit" disabled={savingMaint} className="btn btn-primary">
                  {savingMaint ? 'Guardando...' : 'Registrar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6 text-center">
            <AlertTriangle className="h-10 w-10 text-red-500 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">¿Eliminar {noun}?</h3>
            <p className="text-sm text-gray-600 mb-6">
              {machine.name} quedará fuera del inventario.{isItem ? '' : ' El historial se conserva.'}
            </p>
            <div className="flex justify-center space-x-2">
              <button onClick={handleDelete} className="btn bg-red-600 text-white hover:bg-red-700">
                Eliminar
              </button>
              <button onClick={() => setConfirmDelete(false)} className="btn btn-ghost">
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
