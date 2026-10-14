import React, { useEffect, useState } from 'react';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';
import { X } from 'lucide-react';
import type { Product, ProductCategory, ProductFormData } from '@/types';

// Etiquetas de categoría de producto (tema GoatGym).
export const PRODUCT_CATEGORY_META: Record<ProductCategory, { label: string; badge: string }> = {
  supplement: { label: 'Suplemento', badge: 'bg-purple-100 text-purple-800' },
  drink: { label: 'Bebida', badge: 'bg-teal-100 text-teal-800' },
  apparel: { label: 'Ropa', badge: 'bg-blue-100 text-blue-800' },
  accessory: { label: 'Accesorio', badge: 'bg-amber-100 text-amber-800' },
  other: { label: 'Otro', badge: 'bg-gray-100 text-gray-800' },
};

export const PRODUCT_CATEGORIES = Object.keys(PRODUCT_CATEGORY_META) as ProductCategory[];

/** centavos → dólares con 2 decimales */
export const formatDollars = (cents: number): string =>
  `$${((cents || 0) / 100).toFixed(2)}`;

export type StockLevel = 'ok' | 'low' | 'out';

/** Semáforo de stock: verde (ok) / amarillo (bajo) / rojo (agotado). */
export const stockStatus = (
  product: Pick<Product, 'stockQty' | 'lowStockThreshold'>
): { level: StockLevel; label: string; badge: string; dot: string } => {
  const qty = product.stockQty ?? 0;
  const threshold = product.lowStockThreshold ?? 5;
  if (qty <= 0) {
    return { level: 'out', label: 'Agotado', badge: 'bg-red-100 text-red-800', dot: 'bg-red-500' };
  }
  if (qty <= threshold) {
    return { level: 'low', label: 'Stock bajo', badge: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500' };
  }
  return { level: 'ok', label: 'Disponible', badge: 'bg-green-100 text-green-800', dot: 'bg-green-500' };
};

interface ProductFormState {
  name: string;
  category: ProductCategory;
  cost: string;         // dólares
  salePrice: string;    // dólares
  stockQty: string;     // stock inicial (solo create)
  lowStockThreshold: string;
}

const emptyForm = (): ProductFormState => ({
  name: '',
  category: 'supplement',
  cost: '',
  salePrice: '',
  stockQty: '0',
  lowStockThreshold: '5',
});

interface ProductFormProps {
  open: boolean;
  initial?: Product | null;
  businessId?: string;
  onClose: () => void;
  onSaved: (product: Product) => void;
}

export const ProductForm: React.FC<ProductFormProps> = ({
  open, initial, businessId, onClose, onSaved,
}) => {
  const [form, setForm] = useState<ProductFormState>(emptyForm());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setForm({
        name: initial.name,
        category: initial.category,
        cost: (initial.costPriceCents / 100).toFixed(2),
        salePrice: (initial.salePriceCents / 100).toFixed(2),
        stockQty: String(initial.stockQty ?? 0),
        lowStockThreshold: String(initial.lowStockThreshold ?? 5),
      });
    } else {
      setForm(emptyForm());
    }
  }, [open, initial]);

  if (!open) return null;

  const set = <K extends keyof ProductFormState>(key: K, value: ProductFormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!form.name.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }

    const cost = Number(form.cost);
    if (!Number.isFinite(cost) || cost < 0) {
      toast.error('El costo debe ser mayor o igual a 0');
      return;
    }
    const salePrice = Number(form.salePrice);
    if (!Number.isFinite(salePrice) || salePrice <= 0) {
      toast.error('El precio de venta debe ser mayor que 0');
      return;
    }
    const threshold = Number(form.lowStockThreshold);
    if (!Number.isInteger(threshold) || threshold < 0) {
      toast.error('El umbral de stock bajo debe ser un entero >= 0');
      return;
    }

    const payload: ProductFormData = {
      name: form.name.trim(),
      category: form.category,
      costPriceCents: Math.round(cost * 100),
      salePriceCents: Math.round(salePrice * 100),
      lowStockThreshold: threshold,
    };

    if (!initial) {
      const stockQty = Number(form.stockQty);
      if (!Number.isInteger(stockQty) || stockQty < 0) {
        toast.error('El stock inicial debe ser un entero >= 0');
        return;
      }
      payload.stockQty = stockQty;
    }

    try {
      setSaving(true);
      const response = initial
        ? await apiService.updateProduct(initial.id, payload)
        : await apiService.createProduct({ ...payload, businessId });

      if (response.success) {
        toast.success(initial ? 'Producto actualizado' : 'Producto creado');
        onSaved(response.data);
        onClose();
      }
    } catch (error: any) {
      toast.error(error.message || 'Error guardando producto');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-4 border-b sticky top-0 bg-white">
          <h3 className="text-lg font-semibold text-gray-900">
            {initial ? 'Editar Producto' : 'Nuevo Producto'}
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
              placeholder="Ej: Proteína Whey 1kg"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Categoría *</label>
            <select
              value={form.category}
              onChange={(e) => set('category', e.target.value as ProductCategory)}
              className="input"
            >
              {PRODUCT_CATEGORIES.map((c) => (
                <option key={c} value={c}>{PRODUCT_CATEGORY_META[c].label}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Costo (USD) *</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.cost}
                onChange={(e) => set('cost', e.target.value)}
                className="input"
                placeholder="Ej: 15.00"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Precio de venta (USD) *</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={form.salePrice}
                onChange={(e) => set('salePrice', e.target.value)}
                className="input"
                placeholder="Ej: 25.00"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {!initial && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Stock inicial</label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={form.stockQty}
                  onChange={(e) => set('stockQty', e.target.value)}
                  className="input"
                  placeholder="0"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Si es mayor que 0 se registra una compra inicial automática.
                </p>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Umbral stock bajo</label>
              <input
                type="number"
                min="0"
                step="1"
                value={form.lowStockThreshold}
                onChange={(e) => set('lowStockThreshold', e.target.value)}
                className="input"
                placeholder="5"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-4 border-t">
            <button type="button" onClick={onClose} className="btn btn-outline">
              Cancelar
            </button>
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? 'Guardando...' : initial ? 'Actualizar' : 'Crear Producto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
