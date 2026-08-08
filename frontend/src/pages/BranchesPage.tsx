import React, { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { Branch, BranchFormData } from '@/types';
import toast from 'react-hot-toast';
import { Plus, Edit2, Trash2, X, MapPin, Phone, Building } from 'lucide-react';

export const BranchesPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || "";
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingBranch, setEditingBranch] = useState<Branch | null>(null);
  const [formData, setFormData] = useState<BranchFormData>({
    name: '',
    address: '',
    phone: '',
    businessId: ''
  });
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  useEffect(() => {
    loadBranches();
  }, [effectiveBusinessId]);

  const loadBranches = async () => {
    if (!effectiveBusinessId) {
      setBranches([]);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const response = await apiService.getBranches(effectiveBusinessId);
      if (response.success) {
        setBranches(response.data || []);
      }
    } catch (error) {
      console.error('Error cargando sucursales:', error);
      setBranches([]);
    } finally {
      setLoading(false);
    }
  };

  const openModal = (branch?: Branch) => {
    if (branch) {
      setEditingBranch(branch);
      setFormData({
        name: branch.name,
        address: branch.address,
        phone: branch.phone
      });
    } else {
      setEditingBranch(null);
      setFormData({
        name: '',
        address: '',
        phone: ''
      });
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingBranch(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveBusinessId) return;

    try {
      setSaving(true);
      if (editingBranch) {
        const response = await apiService.updateBranch(editingBranch.id, formData);
        if (response.success) {
          toast.success('Sucursal actualizada');
          setBranches(prev => prev.map(b => b.id === editingBranch.id ? { ...b, ...response.data } : b));
          closeModal();
        }
      } else {
        const response = await apiService.createBranch({ ...formData, businessId: effectiveBusinessId });
        if (response.success) {
          toast.success('Sucursal creada');
          setBranches(prev => [...prev, response.data!]);
          closeModal();
        }
      }
    } catch (error: any) {
      toast.error(error.message || 'Error guardando sucursal');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (branchId: string) => {
    try {
      const response = await apiService.deleteBranch(branchId);
      if (response.success) {
        toast.success('Sucursal eliminada');
        setBranches(prev => prev.filter(b => b.id !== branchId));
        setConfirmDelete(null);
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

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sucursales</h1>
          <p className="text-gray-600 mt-1">Gestiona las sedes de tu negocio</p>
        </div>
        <button onClick={() => openModal()} className="btn btn-primary">
          <Plus className="h-4 w-4 mr-2" />
          Nueva Sucursal
        </button>
      </div>

      {branches.length === 0 ? (
        <div className="card text-center py-12">
          <Building className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay sucursales</h3>
          <p className="text-gray-600 mb-6">Comienza creando tu primera sucursal</p>
          <button onClick={() => openModal()} className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Crear Sucursal
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {branches.map((branch) => (
            <div key={branch.id} className="card relative">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center">
                  <div className="p-2 bg-purple-100 rounded-lg mr-3">
                    <Building className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{branch.name}</h3>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      branch.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {branch.isActive ? 'Activa' : 'Inactiva'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex items-start">
                  <MapPin className="h-4 w-4 text-gray-400 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-600">{branch.address}</span>
                </div>
                <div className="flex items-center">
                  <Phone className="h-4 w-4 text-gray-400 mr-2 flex-shrink-0" />
                  <span className="text-gray-600">{branch.phone}</span>
                </div>
              </div>

              <div className="flex justify-end mt-4 pt-4 border-t gap-2">
                <button
                  onClick={() => openModal(branch)}
                  className="btn btn-ghost btn-sm"
                >
                  <Edit2 className="h-4 w-4" />
                </button>
                {(user?.role === 'super_admin' || user?.role === 'admin') && (
                  <button
                    onClick={() => setConfirmDelete(branch.id)}
                    className="btn btn-ghost btn-sm text-red-600 hover:text-red-800"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>

              {confirmDelete === branch.id && (
                <div className="absolute inset-0 bg-white/95 flex items-center justify-center rounded-lg">
                  <div className="text-center p-4">
                    <p className="text-sm text-gray-900 mb-4">¿Eliminar esta sucursal?</p>
                    <div className="flex space-x-2 justify-center">
                      <button
                        onClick={() => handleDelete(branch.id)}
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
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="flex justify-between items-center p-4 border-b">
              <h3 className="text-lg font-semibold">
                {editingBranch ? 'Editar Sucursal' : 'Nueva Sucursal'}
              </h3>
              <button onClick={closeModal} className="btn btn-ghost btn-sm">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre de la Sucursal *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="input"
                  placeholder="Ej: Sede Central"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dirección *
                </label>
                <input
                  type="text"
                  value={formData.address}
                  onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                  className="input"
                  placeholder="Ej: Av. Libertador #123"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Teléfono *
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                  className="input"
                  placeholder="Ej: +582412345678"
                  required
                />
              </div>

              <div className="flex justify-end space-x-2 pt-4 border-t">
                <button type="button" onClick={closeModal} className="btn btn-outline">
                  Cancelar
                </button>
                <button type="submit" disabled={saving} className="btn btn-primary">
                  {saving ? 'Guardando...' : editingBranch ? 'Actualizar' : 'Crear Sucursal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};