import React, { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import { usePlans } from '@/hooks/usePlans';
import { usePaymentAccounts } from '@/hooks/usePaymentAccounts';
import type { MembershipPlan, PlanFormData } from '@/types';
import toast from 'react-hot-toast';
import { Plus, Edit2, Trash2, X, AlertCircle } from 'lucide-react';

export const PlansPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || "";
  const { plans, loading, setPlans } = usePlans(effectiveBusinessId);
  const { accounts } = usePaymentAccounts(effectiveBusinessId);
  const [showModal, setShowModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<MembershipPlan | null>(null);
  const [formData, setFormData] = useState<PlanFormData>({
    name: '',
    price: 0,
    durationDays: 30,
    description: '',
    benefits: [],
    businessId: '',
    pricesByMethod: {}
  });
  // Beneficios ocultos temporalmente
  // const [benefitInput, setBenefitInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

const openModal = (plan?: MembershipPlan) => {
    if (plan) {
      setEditingPlan(plan);
      setFormData({
        name: plan.name,
        price: plan.price,
        durationDays: plan.durationDays,
        description: plan.description || '',
        benefits: plan.benefits || [],
        pricesByMethod: plan.pricesByMethod || {}
      });
    } else {
      setEditingPlan(null);
      setFormData({
        name: '',
        price: 0,
        durationDays: 0,
        description: '',
        benefits: [],
        pricesByMethod: {}
      });
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingPlan(null);
  };

  /* Beneficios ocultos temporalmente
  const addBenefit = () => {
    if (benefitInput.trim()) {
      setFormData(prev => ({
        ...prev,
        benefits: [...(prev.benefits || []), benefitInput.trim()]
      }));
      setBenefitInput('');
    }
  };

  const removeBenefit = (index: number) => {
    setFormData(prev => ({
      ...prev,
      benefits: (prev.benefits || []).filter((_, i) => i !== index)
    }));
  };
  */

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveBusinessId) return;

    if (formData.price <= 0) {
      toast.error('El precio debe ser mayor a $0');
      return;
    }

    try {
      setSaving(true);
      // Limpiar precios por método vacíos (undefined)
      const cleanPrices = formData.pricesByMethod
        ? Object.fromEntries(Object.entries(formData.pricesByMethod).filter(([, v]) => v !== undefined))
        : undefined;
      const payload = { ...formData, pricesByMethod: cleanPrices };

      if (editingPlan) {
        const response = await apiService.updatePlan(editingPlan.id, payload);
        if (response.success) {
          toast.success('Plan actualizado');
          setPlans(prev => prev.map(p => p.id === editingPlan.id ? { ...p, ...response.data } : p));
          closeModal();
        }
      } else {
        const response = await apiService.createPlan({ ...payload, businessId: effectiveBusinessId });
        if (response.success) {
          toast.success('Plan creado');
          setPlans(prev => [...prev, response.data!]);
          closeModal();
        }
      }
    } catch (error: any) {
      toast.error(error.message || 'Error guardando plan');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (planId: string) => {
    try {
      const response = await apiService.deletePlan(planId);
      if (response.success) {
        toast.success('Plan eliminado');
        setPlans(prev => prev.filter(p => p.id !== planId));
        setConfirmDelete(null);
      }
    } catch (error: any) {
      toast.error(error.message || 'Error eliminando plan');
    }
  };

  const formatPrice = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(cents / 100);
  };

  const formatDuration = (days: number) => {
    if (days === 30) return '1 mes';
    if (days === 90) return '3 meses';
    if (days === 365) return '1 año';
    if (days % 30 === 0) return `${days / 30} meses`;
    return `${days} días`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Planes de Membresía</h1>
          <p className="text-gray-600 mt-1">Gestiona los planes disponibles para tus clientes</p>
        </div>
        <button onClick={() => openModal()} className="btn btn-primary">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Plan
        </button>
      </div>

      {plans.length === 0 ? (
        <div className="card text-center py-12">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay planes</h3>
          <p className="text-gray-600 mb-6">Comienza creando tu primer plan de membresía</p>
          <button onClick={() => openModal()} className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Crear Plan
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div key={plan.id} className="card">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                  <p className="text-2xl font-bold text-primary-600 mt-1">
                    {formatPrice(plan.price)}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  plan.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                }`}>
                  {plan.isActive ? 'Activo' : 'Inactivo'}
                </span>
              </div>

              <div className="mb-4">
                <span className="text-sm text-gray-600">Duración: </span>
                <span className="text-sm font-medium text-gray-900">{formatDuration(plan.durationDays)}</span>
              </div>

              {plan.description && (
                <p className="text-sm text-gray-600 mb-4">{plan.description}</p>
              )}

              {/* Beneficios ocultos temporalmente */}
              {/* {plan.benefits && plan.benefits.length > 0 && (
                <ul className="space-y-1 mb-4">
                  {plan.benefits.slice(0, 3).map((benefit, idx) => (
                    <li key={idx} className="flex items-center text-sm text-gray-700">
                      <Check className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                      {benefit}
                    </li>
                  ))}
                  {plan.benefits.length > 3 && (
                    <li className="text-sm text-gray-500">
                      +{plan.benefits.length - 3} más beneficios
                    </li>
                  )}
                </ul>
              )} */}

              <div className="flex justify-end space-x-2 pt-4 border-t">
                <button
                  onClick={() => openModal(plan)}
                  className="btn btn-ghost btn-sm"
                >
                  <Edit2 className="h-4 w-4" />
                </button>
                {user?.role === 'super_admin' && (
                  <button
                    onClick={() => setConfirmDelete(plan.id)}
                    className="btn btn-ghost btn-sm text-red-600 hover:text-red-800"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>

              {confirmDelete === plan.id && (
                <div className="absolute inset-0 bg-white/95 flex items-center justify-center rounded-lg">
                  <div className="text-center p-4">
                    <p className="text-sm text-gray-900 mb-4">¿Eliminar este plan?</p>
                    <div className="flex space-x-2 justify-center">
                      <button
                        onClick={() => handleDelete(plan.id)}
                        className="btn btn-danger btn-sm"
                      >
                        Eliminar
                      </button>
                      <button
                        onClick={() => setConfirmDelete(null)}
                        className="btn btn-ghost btn-sm"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="flex justify-between items-center p-4 border-b">
              <h3 className="text-lg font-semibold">
                {editingPlan ? 'Editar Plan' : 'Nuevo Plan'}
              </h3>
              <button onClick={closeModal} className="btn btn-ghost btn-sm">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del Plan *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="input"
                  placeholder="Ej: Mensual, Trimestral"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Precio (USD) *
                  </label>
                  <input
                    type="number"
                    value={formData.price ? formData.price / 100 : ''}
                    onChange={(e) => {
                      const raw = e.target.value;
                      setFormData(prev => ({
                        ...prev,
                        price: raw === '' ? 0 : Math.round(parseFloat(raw) * 100)
                      }));
                    }}
                    className="input"
                    placeholder="35.00"
                    min="1"
                    step="0.01"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Duración (días) *
                  </label>
                  <input
                    type="number"
                    value={formData.durationDays || ''}
                    onChange={(e) => {
                      const raw = e.target.value;
                      setFormData(prev => ({
                        ...prev,
                        durationDays: raw === '' ? 0 : parseInt(raw)
                      }));
                    }}
                    className="input"
                    placeholder="30"
                    min="1"
                    required
                  />
                </div>
              </div>

              {/* Precios por método de pago */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Precios por método de pago
                </label>
                <p className="text-xs text-gray-500 mb-3">
                  Opcional. Si no se define, se usa el precio base. Los métodos dependen de tus cuentas de pago registradas.
                </p>
                <div className="space-y-2">
                  {/* Efectivo siempre disponible */}
                  <div className="flex items-center gap-3">
                    <span className="w-32 text-sm text-gray-700">Efectivo</span>
                    <input
                      type="number"
                      value={formData.pricesByMethod?.cash !== undefined ? (formData.pricesByMethod.cash / 100) : ''}
                      onChange={(e) => {
                        const raw = e.target.value;
                        setFormData(prev => ({
                          ...prev,
                          pricesByMethod: {
                            ...prev.pricesByMethod,
                            cash: raw === '' ? undefined : Math.round(parseFloat(raw) * 100)
                          }
                        }));
                      }}
                      className="input"
                      placeholder="Dejar vacío = precio base"
                      min="0"
                      step="0.01"
                    />
                  </div>

                  {accounts.filter(a => a.type === 'zelle').length > 0 && (
                    <div className="flex items-center gap-3">
                      <span className="w-32 text-sm text-gray-700">Zelle</span>
                      <input
                        type="number"
                        value={formData.pricesByMethod?.zelle !== undefined ? (formData.pricesByMethod.zelle / 100) : ''}
                        onChange={(e) => {
                          const raw = e.target.value;
                          setFormData(prev => ({
                            ...prev,
                            pricesByMethod: {
                              ...prev.pricesByMethod,
                              zelle: raw === '' ? undefined : Math.round(parseFloat(raw) * 100)
                            }
                          }));
                        }}
                        className="input"
                        placeholder="Dejar vacío = precio base"
                        min="0"
                        step="0.01"
                      />
                    </div>
                  )}

                  {accounts.filter(a => a.type === 'binance').length > 0 && (
                    <div className="flex items-center gap-3">
                      <span className="w-32 text-sm text-gray-700">Binance</span>
                      <input
                        type="number"
                        value={formData.pricesByMethod?.binance !== undefined ? (formData.pricesByMethod.binance / 100) : ''}
                        onChange={(e) => {
                          const raw = e.target.value;
                          setFormData(prev => ({
                            ...prev,
                            pricesByMethod: {
                              ...prev.pricesByMethod,
                              binance: raw === '' ? undefined : Math.round(parseFloat(raw) * 100)
                            }
                          }));
                        }}
                        className="input"
                        placeholder="Dejar vacío = precio base"
                        min="0"
                        step="0.01"
                      />
                    </div>
                  )}

                  {accounts.filter(a => a.type === 'pago_movil').length > 0 && (
                    <div className="flex items-center gap-3">
                      <span className="w-32 text-sm text-gray-700">Pago Móvil</span>
                      <input
                        type="number"
                        value={formData.pricesByMethod?.pago_movil !== undefined ? (formData.pricesByMethod.pago_movil / 100) : ''}
                        onChange={(e) => {
                          const raw = e.target.value;
                          setFormData(prev => ({
                            ...prev,
                            pricesByMethod: {
                              ...prev.pricesByMethod,
                              pago_movil: raw === '' ? undefined : Math.round(parseFloat(raw) * 100)
                            }
                          }));
                        }}
                        className="input"
                        placeholder="Dejar vacío = precio base"
                        min="0"
                        step="0.01"
                      />
                    </div>
                  )}

                  {accounts.filter(a => a.type === 'bank').length > 0 && (
                    <div className="flex items-center gap-3">
                      <span className="w-32 text-sm text-gray-700">Transferencia</span>
                      <input
                        type="number"
                        value={formData.pricesByMethod?.transfer !== undefined ? (formData.pricesByMethod.transfer / 100) : ''}
                        onChange={(e) => {
                          const raw = e.target.value;
                          setFormData(prev => ({
                            ...prev,
                            pricesByMethod: {
                              ...prev.pricesByMethod,
                              transfer: raw === '' ? undefined : Math.round(parseFloat(raw) * 100)
                            }
                          }));
                        }}
                        className="input"
                        placeholder="Dejar vacío = precio base"
                        min="0"
                        step="0.01"
                      />
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descripción
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="input"
                  rows={2}
                  placeholder="Descripción breve del plan..."
                />
              </div>

              {/* Beneficios ocultos temporalmente */}
              {/*
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Beneficios
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={benefitInput}
                    onChange={(e) => setBenefitInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addBenefit())}
                    className="input flex-1"
                    placeholder="Agregar beneficio..."
                  />
                  <button type="button" onClick={addBenefit} className="btn btn-outline btn-sm">
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
                {formData.benefits.length > 0 && (
                  <ul className="space-y-1">
                    {formData.benefits.map((benefit, idx) => (
                      <li key={idx} className="flex items-center justify-between bg-gray-50 px-3 py-1 rounded text-sm">
                        <span>{benefit}</span>
                        <button type="button" onClick={() => removeBenefit(idx)} className="text-gray-500 hover:text-red-600">
                          <X className="h-4 w-4" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              */}

              <div className="flex justify-end space-x-2 pt-4 border-t">
                <button type="button" onClick={closeModal} className="btn btn-outline">
                  Cancelar
                </button>
                <button type="submit" disabled={saving} className="btn btn-primary">
                  {saving ? 'Guardando...' : editingPlan ? 'Actualizar' : 'Crear Plan'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};