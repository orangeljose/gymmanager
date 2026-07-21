import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ChevronRight, ChevronLeft } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useClients } from '@/hooks/useClients';
import { usePlans } from '@/hooks/usePlans';
import { usePaymentAccounts } from '@/hooks/usePaymentAccounts';
import { apiService } from '@/services/api';
import type { ClientFormData, PaymentFormDataCreate, Branch } from '@/types';
import toast from 'react-hot-toast';

export const ClientFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || "";
  const { createClient, updateClient, getClient } = useClients(effectiveBusinessId || '');
  const { plans, fetchPlans } = usePlans(effectiveBusinessId || '');
  const { accounts } = usePaymentAccounts(effectiveBusinessId || '');
  const [branches, setBranches] = useState<Branch[]>([]);

  const [step, setStep] = useState<1 | 2>(1);
  const [loading, setLoading] = useState(false);
  const [initLoading, setInitLoading] = useState(isEdit);

  const [clientData, setClientData] = useState<ClientFormData>({
    name: '',
    email: '',
    phone: '',
    documentId: '',
    branchId: user?.branchId || '',
    membershipPlanId: '',
    notes: '',
    businessId: effectiveBusinessId || ''
  });

  const [paymentData, setPaymentData] = useState<{
    method: string;
    membershipPlanId: string;
    amount: number;
    methodDetails: Record<string, any>;
  }>({
    method: 'cash',
    membershipPlanId: '',
    amount: 0,
    methodDetails: {}
  });

  useEffect(() => {
    if (effectiveBusinessId) {
      fetchPlans();
      apiService.getBranches(effectiveBusinessId).then(res => {
        if (res.success && res.data) setBranches(res.data);
      });
    }
  }, [effectiveBusinessId]);

  useEffect(() => {
    if (isEdit && id) {
      getClient(id).then(client => {
        if (client) {
          setClientData({
            name: client.name,
            email: client.email,
            phone: client.phone,
            documentId: client.documentId || '',
            branchId: client.branchId,
            membershipPlanId: client.membershipPlanId,
            notes: client.notes || ''
          });
          setPaymentData(prev => ({
            ...prev,
            membershipPlanId: client.membershipPlanId,
            amount: 0
          }));
        }
        setInitLoading(false);
      });
    }
  }, [id, isEdit]);

  const selectedPlan = plans.find(p => p.id === (paymentData.membershipPlanId || clientData.membershipPlanId));

  const handlePlanSelect = (planId: string) => {
    const plan = plans.find(p => p.id === planId);
    setClientData(prev => ({ ...prev, membershipPlanId: planId }));
    setPaymentData(prev => ({ ...prev, membershipPlanId: planId, amount: plan?.price || 0 }));
    setStep(2);
  };

  const handlePaymentMethodChange = (method: string) => {
    setPaymentData(prev => ({
      ...prev,
      method: method as any,
      methodDetails: {}
    }));
  };

  const handleSubmitClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientData.name || !clientData.email || !clientData.phone || !clientData.branchId || !clientData.membershipPlanId) {
      toast.error('Completa todos los campos requeridos');
      return;
    }

    try {
      setLoading(true);
      if (isEdit && id) {
        const result = await updateClient(id, clientData);
        if (result.success) {
          toast.success('Cliente actualizado');
          navigate(`/clients/${id}`);
        }
      } else {
        const result = await createClient(clientData);
        if (result.success) {
          toast.success('Cliente registrado');
          navigate(`/clients/${result.data?.id}`);
        } else {
          toast.error(result.error || 'Error al crear cliente');
        }
      }
    } catch (err: any) {
      toast.error(err.message || 'Error guardando cliente');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitWithPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientData.name || !clientData.email || !clientData.phone || !clientData.branchId || !clientData.membershipPlanId || !clientData.documentId) {
      toast.error('Completa todos los campos requeridos');
      return;
    }

    try {
      setLoading(true);

      let clientId: string;
      if (!isEdit) {
        const result = await createClient(clientData);
        if (!result.success) throw new Error(result.error?.message || 'Error creando cliente');
        if (!result.data?.id) throw new Error('No se pudo obtener client ID');
        clientId = result.data.id;
      } else {
        if (!id) throw new Error('Client ID is required');
        await updateClient(id, clientData);
        clientId = id;
      }

      const paymentPayload: PaymentFormDataCreate = {
        clientId,
        amount: paymentData.amount || 0,
        method: paymentData.method as any,
        membershipPlanId: paymentData.membershipPlanId || clientData.membershipPlanId,
        branchId: clientData.branchId,
        methodDetails: paymentData.methodDetails || {}
      };

      const paymentRes = await apiService.createPayment(paymentPayload);
      if (!paymentRes.success) throw new Error(paymentRes.error?.message || 'Error registrando pago');

      toast.success('Cliente registrado con pago');
      navigate(`/clients/${clientId}`);
    } catch (err: any) {
      toast.error(err.message || 'Error en el proceso');
    } finally {
      setLoading(false);
    }
  };

  if (initLoading) {
    return <div className="flex items-center justify-center h-64"><div className="loading-spinner h-10 w-10" /></div>;
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <Link to={id ? `/clients/${id}` : '/clients'} className="btn btn-ghost btn-sm mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" /> {id ? 'Volver al detalle' : 'Volver a clientes'}
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        {isEdit ? 'Editar Cliente' : 'Nuevo Cliente'}
      </h1>

      {!isEdit && (
        <div className="flex items-center mb-6">
          <div className={`flex items-center ${step === 1 ? 'text-primary-600' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
              step === 1 ? 'bg-primary-500 text-white' : 'bg-primary-100 text-primary-600'
            }`}>1</div>
            <span className="ml-2 font-medium">Datos Personales</span>
          </div>
          <ChevronRight className="h-5 w-5 text-gray-300 mx-3" />
          <div className={`flex items-center ${step === 2 ? 'text-primary-600' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
              step === 2 ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-400'
            }`}>2</div>
            <span className="ml-2 font-medium">Pago</span>
          </div>
        </div>
      )}

      {step === 1 && (
        <form onSubmit={isEdit ? handleSubmitClient : undefined} className="card">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre completo *</label>
              <input
                type="text"
                value={clientData.name}
                onChange={e => setClientData(prev => ({ ...prev, name: e.target.value }))}
                className="input"
                placeholder="Juan Pérez"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input
                  type="email"
                  value={clientData.email}
                  onChange={e => setClientData(prev => ({ ...prev, email: e.target.value }))}
                  className="input"
                  placeholder="juan@email.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono *</label>
                <input
                  type="tel"
                  value={clientData.phone}
                  onChange={e => setClientData(prev => ({ ...prev, phone: e.target.value }))}
                  className="input"
                  placeholder="+584141234567"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cédula / Documento <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={clientData.documentId || ''}
                  onChange={e => setClientData(prev => ({ ...prev, documentId: e.target.value }))}
                  className="input"
                  placeholder="V-30123456"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sucursal *</label>
                <select
                  value={clientData.branchId}
                  onChange={e => setClientData(prev => ({ ...prev, branchId: e.target.value }))}
                  className="input"
                  required
                >
                  <option value="">Seleccionar</option>
                  {branches.map(b => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Plan de Membresía *</label>
              <select
                value={clientData.membershipPlanId}
                onChange={e => handlePlanSelect(e.target.value)}
                className="input"
                required
              >
                <option value="">Seleccionar plan</option>
                {plans.map(plan => (
                  <option key={plan.id} value={plan.id}>
                    {plan.name} - ${(plan.price / 100).toFixed(2)} ({plan.durationDays} días)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Notas</label>
              <textarea
                value={clientData.notes || ''}
                onChange={e => setClientData(prev => ({ ...prev, notes: e.target.value }))}
                className="input"
                rows={2}
                placeholder="Notas adicionales..."
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-6 pt-4 border-t">
            {isEdit ? (
              <button type="submit" disabled={loading} className="btn btn-primary">
                {loading ? 'Guardando...' : 'Actualizar Cliente'}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
if (!clientData.name || !clientData.email || !clientData.phone || !clientData.branchId || !clientData.membershipPlanId || !clientData.documentId) {
                    toast.error('Completa todos los campos requeridos');
                    return;
                  }
                  setStep(2);
                }}
                className="btn btn-primary"
              >
                Continuar <ChevronRight className="h-4 w-4 ml-1" />
              </button>
            )}
          </div>
        </form>
      )}

      {step === 2 && !isEdit && (
        <div className="space-y-4">
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Resumen</h3>
            <div className="text-sm text-gray-600 space-y-1">
              <p><strong>Cliente:</strong> {clientData.name}</p>
              <p><strong>Plan:</strong> {selectedPlan?.name} - ${(selectedPlan?.price || 0) / 100}</p>
            </div>
          </div>

          <form onSubmit={handleSubmitWithPayment} className="card space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Registrar Pago</h3>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Método de Pago</label>
              <select
                value={paymentData.method}
                onChange={e => handlePaymentMethodChange(e.target.value)}
                className="input"
                required
              >
                <option value="">Seleccionar</option>
                <option value="cash">Efectivo</option>
                {accounts.filter(a => a.type === 'zelle').length > 0 && <option value="zelle">Zelle</option>}
                {accounts.filter(a => a.type === 'pago_movil').length > 0 && <option value="pago_movil">Pago Móvil</option>}
                {accounts.filter(a => a.type === 'bank').length > 0 && <option value="transfer">Transferencia</option>}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Monto (USD)</label>
              <input
                type="number"
                value={(paymentData.amount || selectedPlan?.price || 0) / 100}
                onChange={e => setPaymentData(prev => ({
                  ...prev,
                  amount: Math.round(parseFloat(e.target.value || '0') * 100)
                }))}
                className="input"
                step="0.01"
                required
              />
            </div>

              {paymentData.method === 'zelle' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email del quien pagó</label>
                    <input
                      type="email"
                      value={(paymentData.methodDetails as any)?.senderEmail || ''}
                      onChange={e => setPaymentData(prev => ({
                        ...prev,
                        methodDetails: { ...prev.methodDetails, senderEmail: e.target.value }
                      }))}
                      className="input"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cuenta Zelle</label>
                    <select
                      value={(paymentData.methodDetails as any)?.destinationAccountId || ''}
                      onChange={e => setPaymentData(prev => ({
                        ...prev,
                        methodDetails: { ...prev.methodDetails, destinationAccountId: e.target.value }
                      }))}
                      className="input"
                    >
                      <option value="">Seleccionar</option>
                      {accounts.filter(a => a.type === 'zelle').map(acc => (
                        <option key={acc.id} value={acc.id}>{acc.label}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {paymentData.method === 'pago_movil' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono que envió</label>
                    <input
                      type="tel"
                      value={(paymentData.methodDetails as any)?.phoneSender || ''}
                      onChange={e => setPaymentData(prev => ({
                        ...prev,
                        methodDetails: { ...prev.methodDetails, phoneSender: e.target.value }
                      }))}
                      className="input"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Código de confirmación</label>
                    <input
                      type="text"
                      value={(paymentData.methodDetails as any)?.paymentCode || ''}
                      onChange={e => setPaymentData(prev => ({
                        ...prev,
                        methodDetails: { ...prev.methodDetails, paymentCode: e.target.value }
                      }))}
                      className="input"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cuenta Pago Móvil</label>
                    <select
                      value={(paymentData.methodDetails as any)?.destinationAccountId || ''}
                      onChange={e => setPaymentData(prev => ({
                        ...prev,
                        methodDetails: { ...prev.methodDetails, destinationAccountId: e.target.value }
                      }))}
                      className="input"
                    >
                      <option value="">Seleccionar</option>
                      {accounts.filter(a => a.type === 'pago_movil').map(acc => (
                        <option key={acc.id} value={acc.id}>{acc.label}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {paymentData.method === 'card' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Últimos 4 dígitos de la tarjeta</label>
                  <input
                    type="text"
                    maxLength={4}
                    value={(paymentData.methodDetails as any)?.cardLast4 || ''}
                    onChange={e => setPaymentData(prev => ({
                      ...prev,
                      methodDetails: { ...prev.methodDetails, cardLast4: e.target.value }
                    }))}
                    className="input"
                    required
                  />
                </div>
              )}

              {paymentData.method === 'transfer' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Referencia</label>
                  <input
                    type="text"
                    value={(paymentData.methodDetails as any)?.reference || ''}
                    onChange={e => setPaymentData(prev => ({
                      ...prev,
                      methodDetails: { ...prev.methodDetails, reference: e.target.value }
                    }))}
                    className="input"
                    required
                  />
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-2 pt-4 border-t">
                <button type="button" onClick={() => setStep(1)} className="btn btn-outline">
                  <ChevronLeft className="h-4 w-4 mr-1" /> Atrás
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    handleSubmitClient(e as any);
                  }}
                  disabled={loading}
                  className="btn btn-outline"
                >
                  {loading ? 'Creando...' : 'Crear Cliente sin Pago'}
                </button>
                <button type="submit" disabled={loading} className="btn btn-primary">
                  {loading ? 'Procesando...' : 'Registrar Pago y Crear'}
                </button>
              </div>
            </form>
        </div>
      )}
    </div>
  );
};