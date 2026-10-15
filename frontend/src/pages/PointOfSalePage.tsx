import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { usePaymentAccounts } from '@/hooks/usePaymentAccounts';
import { apiService } from '@/services/api';
import { formatDollars } from '@/components/ProductForm';
import { PAYMENT_METHODS, PAYMENT_METHOD_LABELS } from '@/components/ExpenseForm';
import toast from 'react-hot-toast';
import {
  Search, ShoppingCart, Plus, Minus, Trash2, CheckCircle, Package, User, RotateCcw,
} from 'lucide-react';
import type { Client, PaymentMethod, Product, Sale, SaleCreateData } from '@/types';

// Métodos que requieren cuenta de destino (payment_accounts por tipo).
const ACCOUNT_METHODS: PaymentMethod[] = ['zelle', 'pago_movil', 'binance'];

interface CartItem {
  product: Product;
  qty: number;
}

interface SelectedClient {
  id: string;
  name: string;
}

export const PointOfSalePage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';
  const { accounts } = usePaymentAccounts(effectiveBusinessId);

  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [cart, setCart] = useState<CartItem[]>([]);
  const [method, setMethod] = useState<PaymentMethod>('cash');
  const [paymentAccountId, setPaymentAccountId] = useState('');

  const [clientSearch, setClientSearch] = useState('');
  const [clientResults, setClientResults] = useState<Client[]>([]);
  const [selectedClient, setSelectedClient] = useState<SelectedClient | null>(null);

  const [checkingOut, setCheckingOut] = useState(false);
  const [receipt, setReceipt] = useState<Sale | null>(null);

  const scoped = user?.role === 'super_admin' && effectiveBusinessId
    ? { businessId: effectiveBusinessId }
    : {};

  const loadProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.getProducts({ ...scoped, limit: 200 });
      if (response.success) setProducts(response.data);
    } catch (err: any) {
      setError(err.message || 'Error cargando productos');
    } finally {
      setLoading(false);
    }
  }, [user?.role, effectiveBusinessId]);

  useEffect(() => { loadProducts(); }, [loadProducts]);

  // Búsqueda de cliente (debounced, opcional).
  useEffect(() => {
    const term = clientSearch.trim();
    if (term.length < 2) {
      setClientResults([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const res = await apiService.getClients({ search: term, limit: 5 });
        if (res.success) setClientResults(res.data);
      } catch {
        /* búsqueda accesoria */
      }
    }, 300);
    return () => clearTimeout(t);
  }, [clientSearch]);

  const filteredProducts = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return products;
    return products.filter((p) => (p.name || '').toLowerCase().includes(q));
  }, [products, search]);

  const addToCart = (product: Product) => {
    setCart((prev) => {
      const existing = prev.find((i) => i.product.id === product.id);
      if (existing) {
        if (existing.qty >= (product.stockQty ?? 0)) return prev;
        return prev.map((i) =>
          i.product.id === product.id ? { ...i, qty: i.qty + 1 } : i
        );
      }
      return [...prev, { product, qty: 1 }];
    });
  };

  const decrement = (productId: string) => {
    setCart((prev) =>
      prev
        .map((i) => (i.product.id === productId ? { ...i, qty: i.qty - 1 } : i))
        .filter((i) => i.qty > 0)
    );
  };

  const removeFromCart = (productId: string) => {
    setCart((prev) => prev.filter((i) => i.product.id !== productId));
  };

  const totalCents = cart.reduce((sum, i) => sum + i.product.salePriceCents * i.qty, 0);

  const selectClient = (client: Client) => {
    setSelectedClient({ id: client.id, name: client.name });
    setClientSearch('');
    setClientResults([]);
  };

  const reset = () => {
    setCart([]);
    setReceipt(null);
    setSelectedClient(null);
    setClientSearch('');
    setClientResults([]);
    setMethod('cash');
    setPaymentAccountId('');
  };

  const handleCheckout = async () => {
    if (cart.length === 0) {
      toast.error('El carrito está vacío');
      return;
    }
    try {
      setCheckingOut(true);
      const payload: SaleCreateData = {
        items: cart.map((i) => ({ productId: i.product.id, qty: i.qty })),
        method,
        paymentAccountId: ACCOUNT_METHODS.includes(method) && paymentAccountId ? paymentAccountId : null,
        clientId: selectedClient?.id ?? null,
        clientName: selectedClient?.name ?? null,
      };
      const response = await apiService.createSale(payload);
      if (response.success) {
        setReceipt(response.data);
        setCart([]);
        toast.success('Venta registrada');
        loadProducts(); // refrescar stock disponible
      }
    } catch (err: any) {
      toast.error(err.message || 'Error registrando la venta');
    } finally {
      setCheckingOut(false);
    }
  };

  // ---------- Receipt summary ----------
  if (receipt) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <div className="card border-l-4 border-l-green-500 mb-6">
          <div className="flex items-center mb-4">
            <CheckCircle className="h-8 w-8 text-green-600 mr-3" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Venta registrada</h1>
              <p className="text-sm text-gray-600">Recibo {receipt.receiptNumber}</p>
            </div>
          </div>

          <div className="border-t border-gray-100 pt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Cliente</span>
              <span className="text-gray-900 font-medium">
                {receipt.clientName || 'Venta al público'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Método de pago</span>
              <span className="text-gray-900 font-medium">{PAYMENT_METHOD_LABELS[receipt.method]}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Fecha</span>
              <span className="text-gray-900 font-medium">{receipt.date}</span>
            </div>
          </div>

          <div className="border-t border-gray-100 mt-4 pt-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-2">Artículos</h2>
            <ul className="space-y-2">
              {receipt.items.map((item) => (
                <li key={item.productId} className="flex justify-between text-sm">
                  <span className="text-gray-900">
                    {item.productName} <span className="text-gray-400">x{item.qty}</span>
                  </span>
                  <span className="text-gray-600">{formatDollars(item.subtotalCents)}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="border-t border-gray-100 mt-4 pt-4 flex justify-between items-center">
            <span className="text-gray-500 font-medium">Total</span>
            <span className="text-2xl font-bold text-gray-900">{formatDollars(receipt.totalCents)}</span>
          </div>
        </div>

        <button onClick={reset} className="btn btn-primary w-full">
          <RotateCcw className="h-4 w-4 mr-2" />
          Nueva venta
        </button>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Punto de Venta</h1>
          <p className="text-gray-600 mt-1">Agrega productos al carrito y cobra la venta</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Product grid */}
        <div className="lg:col-span-2">
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-9"
              placeholder="Buscar producto..."
            />
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="loading-spinner h-10 w-10"></div>
            </div>
          ) : error ? (
            <div className="card text-center py-12 text-red-600">{error}</div>
          ) : filteredProducts.length === 0 ? (
            <div className="card text-center py-12">
              <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No hay productos disponibles.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredProducts.map((product) => {
                const out = (product.stockQty ?? 0) <= 0;
                return (
                  <div key={product.id} className="card p-4 flex flex-col">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">{product.name}</h3>
                      <p className="text-lg font-bold text-primary-600 mt-1">
                        {formatDollars(product.salePriceCents)}
                      </p>
                      <p className={`text-xs mt-1 ${out ? 'text-red-600' : 'text-gray-500'}`}>
                        {out ? 'Agotado' : `Stock: ${product.stockQty}`}
                      </p>
                    </div>
                    <button
                      onClick={() => addToCart(product)}
                      disabled={out}
                      className="btn btn-primary btn-sm mt-3 w-full disabled:opacity-50"
                    >
                      <Plus className="h-4 w-4 mr-1" /> Agregar
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Cart panel */}
        <div className="card p-4 self-start">
          <div className="flex items-center mb-4">
            <ShoppingCart className="h-5 w-5 text-primary-600 mr-2" />
            <h2 className="text-lg font-semibold text-gray-900">Carrito</h2>
          </div>

          {cart.length === 0 ? (
            <p className="text-sm text-gray-500 py-6 text-center">El carrito está vacío.</p>
          ) : (
            <ul className="space-y-3 mb-4">
              {cart.map((item) => (
                <li key={item.product.id} className="flex items-center justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{item.product.name}</p>
                    <p className="text-xs text-gray-500">{formatDollars(item.product.salePriceCents)} c/u</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button onClick={() => decrement(item.product.id)} className="btn btn-ghost btn-sm p-1">
                      <Minus className="h-4 w-4" />
                    </button>
                    <span className="text-sm font-semibold w-6 text-center">{item.qty}</span>
                    <button
                      onClick={() => addToCart(item.product)}
                      disabled={item.qty >= (item.product.stockQty ?? 0)}
                      className="btn btn-ghost btn-sm p-1 disabled:opacity-40"
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                    <button onClick={() => removeFromCart(item.product.id)} className="btn btn-ghost btn-sm p-1 text-red-600">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {/* Client (opcional) */}
          <div className="border-t border-gray-100 pt-4 space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <User className="h-4 w-4 inline mr-1" /> Cliente (opcional)
              </label>
              {selectedClient ? (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-900 font-medium">{selectedClient.name}</span>
                  <button onClick={() => setSelectedClient(null)} className="text-gray-400 hover:text-red-600">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <>
                  <input
                    type="text"
                    value={clientSearch}
                    onChange={(e) => setClientSearch(e.target.value)}
                    className="input"
                    placeholder="Buscar cliente (venta al público si vacío)"
                  />
                  {clientResults.length > 0 && (
                    <ul className="mt-1 border border-gray-200 rounded-md divide-y divide-gray-100 max-h-40 overflow-y-auto">
                      {clientResults.map((c) => (
                        <li key={c.id}>
                          <button
                            onClick={() => selectClient(c)}
                            className="w-full text-left px-3 py-2 text-sm hover:bg-primary-50"
                          >
                            {c.name}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
              {!selectedClient && (
                <p className="text-xs text-gray-400 mt-1">Sin cliente: se registra como "venta al público".</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Método de pago</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as PaymentMethod)}
                className="input"
              >
                {PAYMENT_METHODS.map((m) => (
                  <option key={m} value={m}>{PAYMENT_METHOD_LABELS[m]}</option>
                ))}
              </select>
            </div>

            {ACCOUNT_METHODS.includes(method) && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cuenta {PAYMENT_METHOD_LABELS[method]} destino
                </label>
                <select
                  value={paymentAccountId}
                  onChange={(e) => setPaymentAccountId(e.target.value)}
                  className="input"
                >
                  <option value="">Seleccionar cuenta</option>
                  {accounts.filter((a) => a.type === method).map((acc) => (
                    <option key={acc.id} value={acc.id}>{acc.label}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="flex justify-between items-center pt-2 border-t border-gray-100">
              <span className="text-gray-500 font-medium">Total</span>
              <span className="text-2xl font-bold text-gray-900">{formatDollars(totalCents)}</span>
            </div>

            <button
              onClick={handleCheckout}
              disabled={checkingOut || cart.length === 0}
              className="btn btn-primary w-full disabled:opacity-50"
            >
              {checkingOut ? 'Cobrando...' : 'Cobrar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
