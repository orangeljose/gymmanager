import React, { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { Receipt } from '@/types';
import toast from 'react-hot-toast';
import { ReceiptIcon, Download, ChevronLeft, ChevronRight } from 'lucide-react';



export const ReceiptsPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || "";
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(50);

  useEffect(() => {
    loadReceipts();
  }, [effectiveBusinessId, page]);

  const loadReceipts = async () => {
    if (!effectiveBusinessId) return;
    try {
      setLoading(true);
      const response = await apiService.getReceipts({
        limit,
        offset: page * limit
      });
      if (response.success && response.data) {
        setReceipts(response.data.receipts);
        setTotal(response.data.total);
      }
    } catch (error) {
      toast.error('Error cargando recibos');
    } finally {
      setLoading(false);
    }
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

  const getMethodLabel = (method: string) => {
    switch (method) {
      case 'cash': return 'Efectivo';
      case 'card': return 'Tarjeta';
      case 'transfer': return 'Transferencia';
      case 'zelle': return 'Zelle';
      case 'pago_movil': return 'Pago Móvil';
      default: return method;
    }
  };

  const getMethodColor = (method: string) => {
    switch (method) {
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

  if (loading && receipts.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recibos de Pago</h1>
          <p className="text-gray-600 mt-1">
            {total > 0 ? `${total} recibos encontrados` : 'Sin recibos registrados'}
          </p>
        </div>
        <button onClick={() => window.print()} className="btn btn-outline">
          <Download className="h-4 w-4 mr-2" />
          Exportar
        </button>
      </div>

      {receipts.length === 0 ? (
        <div className="card text-center py-12">
          <ReceiptIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay recibos registrados</h3>
          <p className="text-gray-600">Los recibos aparecerán aquí cuando se registren pagos</p>
        </div>
      ) : (
        <>
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Recibo
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Fecha
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Cliente
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Plan
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Monto
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Método
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Referencia
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Recibido por
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {receipts.map((receipt) => (
                    <tr key={receipt.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className="font-mono text-sm font-medium text-blue-600">
                          {receipt.receiptNumber}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {formatDate(receipt.createdAt)}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {receipt.clientName}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {receipt.planName || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 text-right">
                        {formatAmount(receipt.amount)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getMethodColor(receipt.method)}`}>
                          {getMethodLabel(receipt.method)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 font-mono">
                        {receipt.reference || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {receipt.registeredByName}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center mt-4">
              <p className="text-sm text-gray-600">
                Mostrando {startItem}-{endItem} de {total}
              </p>
              <div className="flex items-center space-x-2">
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