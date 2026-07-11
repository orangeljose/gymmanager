import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { Receipt, Branch } from '@/types';
import toast from 'react-hot-toast';
import { ReceiptIcon, Download, ChevronLeft, ChevronRight, Calendar, User, CreditCard, Filter, X } from 'lucide-react';

const METHOD_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Todos los métodos' },
  { value: 'cash', label: 'Efectivo' },
  { value: 'card', label: 'Tarjeta' },
  { value: 'transfer', label: 'Transferencia' },
  { value: 'zelle', label: 'Zelle' },
  { value: 'pago_movil', label: 'Pago Móvil' },
  { value: 'other', label: 'Otro' },
];

export const ReceiptsPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || "";
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(50);

  // Filter state
  const [method, setMethod] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [branchId, setBranchId] = useState<string>('');
  const [branches, setBranches] = useState<Branch[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const hasActiveFilters = method || startDate || endDate || branchId;

  useEffect(() => {
    if (effectiveBusinessId && user?.role === 'super_admin') {
      apiService.getBranches(effectiveBusinessId).then(res => {
        if (res.success && res.data) setBranches(res.data);
      });
    }
  }, [effectiveBusinessId, user?.role]);

  const loadReceipts = useCallback(async () => {
    if (!effectiveBusinessId) return;
    try {
      setLoading(true);
      const params: any = {
        limit,
        offset: page * limit
      };
      if (method) params.method = method;
      if (startDate) params.startDate = startDate;
      if (endDate) params.endDate = endDate;
      if (branchId) params.branchId = branchId;

      const response = await apiService.getReceipts(params);
      if (response.success && response.data) {
        setReceipts(response.data.receipts);
        setTotal(response.data.total);
      }
    } catch (error) {
      toast.error('Error cargando recibos');
    } finally {
      setLoading(false);
    }
  }, [effectiveBusinessId, page, limit, method, startDate, endDate, branchId]);

  useEffect(() => {
    loadReceipts();
  }, [loadReceipts]);

  const clearFilters = () => {
    setMethod('');
    setStartDate('');
    setEndDate('');
    setBranchId('');
    setPage(0);
  };

  const formatAmount = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(cents / 100);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const getMethodLabel = (m: string) => {
    switch (m) {
      case 'cash': return 'Efectivo';
      case 'card': return 'Tarjeta';
      case 'transfer': return 'Transferencia';
      case 'zelle': return 'Zelle';
      case 'pago_movil': return 'Pago Móvil';
      default: return m;
    }
  };

  const getMethodColor = (m: string) => {
    switch (m) {
      case 'cash': return 'bg-green-100 text-green-700';
      case 'card': return 'bg-blue-100 text-blue-700';
      case 'transfer': return 'bg-purple-100 text-purple-700';
      case 'zelle': return 'bg-pink-100 text-pink-700';
      case 'pago_movil': return 'bg-orange-100 text-orange-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const totalPages = Math.ceil(total / limit);
  const startItem = page * limit + 1;
  const endItem = Math.min((page + 1) * limit, total);

  return (
    <div className="p-4 sm:p-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4 sm:mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Recibos de Pago</h1>
          <p className="text-sm text-gray-600 mt-1">
            {total > 0 ? `${total} recibos encontrados` : 'Sin recibos registrados'}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn btn-outline ${showFilters || hasActiveFilters ? 'bg-gray-50' : ''}`}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filtros
            {hasActiveFilters && (
              <span className="ml-2 w-2 h-2 bg-primary-500 rounded-full" />
            )}
          </button>
          <button onClick={() => window.print()} className="btn btn-outline">
            <Download className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Exportar</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      {showFilters && (
        <div className="card mb-4">
          <div className="p-4 flex flex-wrap gap-4 items-end">
            <div className="w-full sm:w-auto">
              <label className="block text-sm font-medium text-gray-700 mb-1">Método de pago</label>
              <select
                value={method}
                onChange={(e) => { setMethod(e.target.value); setPage(0); }}
                className="input"
              >
                {METHOD_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div className="w-full sm:w-auto">
              <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => { setStartDate(e.target.value); setPage(0); }}
                className="input"
              />
            </div>

            <div className="w-full sm:w-auto">
              <label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => { setEndDate(e.target.value); setPage(0); }}
                className="input"
              />
            </div>

            {user?.role === 'super_admin' && branches.length > 0 && (
              <div className="w-full sm:w-auto">
                <label className="block text-sm font-medium text-gray-700 mb-1">Sucursal</label>
                <select
                  value={branchId}
                  onChange={(e) => { setBranchId(e.target.value); setPage(0); }}
                  className="input"
                >
                  <option value="">Todas</option>
                  {branches.map(b => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>
            )}

            {hasActiveFilters && (
              <div className="flex items-end">
                <button
                  onClick={clearFilters}
                  className="btn btn-ghost text-sm"
                >
                  <X className="h-4 w-4 mr-1" />
                  Limpiar filtros
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {loading && receipts.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <div className="loading-spinner h-10 w-10"></div>
        </div>
      ) : receipts.length === 0 ? (
        <div className="card text-center py-12">
          <ReceiptIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay recibos registrados</h3>
          <p className="text-gray-600">Los recibos aparecerán aquí cuando se registren pagos</p>
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recibo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cliente</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Monto</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Método</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Referencia</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">Recibido por</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {receipts.map((receipt) => (
                    <tr key={receipt.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className="font-mono text-sm font-medium text-blue-600">{receipt.receiptNumber}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{formatDate(receipt.createdAt)}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{receipt.clientName}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{receipt.planName || '-'}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 text-right">{formatAmount(receipt.amount)}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getMethodColor(receipt.method)}`}>{getMethodLabel(receipt.method)}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 font-mono">{receipt.reference || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600 hidden lg:table-cell">{receipt.registeredByName}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {receipts.map((receipt) => (
              <div key={receipt.id} className="card">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-mono text-sm font-medium text-blue-600">{receipt.receiptNumber}</span>
                  <span className="text-base font-bold text-gray-900">{formatAmount(receipt.amount)}</span>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <User className="h-3.5 w-3.5 text-gray-400" />
                    <span className="font-medium text-gray-900">{receipt.clientName}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Calendar className="h-3.5 w-3.5 text-gray-400" />
                    <span className="text-gray-600">{formatDate(receipt.createdAt)}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <CreditCard className="h-3.5 w-3.5 text-gray-400" />
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getMethodColor(receipt.method)}`}>{getMethodLabel(receipt.method)}</span>
                    {receipt.reference && (
                      <span className="text-gray-500 font-mono text-xs">{receipt.reference}</span>
                    )}
                  </div>

                  <div className="flex justify-between items-center pt-1 border-t border-gray-100">
                    <span className="text-xs text-gray-500">{receipt.planName || 'Sin plan'}</span>
                    <span className="text-xs text-gray-400">{receipt.registeredByName}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mt-4">
              <p className="text-sm text-gray-600 text-center sm:text-left">
                Mostrando {startItem}-{endItem} de {total}
              </p>
              <div className="flex items-center justify-center space-x-2">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="btn btn-outline btn-sm"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-sm text-gray-600">
                  Página {page + 1} de {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= totalPages - 1}
                  className="btn btn-outline btn-sm"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
