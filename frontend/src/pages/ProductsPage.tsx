import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';
import {
  ProductForm, PRODUCT_CATEGORY_META, PRODUCT_CATEGORIES, formatDollars, stockStatus,
} from '@/components/ProductForm';
import { ProductMovementModal } from '@/components/ProductMovementModal';
import type {
  Product, ProductCategory, ProductFilters, ProductSummary,
} from '@/types';
import {
  Plus, Search, Package, DollarSign, AlertTriangle, Ban, Pencil, Trash2, Eye, PackagePlus,
} from 'lucide-react';
import { imageUrl } from '@/utils/images';

const LIMIT = 20;

export const ProductsPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';
  const canWrite = !!user && ['super_admin', 'admin', 'branch_admin'].includes(user.role);

  const [products, setProducts] = useState<Product[]>([]);
  const [summary, setSummary] = useState<ProductSummary | null>(null);
  const [meta, setMeta] = useState({ total: 0, page: 1, limit: LIMIT, pages: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<{ category: ProductCategory | ''; lowStock: boolean; search: string }>({
    category: '', lowStock: false, search: '',
  });

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [movementProduct, setMovementProduct] = useState<Product | null>(null);

  const scoped = user?.role === 'super_admin' && effectiveBusinessId
    ? { businessId: effectiveBusinessId }
    : {};

  const loadSummary = useCallback(async () => {
    try {
      const response = await apiService.getProductsSummary(scoped);
      if (response.success) setSummary(response.data);
    } catch {
      /* el resumen es accesorio; no bloquea la lista */
    }
  }, [user?.role, effectiveBusinessId]);

  const loadProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params: ProductFilters = {
        ...scoped,
        category: filters.category || undefined,
        lowStock: filters.lowStock || undefined,
        search: filters.search || undefined,
        page,
        limit: LIMIT,
      };
      const response = await apiService.getProducts(params);
      if (response.success) {
        setProducts(response.data);
        if (response.meta) {
          setMeta({
            total: response.meta.total ?? 0,
            page: response.meta.page ?? page,
            limit: response.meta.limit ?? LIMIT,
            pages: response.meta.pages ?? 0,
          });
        }
      }
    } catch (err: any) {
      setError(err.message || 'Error cargando productos');
    } finally {
      setLoading(false);
    }
  }, [user?.role, effectiveBusinessId, filters, page]);

  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadProducts(); }, [loadProducts]);

  const updateFilter = (patch: Partial<typeof filters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  };

  const openCreate = () => { setEditing(null); setShowForm(true); };
  const openEdit = (product: Product) => { setEditing(product); setShowForm(true); };

  const handleDelete = async (product: Product) => {
    if (!window.confirm(`¿Eliminar el producto "${product.name}"? Esta acción no se puede deshacer.`)) return;
    try {
      const response = await apiService.deleteProduct(product.id);
      if (response.success) {
        toast.success('Producto eliminado');
        loadProducts();
        loadSummary();
      }
    } catch (err: any) {
      toast.error(err.message || 'Error eliminando producto');
    }
  };

  const statCards = [
    { label: 'Productos', value: String(summary?.totalProducts ?? 0), icon: Package, color: 'text-primary-600 bg-primary-50' },
    { label: 'Valor de stock', value: formatDollars(summary?.totalStockValue ?? 0), icon: DollarSign, color: 'text-green-600 bg-green-50' },
    { label: 'Stock bajo', value: String(summary?.lowStockCount ?? 0), icon: AlertTriangle, color: 'text-yellow-600 bg-yellow-50' },
    { label: 'Agotados', value: String(summary?.outOfStockCount ?? 0), icon: Ban, color: 'text-red-600 bg-red-50' },
  ];

  const hasFilters = !!(filters.category || filters.lowStock || filters.search);

  return (
    <div className="p-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mercancía</h1>
          <p className="text-gray-600 mt-1">Inventario de mercancía, precios y stock</p>
        </div>
        {canWrite && (
          <button onClick={openCreate} className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Producto
          </button>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {statCards.map((card) => (
          <div key={card.label} className="card p-4 flex items-center">
            <div className={`p-2 rounded-lg ${card.color}`}>
              <card.icon className="h-5 w-5" />
            </div>
            <div className="ml-3">
              <p className="text-2xl font-bold text-gray-900">{card.value}</p>
              <p className="text-xs text-gray-500">{card.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="relative lg:col-span-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={filters.search}
              onChange={(e) => updateFilter({ search: e.target.value })}
              className="input pl-9"
              placeholder="Buscar por nombre..."
            />
          </div>
          <select
            value={filters.category}
            onChange={(e) => updateFilter({ category: e.target.value as ProductCategory | '' })}
            className="input"
          >
            <option value="">Todas las categorías</option>
            {PRODUCT_CATEGORIES.map((c) => (
              <option key={c} value={c}>{PRODUCT_CATEGORY_META[c].label}</option>
            ))}
          </select>
          <label className="flex items-center text-sm text-gray-700 px-1">
            <input
              type="checkbox"
              checked={filters.lowStock}
              onChange={(e) => updateFilter({ lowStock: e.target.checked })}
              className="mr-2"
            />
            Solo stock bajo
          </label>
        </div>
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="loading-spinner h-10 w-10"></div>
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No se pudieron cargar los productos</h3>
          <p className="text-gray-600">{error}</p>
        </div>
      ) : products.length === 0 ? (
        <div className="card text-center py-12">
          <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {hasFilters ? 'No hay mercancía para estos filtros' : 'No hay mercancía registrada'}
          </h3>
          <p className="text-gray-600 mb-6">
            Registra la mercancía del gimnasio para controlar precios y stock.
          </p>
          {canWrite && (
            <button onClick={openCreate} className="btn btn-primary">
              <Plus className="h-4 w-4 mr-2" />
              Nuevo Producto
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-left">
                <tr>
                  <th className="px-4 py-3 font-medium">Producto</th>
                  <th className="px-4 py-3 font-medium">Categoría</th>
                  <th className="px-4 py-3 font-medium text-center">Stock</th>
                  <th className="px-4 py-3 font-medium text-right hidden sm:table-cell">Costo</th>
                  <th className="px-4 py-3 font-medium text-right">Precio</th>
                  <th className="px-4 py-3 font-medium text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {products.map((product) => {
                  const stock = stockStatus(product);
                  const cat = PRODUCT_CATEGORY_META[product.category];
                  return (
                    <tr key={product.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          {product.imageUrl ? (
                            <img
                              src={imageUrl(product.imageUrl, 'thumb')}
                              alt={product.name}
                              loading="lazy"
                              className="h-10 w-10 rounded-lg object-cover ring-1 ring-gray-100"
                            />
                          ) : (
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100">
                              <Package className="h-5 w-5 text-gray-400" />
                            </div>
                          )}
                          <Link to={`/products/${product.id}`} className="font-medium text-gray-900 hover:text-primary-600">
                            {product.name}
                          </Link>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`badge ${cat.badge}`}>{cat.label}</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`badge ${stock.badge} whitespace-nowrap`}>
                          <span className={`mr-1.5 h-2 w-2 rounded-full ${stock.dot}`} />
                          {product.stockQty} · {stock.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600 hidden sm:table-cell whitespace-nowrap">
                        {formatDollars(product.costPriceCents)}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-900 whitespace-nowrap">
                        {formatDollars(product.salePriceCents)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end space-x-1">
                          <Link
                            to={`/products/${product.id}`}
                            className="p-2 rounded-md text-gray-500 hover:bg-primary-50 hover:text-primary-600"
                            title="Ver detalle"
                          >
                            <Eye className="h-4 w-4" />
                          </Link>
                          {canWrite && (
                            <>
                              <button
                                onClick={() => setMovementProduct(product)}
                                className="p-2 rounded-md text-gray-500 hover:bg-primary-50 hover:text-primary-600"
                                title="Reponer"
                              >
                                <PackagePlus className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => openEdit(product)}
                                className="p-2 rounded-md text-gray-500 hover:bg-primary-50 hover:text-primary-600"
                                title="Editar"
                              >
                                <Pencil className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => handleDelete(product)}
                                className="p-2 rounded-md text-gray-500 hover:bg-red-50 hover:text-red-600"
                                title="Eliminar"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {meta.pages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-gray-500">
                Página {meta.page} de {meta.pages} · {meta.total} productos
              </p>
              <div className="flex space-x-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={meta.page <= 1}
                  className="btn btn-secondary btn-sm"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(meta.pages, p + 1))}
                  disabled={meta.page >= meta.pages}
                  className="btn btn-secondary btn-sm"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </>
      )}

      <ProductForm
        open={showForm}
        initial={editing}
        businessId={effectiveBusinessId}
        onClose={() => setShowForm(false)}
        onSaved={() => {
          loadProducts();
          loadSummary();
        }}
      />

      {movementProduct && (
        <ProductMovementModal
          open={!!movementProduct}
          product={movementProduct}
          onClose={() => setMovementProduct(null)}
          onSaved={() => {
            setMovementProduct(null);
            loadProducts();
            loadSummary();
          }}
        />
      )}
    </div>
  );
};
