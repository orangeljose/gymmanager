import React, { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Edit2, CreditCard, Phone, Mail, MapPin, X, AlertCircle } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useClients } from '@/hooks/useClients';
import { usePlans } from '@/hooks/usePlans';
import { usePaymentAccounts } from '@/hooks/usePaymentAccounts';
import { apiService } from '@/services/api';
import type { Client, Payment, PaymentFormData } from '@/types';
import toast from 'react-hot-toast';

export const ClientDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { getClient, getClientPayments } = useClients(user?.businessId || '');
  const { plans } = usePlans(user?.businessId || '');
  const { accounts } = usePaymentAccounts(user?.businessId || '');
  const [client, setClient] = useState<Client | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [paymentForm, setPaymentForm] = useState<Partial<PaymentFormData>>({});

  useEffect(() => {
    if (!id) return;
    const loadData = async () => {
      setLoading(true);
      const [clientData, paymentsData] = await Promise.all([
        getClient(id),
        getClientPayments(id)
      ]);
      if (clientData) setClient(clientData);
      if (paymentsData) setPayments(paymentsData);
      setLoading(false);
    };
    loadData();
  }, [id]);

  const getDaysRemaining = (membershipEnd: string) => {
    const today = new Date();
    const end = new Date(membershipEnd);
    return Math.ceil((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  };

  const getMembershipProgress = () => {
    if (!client) return 0;
    const start = new Date(client.membershipStart).getTime();
    const end = new Date(client.membershipEnd).getTime();
    const now = Date.now();
    if (now >= end) return 100;
    if (now <= start) return 0;
    return Math.round(((now - start) / (end - start)) * 100);
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100);
  };

  const formatDate = (d: string) => new Date(d).toLocaleDateString('es-VE', { day: '2-digit', month: 'short', year: 'numeric' });

  const getPlanName = (planId: string) => {
    const plan = plans.find(p => p.id === planId);
    return plan ? plan.name : planId;
  };

  const getSelectedPlan = () => {
    return plans.find(p => p.id === (paymentForm.membershipPlanId || client?.membershipPlanId));
  };

  const handleOpenPaymentModal = () => {
    const selectedPlan = getSelectedPlan();
    setPaymentForm({
      clientId: client?.id,
      membershipPlanId: client?.membershipPlanId,
      branchId: client?.branchId,
      amount: selectedPlan?.price || 0,
      method: 'cash',
      methodDetails: {}
    });
    setShowPaymentModal(true);
  };

  const handlePaymentMethodChange = (method: string) => {
    setPaymentForm(prev => ({
      ...prev,
      method: method as any,
      methodDetails: {}
    }));
  };

  const handleRegisterPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!client || !paymentForm.method || !paymentForm.membershipPlanId) return;
    try {
      setPaymentLoading(true);
      const payload: PaymentFormData = {
        clientId: client.id,
        amount: paymentForm.amount || 0,
        method: paymentForm.method,
        membershipPlanId: paymentForm.membershipPlanId,
        branchId: client.branchId,
        methodDetails: paymentForm.methodDetails || {}
      };
      const response = await apiService.createPayment(payload);
      if (response.success) {
        toast.success('Pago registrado correctamente');
        const updatedPayments = await getClientPayments(client.id);
        if (updatedPayments) setPayments(updatedPayments);
        const updatedClient = await getClient(client.id);
        if (updatedClient) setClient(updatedClient);
        setShowPaymentModal(false);
      }
    } catch (err: any) {
      toast.error(err.message || 'Error registrando pago');
    } finally {
      setPaymentLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="loading-spinner h-10 w-10" /></div>;
  }

  if (!client) {
    return (
      <div className="p-6 text-center">
        <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Cliente no encontrado</h3>
        <Link to="/clients" className="btn btn-primary mt-4">Volver a clientes</Link>
      </div>
    );
  }

  const daysRemaining = getDaysRemaining(client.membershipEnd);
  const progress = getMembershipProgress();

  return (
    <div className="p-6">
      <div className="mb-6">
        <Link to="/clients" className="btn btn-ghost btn-sm mb-4">
          <ArrowLeft className="h-4 w-4 mr-1" /> Volver a clientes
        </Link>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{client.name}</h1>
            <div className="flex items-center gap-3 mt-2">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                client.status === 'active' ? 'bg-green-100 text-green-800' :
                  client.status === 'expired' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
              }`}>
                {client.status === 'active' ? 'Al día' : client.status === 'expired' ? 'Vencido' : 'Suspendido'}
              </span>
              <span className="text-sm text-gray-500">
                Registrado el {formatDate(client.createdAt)}
              </span>
            </div>
          </div>
          {(user?.role === 'super_admin' || user?.role === 'admin') && (
            <Link to={`/clients/${client.id}/edit`} className="btn btn-outline">
              <Edit2 className="h-4 w-4 mr-2" /> Editar
            </Link>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Membresía</h3>
            <div className="mb-4">
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium">{getPlanName(client.membershipPlanId)}</span>
                <span className="text-gray-500">{formatCurrency(getSelectedPlan()?.price || 0)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${daysRemaining < 0 ? 'bg-red-500' : daysRemaining <= 7 ? 'bg-yellow-500' : 'bg-primary-500'}`}
                  style={{ width: `${Math.min(progress, 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs mt-1 text-gray-500">
                <span>{formatDate(client.membershipStart)}</span>
                <span>
                  {daysRemaining < 0 ? `Vencio hace ${Math.abs(daysRemaining)} días` :
                    daysRemaining === 0 ? 'Vence hoy' :
                      `${daysRemaining} días restantes`}
                </span>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Historial de Pagos</h3>
              {user?.role !== 'trainer' && (
                <button onClick={handleOpenPaymentModal} className="btn btn-primary btn-sm">
                  <CreditCard className="h-4 w-4 mr-1" /> Registrar Pago
                </button>
              )}
            </div>
            {payments.length === 0 ? (
              <p className="text-gray-500 text-center py-6">No hay pagos registrados</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b">
                    <tr>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2">Fecha</th>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2">Plan</th>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2">Monto</th>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2">Método</th>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2">Recibo</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {payments.map((payment) => (
                      <tr key={payment.id}>
                        <td className="py-3 text-sm">{formatDate(payment.createdAt)}</td>
                        <td className="py-3 text-sm">{getPlanName(payment.membershipPlanId)}</td>
                        <td className="py-3 text-sm font-medium">{formatCurrency(payment.amount)}</td>
                        <td className="py-3 text-sm capitalize">{payment.method}</td>
                        <td className="py-3 text-sm text-gray-500">{payment.receiptNumber}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Datos Personales</h3>
            <div className="space-y-3">
              <div className="flex items-center">
                <Mail className="h-4 w-4 text-gray-400 mr-3" />
                <div>
                  <div className="text-xs text-gray-500">Email</div>
                  <div className="text-sm text-gray-900">{client.email}</div>
                </div>
              </div>
              <div className="flex items-center">
                <Phone className="h-4 w-4 text-gray-400 mr-3" />
                <div>
                  <div className="text-xs text-gray-500">Teléfono</div>
                  <div className="text-sm text-gray-900">{client.phone}</div>
                </div>
              </div>
              {client.documentId && (
                <div className="flex items-center">
                  <MapPin className="h-4 w-4 text-gray-400 mr-3" />
                  <div>
                    <div className="text-xs text-gray-500">Cédula</div>
                    <div className="text-sm text-gray-900">{client.documentId}</div>
                  </div>
                </div>
              )}
            </div>
            {client.notes && (
              <div className="mt-4 pt-4 border-t">
                <div className="text-xs text-gray-500 mb-1">Notas</div>
                <div className="text-sm text-gray-700">{client.notes}</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {showPaymentModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="flex justify-between items-center p-4 border-b">
              <h3 className="text-lg font-semibold">Registrar Pago</h3>
              <button onClick={() => setShowPaymentModal(false)} className="btn btn-ghost btn-sm">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleRegisterPayment} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cliente</label>
                <input type="text" value={client.name} className="input bg-gray-50" disabled />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Plan</label>
                <select
                  value={paymentForm.membershipPlanId}
                  onChange={e => {
                    const plan = plans.find(p => p.id === e.target.value);
                    setPaymentForm(prev => ({ ...prev, membershipPlanId: e.target.value, amount: plan?.price }));
                  }}
                  className="input"
                  required
                >
                  <option value="">Seleccionar plan</option>
                  {plans.map(plan => (
                    <option key={plan.id} value={plan.id}>{plan.name} - {formatCurrency(plan.price)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Monto (USD)</label>
                <input
                  type="number"
                  value={(paymentForm.amount || 0) / 100}
                  onChange={e => setPaymentForm(prev => ({ ...prev, amount: Math.round(parseFloat(e.target.value || '0') * 100) }))}
                  className="input"
                  step="0.01"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Método de Pago</label>
                <select
                  value={paymentForm.method}
                  onChange={e => handlePaymentMethodChange(e.target.value)}
                  className="input"
                  required
                >
                  <option value="">Seleccionar método</option>
                  <option value="cash">Efectivo</option>
                  <option value="card">Tarjeta</option>
                  <option value="transfer">Transferencia</option>
                  <option value="zelle">Zelle</option>
                  <option value="pago_movil">Pago Móvil</option>
                  <option value="other">Otro</option>
                </select>
              </div>

              {paymentForm.method === 'zelle' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email del quien pag&oacute;</label>
                    <input
                      type="email"
                      value={paymentForm.methodDetails?.senderEmail || ''}
                      onChange={e => setPaymentForm(prev => ({
                        ...prev,
                        methodDetails: { ...prev.methodDetails, senderEmail: e.target.value }
                      }))}
                      className="input"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cuenta Zelle destino</label>
                    <select
                      value={(paymentForm.methodDetails as any)?.destinationAccountId || ''}
                      onChange={e => setPaymentForm(prev => ({
                        ...prev,
                        methodDetails: { ...prev.methodDetails, destinationAccountId: e.target.value }
                      }))}
                      className="input"
                    >
                      <option value="">Seleccionar cuenta</option>
                      {accounts.filter(a => a.type === 'zelle').map(acc => (
                        <option key={acc.id} value={acc.id}>{acc.label}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {paymentForm.method === 'pago_movil' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono que envió</label>
                    <input
                      type="tel"
                      value={paymentForm.methodDetails?.phoneSender || ''}
                      onChange={e => setPaymentForm(prev => ({
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
                      value={paymentForm.methodDetails?.paymentCode || ''}
                      onChange={e => setPaymentForm(prev => ({
                        ...prev,
                        methodDetails: { ...prev.methodDetails, paymentCode: e.target.value }
                      }))}
                      className="input"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cuenta pago móvil destino</label>
                    <select
                      value={(paymentForm.methodDetails as any)?.destinationAccountId || ''}
                      onChange={e => setPaymentForm(prev => ({
                        ...prev,
                        methodDetails: { ...prev.methodDetails, destinationAccountId: e.target.value }
                      }))}
                      className="input"
                    >
                      <option value="">Seleccionar cuenta</option>
                      {accounts.filter(a => a.type === 'pago_movil').map(acc => (
                        <option key={acc.id} value={acc.id}>{acc.label}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {paymentForm.method === 'card' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Últimos 4 dígitos</label>
                  <input
                    type="text"
                    maxLength={4}
                    value={paymentForm.methodDetails?.cardLast4 || ''}
                    onChange={e => setPaymentForm(prev => ({
                      ...prev,
                      methodDetails: { ...prev.methodDetails, cardLast4: e.target.value }
                    }))}
                    className="input"
                    required
                  />
                </div>
              )}

              {paymentForm.method === 'transfer' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Referencia</label>
                  <input
                    type="text"
                    value={paymentForm.methodDetails?.reference || ''}
                    onChange={e => setPaymentForm(prev => ({
                      ...prev,
                      methodDetails: { ...prev.methodDetails, reference: e.target.value }
                    }))}
                    className="input"
                    required
                  />
                </div>
              )}

              <div className="flex justify-end gap-2 pt-4 border-t">
                <button type="button" onClick={() => setShowPaymentModal(false)} className="btn btn-outline">
                  Cancelar
                </button>
                <button type="submit" disabled={paymentLoading} className="btn btn-primary">
                  {paymentLoading ? 'Registrando...' : 'Registrar Pago'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};