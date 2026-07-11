import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, UserCheck, Calendar, CreditCard, AlertCircle, Building } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { usePlans } from '@/hooks/usePlans';
import { apiService } from '@/services/api';
import { PaymentForm } from '@/components/PaymentForm';
import type { Client } from '@/types';

export const PaymentsNewPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';
  const { plans } = usePlans(effectiveBusinessId);
  const navigate = useNavigate();

  const [searchTerm, setSearchTerm] = useState('');
  const [clients, setClients] = useState<Client[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [receiptNumber, setReceiptNumber] = useState<string | null>(null);

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100);
  };

  const formatDate = (d: string) => new Date(d).toLocaleDateString('es-VE', { day: '2-digit', month: 'short', year: 'numeric' });

  const getDaysRemaining = (membershipEnd: string) => {
    const today = new Date();
    const end = new Date(membershipEnd);
    return Math.ceil((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  };

  const getPlanName = (planId: string) => {
    const plan = plans.find(p => p.id === planId);
    return plan ? plan.name : planId;
  };

  const searchClients = useCallback(async (term: string) => {
    if (!term || term.length < 2) {
      setClients([]);
      setShowDropdown(false);
      return;
    }

    setSearching(true);
    try {
      const response = await apiService.getClients({ search: term, limit: 10 });
      if (response.success && response.data) {
        setClients(response.data);
        setShowDropdown(response.data.length > 0);
      }
    } catch (err) {
      console.error('Error searching clients:', err);
      setClients([]);
    } finally {
      setSearching(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      searchClients(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm, searchClients]);

  const handleSelectClient = (client: Client) => {
    setSelectedClient(client);
    setSearchTerm('');
    setClients([]);
    setShowDropdown(false);
    setReceiptNumber(null);
  };

  const handlePaymentSuccess = () => {
    // Reset for next payment
    setSelectedClient(null);
    setReceiptNumber(null);
  };

  const handleClearSelection = () => {
    setSelectedClient(null);
    setReceiptNumber(null);
  };

  const daysRemaining = selectedClient ? getDaysRemaining(selectedClient.membershipEnd) : 0;

  return (
    <div className="p-6">
      <div className="mb-6">
        <Link to="/dashboard" className="btn btn-ghost btn-sm mb-4">
          ← Volver al dashboard
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">Registrar Pago</h1>
        <p className="text-gray-600 mt-1">Busca un cliente y registra su pago de membresía</p>
      </div>

      {/* Client Search */}
      {!selectedClient && (
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Buscar Cliente</h3>
            <p className="card-description">Escribe al menos 2 caracteres para buscar</p>
          </div>
          <div className="card-content">
            <div className="relative">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  onFocus={() => { if (clients.length > 0) setShowDropdown(true); }}
                  placeholder="Buscar cliente por nombre..."
                  className="input pl-10"
                  autoFocus
                />
                {searching && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <div className="loading-spinner h-4 w-4" />
                  </div>
                )}
              </div>

              {showDropdown && clients.length > 0 && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {clients.map(client => (
                    <button
                      key={client.id}
                      type="button"
                      onClick={() => handleSelectClient(client)}
                      className="w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 flex items-center justify-between"
                    >
                      <div>
                        <p className="font-medium text-gray-900">{client.name}</p>
                        <p className="text-sm text-gray-500">{client.email}</p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        client.status === 'active' ? 'bg-green-100 text-green-800' :
                        client.status === 'expired' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {client.status === 'active' ? 'Al día' : client.status === 'expired' ? 'Vencido' : 'Suspendido'}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {!searching && searchTerm.length >= 2 && clients.length === 0 && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg p-4 text-center text-gray-500">
                  No se encontraron clientes
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Client Summary Card */}
      {selectedClient && (
        <div className="card mb-6">
          <div className="card-header flex justify-between items-start">
            <div>
              <h3 className="card-title">Cliente Seleccionado</h3>
              <p className="card-description">Verifica los datos antes de registrar el pago</p>
            </div>
            <button onClick={handleClearSelection} className="btn btn-ghost btn-sm text-gray-500">
              Cambiar cliente
            </button>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex items-center">
                <UserCheck className="h-5 w-5 text-gray-400 mr-3 flex-shrink-0" />
                <div>
                  <div className="text-xs text-gray-500">Nombre</div>
                  <div className="text-sm font-medium text-gray-900">{selectedClient.name}</div>
                </div>
              </div>
              <div className="flex items-center">
                <CreditCard className="h-5 w-5 text-gray-400 mr-3 flex-shrink-0" />
                <div>
                  <div className="text-xs text-gray-500">Plan Actual</div>
                  <div className="text-sm font-medium text-gray-900">{getPlanName(selectedClient.membershipPlanId)}</div>
                </div>
              </div>
              <div className="flex items-center">
                <Calendar className="h-5 w-5 text-gray-400 mr-3 flex-shrink-0" />
                <div>
                  <div className="text-xs text-gray-500">Vencimiento</div>
                  <div className="text-sm font-medium text-gray-900">
                    {formatDate(selectedClient.membershipEnd)}
                  </div>
                </div>
              </div>
              <div className="flex items-center">
                <AlertCircle className={`h-5 w-5 mr-3 flex-shrink-0 ${
                  selectedClient.status === 'active' ? 'text-green-500' :
                  selectedClient.status === 'expired' ? 'text-red-500' : 'text-yellow-500'
                }`} />
                <div>
                  <div className="text-xs text-gray-500">Estado</div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      selectedClient.status === 'active' ? 'bg-green-100 text-green-800' :
                      selectedClient.status === 'expired' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {selectedClient.status === 'active' ? 'Activo' : selectedClient.status === 'expired' ? 'Vencido' : 'Suspendido'}
                    </span>
                    {selectedClient.status === 'active' && daysRemaining >= 0 && daysRemaining <= 7 && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-yellow-500 text-white">
                        {daysRemaining === 0 ? 'Hoy' : `${daysRemaining}d`}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payment Form */}
      {selectedClient && (
        <div className="max-w-lg">
          <PaymentForm
            businessId={effectiveBusinessId}
            clientId={selectedClient.id}
            clientName={selectedClient.name}
            currentPlanId={selectedClient.membershipPlanId}
            branchId={selectedClient.branchId}
            initialAmount={plans.find(p => p.id === selectedClient.membershipPlanId)?.price}
            onSuccess={handlePaymentSuccess}
            onCancel={handleClearSelection}
            isModal={false}
          />
        </div>
      )}

      {/* Empty State */}
      {!selectedClient && !searchTerm && (
        <div className="text-center py-12">
          <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-600 mb-2">Busca un cliente para comenzar</h3>
          <p className="text-gray-500">
            Utiliza el buscador para encontrar al cliente y registrar su pago de membresía.
          </p>
        </div>
      )}
    </div>
  );
};

export default PaymentsNewPage;
