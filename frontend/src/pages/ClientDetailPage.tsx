import React, { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Edit2, CreditCard, Phone, Mail, MapPin, AlertCircle, Clock, Trash2, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '@/hooks/useAuth';
import { useClients } from '@/hooks/useClients';
import { usePlans } from '@/hooks/usePlans';
import { usePaymentAccounts } from '@/hooks/usePaymentAccounts';
import { PaymentForm } from '@/components/PaymentForm';
import { apiService } from '@/services/api';
import type { Client, Payment } from '@/types';

export const ClientDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || "";
  const { getClient, getClientPayments } = useClients(effectiveBusinessId || '');
  const { plans } = usePlans(effectiveBusinessId || '');
  const { accounts } = usePaymentAccounts(effectiveBusinessId || '');
  const accountLookup = Object.fromEntries(accounts.map(a => [a.id, a.label || a.identifier]));
  const [client, setClient] = useState<Client | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Payment | null>(null);
  const [deleting, setDeleting] = useState(false);

  const canDeletePayment = user?.role === 'super_admin' || user?.role === 'admin' || user?.role === 'branch_admin';

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

  const toDate = (d: any): Date => {
    if (!d) return new Date();
    if (typeof d === 'string') return new Date(d);
    if (d.seconds) return new Date(d.seconds * 1000);
    if (d instanceof Date) return d;
    return new Date(d);
  };

  const getDaysRemaining = (membershipEnd: any) => {
    const today = new Date();
    const end = toDate(membershipEnd);
    return Math.ceil((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  };

  const getMembershipProgress = () => {
    if (!client) return 0;
    const start = toDate(client.membershipStart).getTime();
    const end = toDate(client.membershipEnd).getTime();
    const now = Date.now();
    if (now >= end) return 100;
    if (now <= start) return 0;
    if (end <= start) return 0; // Evitar división por 0
    return Math.round(((now - start) / (end - start)) * 100);
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100);
  };

  const formatDate = (d: any) => {
    if (!d) return 'N/A';
    let date: Date;
    if (typeof d === 'string') {
      // Si es solo fecha (YYYY-MM-DD), agregar T00:00 para evitar timezone shift
      if (/^\d{4}-\d{2}-\d{2}$/.test(d)) d = d + 'T12:00:00';
      date = new Date(d);
    } else if (d.seconds) {
      date = new Date(d.seconds * 1000);
    } else {
      date = new Date(d);
    }
    return date.toLocaleDateString('es-VE', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const methodLabels: Record<string, string> = {
    cash: 'Efectivo',
    card: 'Tarjeta',
    transfer: 'Transferencia',
    zelle: 'Zelle',
    pago_movil: 'Pago Móvil',
    binance: 'Binance',
    other: 'Otro'
  };
  const getMethodLabel = (m: string) => methodLabels[m] || m;

  const getPlanName = (planId: string) => {
    const plan = plans.find(p => p.id === planId);
    return plan ? plan.name : planId;
  };

  const handleOpenPaymentModal = () => {
    setShowPaymentModal(true);
  };

  const handlePaymentSuccess = async () => {
    if (!client) return;
    const updatedPayments = await getClientPayments(client.id);
    if (updatedPayments) setPayments(updatedPayments);
    const updatedClient = await getClient(client.id);
    if (updatedClient) setClient(updatedClient);
    setShowPaymentModal(false);
  };

  const handleDeletePayment = async () => {
    if (!deleteTarget) return;
    try {
      setDeleting(true);
      const response = await apiService.deletePayment(deleteTarget.id);
      if (response.success) {
        toast.success('Pago eliminado correctamente');
        setDeleteTarget(null);
        if (client) {
          const updatedPayments = await getClientPayments(client.id);
          if (updatedPayments) setPayments(updatedPayments);
          const updatedClient = await getClient(client.id);
          if (updatedClient) setClient(updatedClient);
        }
      } else {
        toast.error(response.error?.message || 'Error al eliminar el pago');
      }
    } catch (err: any) {
      toast.error(err.message || 'Error al eliminar el pago');
    } finally {
      setDeleting(false);
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
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                client.status === 'active' ? 'bg-green-100 text-green-800' :
                  client.status === 'expired' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
              }`}>
                {client.status === 'active' ? 'Al día' : client.status === 'expired' ? 'Vencido' : 'Suspendido'}
              </span>
              {client.status === 'active' && daysRemaining >= 0 && daysRemaining <= 7 && (
                <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-bold ${
                  daysRemaining === 0 ? 'bg-red-500 text-white' : 'bg-yellow-500 text-white'
                }`}>
                  <Clock className="h-3 w-3" />
                  {daysRemaining === 0 ? 'Vence hoy' : `Vence en ${daysRemaining} días`}
                </span>
              )}
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
                <span className="text-gray-500">{formatCurrency(plans.find(p => p.id === client.membershipPlanId)?.price || 0)}</span>
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
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2 hidden sm:table-cell">Fecha</th>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2 hidden sm:table-cell">Plan</th>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2 hidden sm:table-cell">Monto</th>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2 hidden sm:table-cell">Método</th>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2 hidden sm:table-cell">Cuenta / Registró</th>
                      <th className="text-left text-xs font-medium text-gray-500 uppercase py-2 hidden sm:table-cell">Recibo</th>
                      {canDeletePayment && (
                        <th className="text-right text-xs font-medium text-gray-500 uppercase py-2 hidden sm:table-cell">Acciones</th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {payments.map((payment) => (
                      <tr key={payment.id}>
                        <td className="py-3 text-sm hidden sm:table-cell">{formatDate(payment.paymentDate || payment.createdAt)}</td>
                        <td className="py-3 text-sm hidden sm:table-cell">{getPlanName(payment.membershipPlanId)}</td>
                        <td className="py-3 text-sm font-medium hidden sm:table-cell">{formatCurrency(payment.amount)}</td>
                        <td className="py-3 text-sm hidden sm:table-cell">{getMethodLabel(payment.method)}</td>
                        <td className="py-3 text-sm text-gray-500 hidden sm:table-cell">
                          {payment.method === 'cash'
                            ? payment.registeredByName || '-'
                            : accountLookup[payment.paymentAccountId || ''] || payment.registeredByName || '-'}
                        </td>
                        <td className="py-3 text-sm text-gray-500 hidden sm:table-cell">{payment.receiptNumber}</td>
                        {canDeletePayment && (
                          <td className="py-3 hidden sm:table-cell">
                            <div className="flex justify-end">
                              <button
                                onClick={() => setDeleteTarget(payment)}
                                className="btn btn-ghost btn-sm text-red-600 hover:text-red-800"
                                title="Eliminar pago"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        )}
                        {/* Mobile card view */}
                        <td className="py-3 sm:hidden" colSpan={canDeletePayment ? 7 : 6}>
                          <div className="space-y-1">
                            <div className="flex justify-between">
                              <span className="text-xs text-gray-500">Fecha</span>
                              <span className="text-sm">{formatDate(payment.paymentDate || payment.createdAt)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-xs text-gray-500">Plan</span>
                              <span className="text-sm">{getPlanName(payment.membershipPlanId)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-xs text-gray-500">Monto</span>
                              <span className="text-sm font-medium">{formatCurrency(payment.amount)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-xs text-gray-500">Método</span>
                              <span className="text-sm">{getMethodLabel(payment.method)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-xs text-gray-500">Cuenta / Registró</span>
                              <span className="text-sm text-gray-500">
                                {payment.method === 'cash'
                                  ? payment.registeredByName || '-'
                                  : accountLookup[payment.paymentAccountId || ''] || payment.registeredByName || '-'}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-xs text-gray-500">Recibo</span>
                              <span className="text-sm text-gray-500">{payment.receiptNumber}</span>
                            </div>
                            {canDeletePayment && (
                              <div className="flex justify-end pt-1">
                                <button
                                  onClick={() => setDeleteTarget(payment)}
                                  className="btn btn-ghost btn-sm text-red-600 hover:text-red-800"
                                >
                                  <Trash2 className="h-4 w-4 mr-1" /> Eliminar
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
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
            {(() => {
              const missing: string[] = [];
              if (!client.email) missing.push('email');
              if (!client.phone) missing.push('teléfono');
              if (!client.documentId) missing.push('cédula');
              if (missing.length > 0) {
                return (
                  <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800">
                      ⚠ A este cliente le faltan: <strong>{missing.join(', ')}</strong>. Completá estos datos cuando sea posible.
                    </p>
                  </div>
                );
              }
              return null;
            })()}
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
        <PaymentForm
          businessId={effectiveBusinessId}
          clientId={client.id}
          clientName={client.name}
          currentPlanId={client.membershipPlanId}
          branchId={client.branchId}
          initialAmount={plans.find(p => p.id === client.membershipPlanId)?.price}
          onSuccess={handlePaymentSuccess}
          onCancel={() => setShowPaymentModal(false)}
          isModal={true}
        />
      )}

      {deleteTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="flex justify-between items-center p-4 border-b">
              <h3 className="text-lg font-semibold">Eliminar Pago</h3>
              <button onClick={() => setDeleteTarget(null)} className="btn btn-ghost btn-sm">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4">
              <p className="text-sm text-gray-700 mb-2">
                ¿Estás seguro de eliminar el pago de <strong>{formatCurrency(deleteTarget.amount)}</strong> del {formatDate(deleteTarget.paymentDate || deleteTarget.createdAt)}?
              </p>
              <p className="text-sm text-gray-500 mb-4">
                Recibo <strong>{deleteTarget.receiptNumber}</strong> — Se recalculará la membresía del cliente.
              </p>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setDeleteTarget(null)}
                  className="btn btn-outline"
                  disabled={deleting}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeletePayment}
                  disabled={deleting}
                  className="btn btn-danger"
                >
                  {deleting ? 'Eliminando...' : 'Eliminar Pago'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};