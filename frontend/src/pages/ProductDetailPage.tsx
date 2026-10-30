import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import { ProductForm, PRODUCT_CATEGORY_META, formatDollars, stockStatus } from '@/components/ProductForm';
import { ProductMovementModal } from '@/components/ProductMovementModal';
import { imageUrl } from '@/utils/images';
import toast from 'react-hot-toast';
import type { Product, ProductMovement } from '@/types';
import {
  ArrowLeft, Package, Edit2, Trash2, PlusCircle, AlertTriangle, Tag, DollarSign,
  Boxes, ArrowDownRight, ArrowUpRight,
} from 'lucide-react';

// Incluye `sale` por compatibilidad con movimientos legacy; hoy solo se registran compras.
const TYPE_META: Record<string, { label: string; badge: string; icon: React.ElementType }> = {
  sale: { label: 'Venta', badge: 'bg-green-100 text-green-800', icon: ArrowUpRight },
  purchase: { label: 'Compra', badge: 'bg-blue-100 text-blue-800', icon: ArrowDownRight },
};

const ADMIN_ROLES = ['super_admin', 'admin', 'branch_admin'];

export const ProductDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const canWrite = !!user && ADMIN_ROLES.includes(user.role);
  const canPurchase = canWrite;
  const canRegisterMovement = canPurchase;

  const [product, setProduct] = useState<Product | null>(null);
  const [history, setHistory] = useState<ProductMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showEdit, setShowEdit] = useState(false);
  const [showMovement, setShowMovement] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const loadProduct = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const [productRes, historyRes] = await Promise.all([
        apiService.getProduct(id),
        apiService.getProductMovements(id, { limit: 100 }),
      ]);
      if (productRes.success) setProduct(productRes.data);
      if (historyRes.success) setHistory(historyRes.data);
    } catch (err: any) {
      setError(err.message || 'Error cargando el producto');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadProduct();
  }, [loadProduct]);

  const handleDelete = async () => {
    if (!id) return;
    try {
      const response = await apiService.deleteProduct(id);
      if (response.success) {
        toast.success('Producto eliminado');
        navigate('/products');
      }
    } catch (err: any) {
      toast.error(err.message || 'Error eliminando producto');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="p-6">
        <div className="card text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Producto no encontrado</h3>
          <p className="text-gray-600 mb-6">{error || 'El producto que buscas no existe.'}</p>
          <Link to="/products" className="btn btn-primary">Volver a Productos</Link>
        </div>
      </div>
    );
  }

  const stock = stockStatus(product);
  const cat = PRODUCT_CATEGORY_META[product.category];

  return (
    <div className="p-6">
      <Link to="/products" className="inline-flex items-center text-sm text-gray-500 hover:text-primary-600 mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" /> Volver a Productos
      </Link>

      {/* Ficha */}
      <div className="mb-6 overflow-hidden rounded-xl bg-white shadow-md ring-1 ring-gray-100 border-l-4 border-l-primary-500">
        <div className="flex flex-col md:flex-row">
          <div className="shrink-0 md:w-80">
            {product.imageUrl ? (
              <img
                src={imageUrl(product.imageUrl, 'tile')}
                alt={product.name}
                className="h-56 w-full object-cover md:h-full md:min-h-[17rem]"
              />
            ) : (
              <div className="flex h-56 w-full items-center justify-center bg-gradient-to-br from-primary-50 via-white to-gray-100 md:h-full md:min-h-[17rem]">
                <Package className="h-14 w-14 text-primary-300" />
              </div>
            )}
          </div>

          <div className="flex-1 p-6">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
              <div className="flex items-start">
                <div>
              <h1 className="text-2xl font-bold text-gray-900">{product.name}</h1>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <span className={`badge ${cat.badge}`}>{cat.label}</span>
                <span className={`badge ${stock.badge}`}>
                  <span className={`mr-1.5 h-2 w-2 rounded-full ${stock.dot}`} />
                  {stock.label}
                </span>
              </div>
            </div>
          </div>

          {canWrite && (
            <div className="flex space-x-2">
              <button onClick={() => setShowEdit(true)} className="btn btn-outline btn-sm">
                <Edit2 className="h-4 w-4 mr-1" /> Editar
              </button>
              <button
                onClick={() => setConfirmDelete(true)}
                className="btn btn-ghost btn-sm text-red-600 hover:text-red-800"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-4 border-t">
          <div className="flex items-center text-sm">
            <Boxes className="h-4 w-4 mr-2 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Stock disponible</p>
              <p className="text-gray-900">{product.stockQty} (umbral {product.lowStockThreshold})</p>
            </div>
          </div>
          <div className="flex items-center text-sm">
            <Tag className="h-4 w-4 mr-2 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Categoría</p>
              <p className="text-gray-900">{cat.label}</p>
            </div>
          </div>
          <div className="flex items-center text-sm">
            <DollarSign className="h-4 w-4 mr-2 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Costo</p>
              <p className="text-gray-900">{formatDollars(product.costPriceCents)}</p>
            </div>
          </div>
          <div className="flex items-center text-sm">
            <DollarSign className="h-4 w-4 mr-2 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Precio de venta</p>
              <p className="text-gray-900">{formatDollars(product.salePriceCents)}</p>
            </div>
          </div>
        </div>
          </div>
        </div>
      </div>

      {/* Historial de movimientos */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Historial de movimientos</h2>
          {canRegisterMovement && (
            <button onClick={() => setShowMovement(true)} className="btn btn-primary btn-sm">
              <PlusCircle className="h-4 w-4 mr-2" /> Reponer
            </button>
          )}
        </div>

        {history.length === 0 ? (
          <div className="text-center py-10">
            <Boxes className="h-10 w-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">Sin movimientos registrados aún.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4 font-medium">Fecha</th>
                  <th className="py-2 pr-4 font-medium">Tipo</th>
                  <th className="py-2 pr-4 font-medium text-center">Cantidad</th>
                  <th className="py-2 pr-4 font-medium text-right">Precio unit.</th>
                  <th className="py-2 pr-4 font-medium text-right">Total</th>
                  <th className="py-2 pr-4 font-medium hidden sm:table-cell">Registrado por</th>
                  <th className="py-2 pr-4 font-medium hidden md:table-cell">Nota</th>
                </tr>
              </thead>
              <tbody>
                {history.map((mv) => {
                  const tmeta = TYPE_META[mv.type] || TYPE_META.purchase;
                  const Icon = tmeta.icon;
                  return (
                    <tr key={mv.id} className="border-b last:border-0">
                      <td className="py-3 pr-4 whitespace-nowrap text-gray-900">{mv.date}</td>
                      <td className="py-3 pr-4">
                        <span className={`badge ${tmeta.badge}`}>
                          <Icon className="h-3 w-3 mr-1" />
                          {tmeta.label}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-center text-gray-900">{mv.qty}</td>
                      <td className="py-3 pr-4 text-right text-gray-600 whitespace-nowrap">
                        {formatDollars(mv.unitPriceCents)}
                      </td>
                      <td className="py-3 pr-4 text-right font-semibold text-gray-900 whitespace-nowrap">
                        {formatDollars(mv.totalCents)}
                      </td>
                      <td className="py-3 pr-4 text-gray-600 hidden sm:table-cell">{mv.registeredByName || '—'}</td>
                      <td className="py-3 pr-4 text-gray-600 hidden md:table-cell max-w-xs truncate">
                        {mv.note || '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit modal */}
      <ProductForm
        open={showEdit}
        initial={product}
        onClose={() => setShowEdit(false)}
        onSaved={(updated) => setProduct((prev) => ({ ...(prev as Product), ...updated }))}
      />

      {/* Movement modal */}
      {showMovement && (
        <ProductMovementModal
          open={showMovement}
          product={product}
          onClose={() => setShowMovement(false)}
          onSaved={() => { loadProduct(); }}
        />
      )}

      {/* Delete confirm */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6 text-center">
            <AlertTriangle className="h-10 w-10 text-red-500 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">¿Eliminar producto?</h3>
            <p className="text-sm text-gray-600 mb-6">
              {product.name} quedará fuera del inventario. El historial de movimientos se conserva.
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
