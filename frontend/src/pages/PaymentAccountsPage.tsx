import React, { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import { usePaymentAccounts } from '@/hooks/usePaymentAccounts';
import type { PaymentAccount, PaymentAccountFormData, PaymentAccountType } from '@/types';
import toast from 'react-hot-toast';
import { Plus, Edit2, Trash2, X, AlertCircle, Mail, Phone, Building } from 'lucide-react';

export const PaymentAccountsPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || "";
  const { accounts, loading, setAccounts } = usePaymentAccounts(effectiveBusinessId);
  const [showModal, setShowModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState<PaymentAccount | null>(null);
  const [formData, setFormData] = useState<PaymentAccountFormData>({
    type: 'zelle',
    identifier: '',
    label: '',
    description: '',
    businessId: ''
  });
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const openModal = (account?: PaymentAccount) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        type: account.type,
        identifier: account.identifier,
        label: account.label || '',
        description: account.description || '',
        bankName: account.bankName || '',
        cedula: account.cedula || ''
      });
    } else {
      setEditingAccount(null);
      setFormData({
        type: 'zelle',
        identifier: '',
        label: '',
        description: '',
        bankName: '',
        cedula: ''
      });
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingAccount(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveBusinessId) return;

    try {
      setSaving(true);
      if (editingAccount) {
        const { type, ...updateData } = formData;
        const response = await apiService.updatePaymentAccount(editingAccount.id, updateData);
        if (response.success) {
          toast.success('Cuenta actualizada');
          setAccounts(prev => prev.map(a => a.id === editingAccount.id ? { ...a, ...response.data } : a));
          closeModal();
        }
      } else {
        const response = await apiService.createPaymentAccount({ ...formData, businessId: effectiveBusinessId });
        if (response.success) {
          toast.success('Cuenta creada');
          setAccounts(prev => [...prev, response.data!]);
          closeModal();
        }
      }
    } catch (error: any) {
      toast.error(error.message || 'Error guardando cuenta');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (accountId: string) => {
    try {
      const response = await apiService.deletePaymentAccount(accountId);
if (response.success) {
          toast.success('Cuenta eliminada');
          setAccounts(prev => prev.filter(a => a.id !== accountId));
          setConfirmDelete(null);
        }
    } catch (error: any) {
      toast.error(error.message || 'Error eliminando cuenta');
    }
  };

  const getAccountIcon = (type: PaymentAccountType) => {
    switch (type) {
      case 'zelle':
        return <Mail className="h-5 w-5" />;
      case 'pago_movil':
        return <Phone className="h-5 w-5" />;
      case 'bank':
        return <Building className="h-5 w-5" />;
      case 'binance':
        return <Building className="h-5 w-5" />;
    }
  };

  const getAccountTypeLabel = (type: PaymentAccountType) => {
    switch (type) {
      case 'zelle':
        return 'Zelle';
      case 'pago_movil':
        return 'Pago Móvil';
      case 'binance':
        return 'Binance';
      // case 'bank':
      //   return 'Transferencia Bancaria';
    }
  };

  const getAccountTypeColor = (type: PaymentAccountType) => {
    switch (type) {
      case 'zelle':
        return 'bg-purple-100 text-purple-700';
      case 'pago_movil':
        return 'bg-green-100 text-green-700';
      case 'bank':
        return 'bg-blue-100 text-blue-700';
      case 'binance':
        return 'bg-yellow-100 text-yellow-700';
    }
  };

  const accountsByType = accounts.reduce((acc, account) => {
    if (!acc[account.type]) acc[account.type] = [];
    acc[account.type].push(account);
    return acc;
  }, {} as Record<PaymentAccountType, PaymentAccount[]>);

  if (loading) {
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
          <h1 className="text-2xl font-bold text-gray-900">Cuentas de Pago</h1>
          <p className="text-gray-600 mt-1">Gestiona las cuentas donde recibes pagos</p>
        </div>
        <button onClick={() => openModal()} className="btn btn-primary">
          <Plus className="h-4 w-4 mr-2" />
          Nueva Cuenta
        </button>
      </div>

      {accounts.length === 0 ? (
        <div className="card text-center py-12">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay cuentas registradas</h3>
          <p className="text-gray-600 mb-6">Agrega las cuentas donde recibes pagos (Zelle, Pago Móvil, Bancarias)</p>
          <button onClick={() => openModal()} className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Agregar Cuenta
          </button>
        </div>
      ) : (
        <div className="space-y-8">
          {(['zelle', 'pago_movil', 'bank'] as PaymentAccountType[]).map((type) => {
            const typeAccounts = accountsByType[type];
            if (!typeAccounts || typeAccounts.length === 0) return null;

            return (
              <div key={type}>
                <h2 className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium mb-4 ${getAccountTypeColor(type)}`}>
                  {getAccountIcon(type)}
                  <span className="ml-2">{getAccountTypeLabel(type)}</span>
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {typeAccounts.map((account) => (
                    <div key={account.id} className="card relative">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center">
                          <div className={`p-2 rounded-lg ${getAccountTypeColor(type)}`}>
                            {getAccountIcon(account.type)}
                          </div>
                          <div className="ml-3">
                            <h3 className="font-medium text-gray-900">{account.label}</h3>
                            <p className="text-sm text-gray-500">{account.identifier}</p>
                          </div>
                        </div>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          account.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                        }`}>
                          {account.isActive ? 'Activa' : 'Inactiva'}
                        </span>
                      </div>

                      {account.description && (
                        <p className="text-sm text-gray-600 mb-4">{account.description}</p>
                      )}

                      <div className="flex justify-end space-x-2 pt-3 border-t">
                        <button
                          onClick={() => openModal(account)}
                          className="btn btn-ghost btn-sm"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        {user?.role === 'super_admin' && (
                          <button
                            onClick={() => setConfirmDelete(account.id)}
                            className="btn btn-ghost btn-sm text-red-600 hover:text-red-800"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>

                      {confirmDelete === account.id && (
                        <div className="absolute inset-0 bg-white/95 flex items-center justify-center rounded-lg">
                          <div className="text-center p-4">
                            <p className="text-sm text-gray-900 mb-4">¿Eliminar esta cuenta?</p>
                            <div className="flex space-x-2 justify-center">
                              <button
                                onClick={() => handleDelete(account.id)}
                                className="btn btn-danger btn-sm"
                              >
                                Eliminar
                              </button>
                              <button
                                onClick={() => setConfirmDelete(null)}
                                className="btn btn-ghost btn-sm"
                              >
                                Cancelar
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="flex justify-between items-center p-4 border-b">
              <h3 className="text-lg font-semibold">
                {editingAccount ? 'Editar Cuenta' : 'Nueva Cuenta de Pago'}
              </h3>
              <button onClick={closeModal} className="btn btn-ghost btn-sm">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo de Cuenta *
                </label>
                <select
                  value={formData.type}
                  onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value as PaymentAccountType }))}
                  className="input"
                  disabled={!!editingAccount}
                >
                  <option value="zelle">Zelle</option>
                  <option value="pago_movil">Pago Móvil</option>
                  <option value="binance">Binance</option>
                  {/* <option value="bank">Transferencia Bancaria</option> */}
                </select>
              </div>

              {/* Campos específicos para Pago Móvil */}
              {formData.type === 'pago_movil' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Banco *
                    </label>
                    <input
                      type="text"
                      value={formData.bankName || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, bankName: e.target.value }))}
                      className="input"
                      placeholder="Ej: Banco Nacional de Crédito"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Cédula *
                    </label>
                    <input
                      type="text"
                      value={formData.cedula || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, cedula: e.target.value }))}
                      className="input"
                      placeholder="Ej: V-12345678"
                      required
                    />
                  </div>
                </>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {formData.type === 'zelle' ? 'Email de Zelle *' :
                    formData.type === 'binance' ? 'Email / ID de Binance *' :
                    formData.type === 'pago_movil' ? 'Número de Teléfono *' :
                      'Número de Cuenta *'}
                </label>
                <input
                  type={formData.type === 'zelle' || formData.type === 'binance' ? 'email' : 'tel'}
                  value={formData.identifier}
                  onChange={(e) => setFormData(prev => ({ ...prev, identifier: e.target.value }))}
                  className="input"
                  placeholder={
                    formData.type === 'zelle' ? 'correo@example.com' :
                      formData.type === 'binance' ? 'correo@binance.com o ID' :
                      formData.type === 'pago_movil' ? '04141234567' :
                        '01234567890123456789'
                  }
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Alias / Nombre
                </label>
                <input
                  type="text"
                  value={formData.label}
                  onChange={(e) => setFormData(prev => ({ ...prev, label: e.target.value }))}
                  className="input"
                  placeholder="Ej: Zelle principal del owner"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descripción
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="input"
                  rows={2}
                  placeholder="Notas sobre esta cuenta..."
                />
              </div>

              <div className="flex justify-end space-x-2 pt-4 border-t">
                <button type="button" onClick={closeModal} className="btn btn-outline">
                  Cancelar
                </button>
                <button type="submit" disabled={saving} className="btn btn-primary">
                  {saving ? 'Guardando...' : editingAccount ? 'Actualizar' : 'Crear Cuenta'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};