import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { usePlans } from '@/hooks/usePlans';
import { usePaymentAccounts } from '@/hooks/usePaymentAccounts';
import { apiService } from '@/services/api';
import type { PaymentFormData, PaymentMethod } from '@/types';
import toast from 'react-hot-toast';

interface PaymentFormProps {
  businessId: string;
  clientId: string;
  clientName: string;
  currentPlanId: string;
  branchId: string;
  initialAmount?: number;
  onSuccess: (receiptNumber?: string) => void;
  onCancel: () => void;
  isModal?: boolean;
}

export const PaymentForm: React.FC<PaymentFormProps> = ({
  businessId,
  clientId,
  clientName,
  currentPlanId,
  branchId,
  initialAmount,
  onSuccess,
  onCancel,
  isModal = false
}) => {
  const { plans } = usePlans(businessId);
  const { accounts } = usePaymentAccounts(businessId);

  const [planId, setPlanId] = useState<string>(currentPlanId || '');
  const [amount, setAmount] = useState<number>(initialAmount || 0);
  const [method, setMethod] = useState<PaymentMethod>('cash');
  const [methodDetails, setMethodDetails] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split('T')[0]);

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100);
  };

  const getPlanName = (id: string) => {
    const plan = plans.find(p => p.id === id);
    return plan ? plan.name : id;
  };

  useEffect(() => {
    if (currentPlanId) setPlanId(currentPlanId);
  }, [currentPlanId]);

  useEffect(() => {
    if (initialAmount !== undefined) setAmount(initialAmount);
  }, [initialAmount]);

  const handlePlanChange = (planIdValue: string) => {
    const plan = plans.find(p => p.id === planIdValue);
    setPlanId(planIdValue);
    if (plan) {
      // Usar precio por método actual si existe
      const methodPrice = plan.pricesByMethod?.[method];
      setAmount(methodPrice || plan.price);
    }
  };

  const handleMethodChange = (newMethod: string) => {
    setMethod(newMethod as PaymentMethod);
    setMethodDetails({});
    // Autocompletar monto según precio por método del plan seleccionado
    const plan = plans.find(p => p.id === planId);
    if (plan) {
      const methodPrice = plan.pricesByMethod?.[newMethod];
      setAmount(methodPrice || plan.price);
    }
  };

  const updateMethodDetail = (key: string, value: string) => {
    setMethodDetails(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId || !method || !planId) return;

    try {
      setLoading(true);
      const payload: PaymentFormData = {
        clientId,
        amount,
        method,
        membershipPlanId: planId,
        branchId,
        methodDetails,
        paymentDate,
        paymentAccountId: methodDetails.destinationAccountId || undefined
      };
      const response = await apiService.createPayment(payload);
      if (response.success) {
        toast.success('Pago registrado correctamente');
        onSuccess(response.data?.receiptNumber);
      }
    } catch (err: any) {
      toast.error(err.message || 'Error registrando pago');
    } finally {
      setLoading(false);
    }
  };

  const formContent = (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Cliente</label>
        <input type="text" value={clientName} className="input bg-gray-50" disabled />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Plan</label>
        <select
          value={planId}
          onChange={e => handlePlanChange(e.target.value)}
          className="input"
          required
        >
          <option value="">Seleccionar plan</option>
          {plans.map(plan => (
            <option key={plan.id} value={plan.id}>{plan.name} - {formatCurrency(plan.price)}</option>
          ))}
        </select>
        {planId && (
          <p className="mt-1 text-sm text-blue-600">
            Plan: {getPlanName(planId)} — {formatCurrency(plans.find(p => p.id === planId)?.price || 0)}
          </p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Monto (USD)</label>
        <input
          type="number"
          value={(amount || 0) / 100}
          className="input bg-gray-50"
          min="1"
          step="0.01"
          readOnly
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Fecha de Pago</label>
        <input
          type="date"
          value={paymentDate}
          onChange={e => setPaymentDate(e.target.value)}
          className="input"
          max={new Date().toISOString().split('T')[0]}
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Método de Pago</label>
        <select
          value={method}
          onChange={e => handleMethodChange(e.target.value)}
          className="input"
          required
        >
          <option value="">Seleccionar método</option>
          <option value="cash">Efectivo</option>
          {accounts.filter(a => a.type === 'zelle').length > 0 && <option value="zelle">Zelle</option>}
          {accounts.filter(a => a.type === 'pago_movil').length > 0 && <option value="pago_movil">Pago Móvil</option>}
          {accounts.filter(a => a.type === 'bank').length > 0 && <option value="transfer">Transferencia</option>}
        </select>
      </div>

      {method === 'zelle' && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email del quien pag&oacute;</label>
            <input
              type="email"
              value={methodDetails.senderEmail || ''}
              onChange={e => updateMethodDetail('senderEmail', e.target.value)}
              className="input"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cuenta Zelle destino</label>
            <select
              value={methodDetails.destinationAccountId || ''}
              onChange={e => updateMethodDetail('destinationAccountId', e.target.value)}
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

      {method === 'pago_movil' && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono que envió</label>
            <input
              type="tel"
              value={methodDetails.phoneSender || ''}
              onChange={e => updateMethodDetail('phoneSender', e.target.value)}
              className="input"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Código de confirmación</label>
            <input
              type="text"
              value={methodDetails.paymentCode || ''}
              onChange={e => updateMethodDetail('paymentCode', e.target.value)}
              className="input"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cuenta pago móvil destino</label>
            <select
              value={methodDetails.destinationAccountId || ''}
              onChange={e => updateMethodDetail('destinationAccountId', e.target.value)}
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

      {method === 'card' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Últimos 4 dígitos</label>
          <input
            type="text"
            maxLength={4}
            value={methodDetails.cardLast4 || ''}
            onChange={e => updateMethodDetail('cardLast4', e.target.value)}
            className="input"
            required
          />
        </div>
      )}

      {method === 'transfer' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Referencia</label>
          <input
            type="text"
            value={methodDetails.reference || ''}
            onChange={e => updateMethodDetail('reference', e.target.value)}
            className="input"
            required
          />
        </div>
      )}

      <div className="flex justify-end gap-2 pt-4 border-t">
        <button type="button" onClick={onCancel} className="btn btn-outline">
          Cancelar
        </button>
        <button type="submit" disabled={loading} className="btn btn-primary">
          {loading ? 'Registrando...' : 'Registrar Pago'}
        </button>
      </div>
    </form>
  );

  if (!isModal) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Registrar Pago</h3>
          <p className="card-description">Completa los datos del pago para {clientName}</p>
        </div>
        <div className="card-content">
          {formContent}
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        <div className="flex justify-between items-center p-4 border-b">
          <h3 className="text-lg font-semibold">Registrar Pago</h3>
          <button onClick={onCancel} className="btn btn-ghost btn-sm">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-4">
          {formContent}
        </div>
      </div>
    </div>
  );
};

export default PaymentForm;
