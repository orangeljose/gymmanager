import React, { useEffect, useState } from 'react';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { usePaymentAccounts } from '@/hooks/usePaymentAccounts';
import { PAYMENT_METHODS, PAYMENT_METHOD_LABELS } from '@/components/ExpenseForm';
import toast from 'react-hot-toast';
import { X } from 'lucide-react';
import type { MovementType, PaymentMethod, Product, ProductMovement, ProductMovementFormData } from '@/types';

const todayIso = () => new Date().toISOString().slice(0, 10);

const ADMIN_ROLES = ['super_admin', 'admin', 'branch_admin'];
const SALE_ROLES = ['super_admin', 'admin', 'branch_admin', 'cashier'];

// Métodos que requieren cuenta de destino (payment_accounts por tipo).
const ACCOUNT_METHODS: PaymentMethod[] = ['zelle', 'pago_movil', 'binance'];

interface MovementFormState {
  type: MovementType;
  qty: string;
  unitPrice: string;   // dólares; vacío en venta ⇒ usa salePriceCents
  date: string;
  note: string;
  updateCostPrice: boolean;
  method: PaymentMethod;
  paymentAccountId: string;
}

interface ProductMovementModalProps {
  open: boolean;
  product: Product;
  onClose: () => void;
  onSaved: (movement: ProductMovement) => void;
}

export const ProductMovementModal: React.FC<ProductMovementModalProps> = ({
  open, product, onClose, onSaved,
}) => {
  const { user } = useAuth();
  const canPurchase = !!user && ADMIN_ROLES.includes(user.role);
  const canSell = !!user && SALE_ROLES.includes(user.role);
  const { accounts } = usePaymentAccounts(product.businessId || '');

  const [form, setForm] = useState<MovementFormState>(() => ({
    type: 'sale',
    qty: '1',
    unitPrice: '',
    date: todayIso(),
    note: '',
    updateCostPrice: false,
    method: 'cash',
    paymentAccountId: '',
  }));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm({
      // Por defecto venta; si el rol no puede vender, arranca en compra.
      type: canSell ? 'sale' : 'purchase',
      qty: '1',
      unitPrice: '',
      date: todayIso(),
      note: '',
      updateCostPrice: false,
      method: 'cash',
      paymentAccountId: '',
    });
  }, [open, canSell]);

  if (!open) return null;

  const set = <K extends keyof MovementFormState>(key: K, value: MovementFormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const qty = Number(form.qty);
    if (!Number.isInteger(qty) || qty <= 0) {
      toast.error('La cantidad debe ser un entero mayor que 0');
      return;
    }

    if (form.type === 'sale' && qty > (product.stockQty ?? 0)) {
      toast.error('Stock insuficiente');
      return;
    }

    const payload: ProductMovementFormData = {
      type: form.type,
      qty,
      date: form.date || todayIso(),
      note: form.note.trim() || undefined,
      method: form.method,
      paymentAccountId: form.paymentAccountId || null,
    };

    if (form.unitPrice.trim()) {
      const price = Number(form.unitPrice);
      if (!Number.isFinite(price) || price < 0) {
        toast.error('El precio unitario debe ser mayor o igual a 0');
        return;
      }
      payload.unitPriceCents = Math.round(price * 100);
    } else if (form.type === 'purchase') {
      toast.error('El costo unitario es obligatorio en una compra');
      return;
    }

    if (form.type === 'purchase') {
      payload.updateCostPrice = form.updateCostPrice;
    }

    try {
      setSaving(true);
      const response = await apiService.createProductMovement(product.id, payload);
      if (response.success) {
        toast.success(form.type === 'sale' ? 'Venta registrada' : 'Compra registrada');
        onSaved(response.data);
        onClose();
      }
    } catch (error: any) {
      toast.error(error.message || 'Error registrando movimiento');
    } finally {
      setSaving(false);
    }
  };

  const salePriceDollars = (product.salePriceCents / 100).toFixed(2);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-4 border-b sticky top-0 bg-white">
          <h3 className="text-lg font-semibold text-gray-900">Registrar Movimiento</h3>
          <button onClick={onClose} className="btn btn-ghost btn-sm" type="button">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <p className="text-sm text-gray-600">
            <span className="font-medium text-gray-900">{product.name}</span>
            {' · '}Stock actual: <span className="font-medium">{product.stockQty ?? 0}</span>
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo *</label>
              <select
                value={form.type}
                onChange={(e) => set('type', e.target.value as MovementType)}
                className="input"
                disabled={!canSell && !canPurchase}
              >
                {canSell && <option value="sale">Venta</option>}
                {canPurchase && <option value="purchase">Compra</option>}
              </select>
              {!canPurchase && (
                <p className="text-xs text-gray-500 mt-1">Solo administradores pueden registrar compras.</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cantidad *</label>
              <input
                type="number"
                min="1"
                step="1"
                value={form.qty}
                onChange={(e) => set('qty', e.target.value)}
                className="input"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {form.type === 'sale' ? 'Precio unitario (USD)' : 'Costo unitario (USD) *'}
            </label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.unitPrice}
              onChange={(e) => set('unitPrice', e.target.value)}
              className="input"
              placeholder={form.type === 'sale' ? `Por defecto $${salePriceDollars}` : 'Ej: 15.00'}
              required={form.type === 'purchase'}
            />
            {form.type === 'sale' && (
              <p className="text-xs text-gray-500 mt-1">
                Si se deja vacío se usa el precio de venta (${salePriceDollars}).
              </p>
            )}
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

          {form.type === 'purchase' && (
            <label className="flex items-center text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.updateCostPrice}
                onChange={(e) => set('updateCostPrice', e.target.checked)}
                className="mr-2"
              />
              Actualizar el costo del producto con este precio
            </label>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nota</label>
            <input
              type="text"
              value={form.note}
              onChange={(e) => set('note', e.target.value)}
              className="input"
              placeholder="Detalle opcional"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Método de pago</label>
            <select
              value={form.method}
              onChange={(e) => set('method', e.target.value as PaymentMethod)}
              className="input"
            >
              {PAYMENT_METHODS.map((m) => (
                <option key={m} value={m}>{PAYMENT_METHOD_LABELS[m]}</option>
              ))}
            </select>
          </div>

          {ACCOUNT_METHODS.includes(form.method) && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cuenta {PAYMENT_METHOD_LABELS[form.method]} destino
              </label>
              <select
                value={form.paymentAccountId}
                onChange={(e) => set('paymentAccountId', e.target.value)}
                className="input"
              >
                <option value="">Seleccionar cuenta</option>
                {accounts.filter((a) => a.type === form.method).map((acc) => (
                  <option key={acc.id} value={acc.id}>{acc.label}</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-4 border-t">
            <button type="button" onClick={onClose} className="btn btn-outline">
              Cancelar
            </button>
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? 'Guardando...' : 'Registrar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
