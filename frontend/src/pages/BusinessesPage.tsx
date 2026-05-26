import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Building, Plus, ArrowLeft, X, Edit2 } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { Business } from '@/types';
import toast from 'react-hot-toast';

export const BusinessesPage: React.FC = () => {
  const { user, businesses, loadBusinesses } = useAuth();
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingBusiness, setEditingBusiness] = useState<Business | null>(null);
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadBusinesses();
    setLoading(false);
  }, []);

  const openCreateModal = () => {
    setEditingBusiness(null);
    setName('');
    setShowModal(true);
  };

  const openEditModal = (business: Business) => {
    setEditingBusiness(business);
    setName(business.name);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingBusiness(null);
    setName('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSaving(true);
    try {
      if (editingBusiness) {
        const response = await apiService.updateBusiness(editingBusiness.id, { name: name.trim() });
        if (response.success) {
          toast.success('Negocio actualizado');
          closeModal();
          loadBusinesses();
        } else {
          toast.error(response.error?.message || 'Error al actualizar');
        }
      } else {
        const response = await apiService.createBusiness({
          name: name.trim(),
          rubro: 'Gimnasio'
        });
        if (response.success) {
          toast.success('Negocio creado');
          closeModal();
          loadBusinesses();
        } else {
          toast.error(response.error?.message || 'Error al crear');
        }
      }
    } catch (err: any) {
      toast.error(err.message || 'Error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, bname: string) => {
    if (!confirm(`¿Eliminar el negocio "${bname}"?`)) return;
    try {
      const response = await apiService.deleteBusiness(id);
      if (response.success) {
        toast.success('Negocio eliminado');
        loadBusinesses();
      } else {
        toast.error(response.error?.message || 'Error al eliminar');
      }
    } catch (err: any) {
      toast.error(err.message || 'Error al eliminar');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  const isSuperAdmin = user?.role === 'super_admin';

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Link to="/admin" className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Negocios</h1>
            <p className="text-gray-600 mt-1">Gestiona todos tus negocios</p>
          </div>
        </div>
        {isSuperAdmin && (
          <button onClick={openCreateModal} className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Negocio
          </button>
        )}
      </div>

      {businesses.length === 0 ? (
        <div className="card text-center py-12">
          <Building className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay negocios</h3>
          <p className="text-gray-600 mb-6">Crea tu primer negocio para comenzar</p>
          {isSuperAdmin && (
            <button onClick={openCreateModal} className="btn btn-primary">
              <Plus className="h-4 w-4 mr-2" />
              Crear Negocio
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {businesses.map((business) => (
            <div key={business.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Building className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{business.name}</h3>
                  </div>
                </div>
                {isSuperAdmin && (
                  <button
                    onClick={() => openEditModal(business)}
                    className="p-1.5 hover:bg-gray-100 rounded-md transition-colors"
                    title="Editar nombre"
                  >
                    <Edit2 className="h-4 w-4 text-gray-500" />
                  </button>
                )}
              </div>

              <div className="mt-4 pt-4 border-t flex justify-between items-center">
                <span className="text-xs text-gray-500">
                  Creado: {new Date(business.createdAt?.seconds * 1000 || Date.now()).toLocaleDateString()}
                </span>
                {isSuperAdmin && (
                  <button
                    onClick={() => handleDelete(business.id, business.name)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Eliminar
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingBusiness ? 'Editar Negocio' : 'Nuevo Negocio'}
              </h2>
              <button onClick={closeModal} className="p-1 hover:bg-gray-100 rounded-md">
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del Negocio <span className="text-red-500">*</span>
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ej: Gimnasio Central"
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  disabled={saving}
                  autoFocus
                />
              </div>

              {!editingBusiness && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Rubro</label>
                  <input
                    type="text"
                    value="Gimnasio"
                    disabled
                    className="w-full px-4 py-2 border border-gray-200 rounded-md bg-gray-50 text-gray-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Por ahora solo trabajamos con Gimnasios</p>
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  disabled={saving}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving || !name.trim()}
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Guardando...' : editingBusiness ? 'Guardar' : 'Crear Negocio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};