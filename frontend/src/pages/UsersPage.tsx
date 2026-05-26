import React, { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { User, UserRole, Branch } from '@/types';
import toast from 'react-hot-toast';
import { Plus, Edit2, X, AlertCircle, Mail, Shield, Building, Users as UsersIcon } from 'lucide-react';

const ROLE_LABELS: Record<UserRole, string> = {
  super_admin: 'Super Admin',
  admin: 'Admin',
    branch_admin: 'Encargado de Sucursal',
  cashier: 'Cajero',
  trainer: 'Entrenador'
};

const ROLE_COLORS: Record<UserRole, string> = {
  super_admin: 'bg-purple-100 text-purple-800',
admin: 'bg-purple-100 text-purple-800',
    branch_admin: 'bg-blue-100 text-blue-800',
  cashier: 'bg-green-100 text-green-800',
  trainer: 'bg-orange-100 text-orange-800'
};

export const UsersPage: React.FC = () => {
  const { user, selectedBusinessId, businesses } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    role: 'cashier' as UserRole,
    businessId: '',
    branchId: ''
  });
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  // Effective business ID based on context
  const effectiveBusinessId = selectedBusinessId || user?.businessId || '';

  useEffect(() => {
    loadBranches();
    loadUsers();
  }, [effectiveBusinessId]);

  const loadBranches = async () => {
    if (!effectiveBusinessId) return;
    try {
      const response = await apiService.getBranches(effectiveBusinessId);
      if (response.success && response.data) {
        setBranches(response.data);
      }
    } catch (error) {
      console.error('Error loading branches:', error);
    }
  };

  const loadUsers = async () => {
    if (!effectiveBusinessId) {
      setUsers([]);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const response = await apiService.getUsers({ businessId: effectiveBusinessId });
      if (response.success) {
        setUsers(response.data || []);
      }
    } catch (error) {
      console.error('Error loading users:', error);
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const openModal = (userToEdit?: User) => {
    if (userToEdit) {
      setEditingUser(userToEdit);
      setFormData({
        email: userToEdit.email,
        name: userToEdit.name,
        role: userToEdit.role,
        businessId: userToEdit.businessId || '',
        branchId: userToEdit.branchId || ''
      });
    } else {
      setEditingUser(null);
      // branch_admin auto-setear branchId
      let defaultBranchId = '';
      if (user?.role === 'branch_admin') {
        defaultBranchId = user?.branchId || '';
      }
      // Super admin debe especificar businessId del selector
      let defaultBusinessId = '';
      if (user?.role === 'super_admin') {
        defaultBusinessId = effectiveBusinessId;
      }
      setFormData({
        email: '',
        name: '',
        role: 'cashier',
        businessId: defaultBusinessId,
        branchId: defaultBranchId
      });
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingUser(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setSaving(true);
      if (editingUser) {
        const response = await apiService.updateUser(editingUser.id, formData);
        if (response.success) {
          toast.success('Usuario actualizado');
          loadUsers();
          closeModal();
        }
      } else {
        const response = await apiService.createUser(formData);
        if (response.success) {
          toast.success('Usuario creado. Se envió email para crear contraseña.');
          loadUsers();
          closeModal();
        }
      }
    } catch (error: any) {
      toast.error(error.message || 'Error procesando solicitud');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (userId: string) => {
    try {
      const response = await apiService.deleteUser(userId);
      if (response.success) {
        toast.success('Usuario desactivado');
        loadUsers();
        setConfirmDelete(null);
      }
    } catch (error: any) {
      toast.error(error.message || 'Error desactivando usuario');
    }
  };

  const getBranchName = (branchId: string | null | undefined) => {
    if (!branchId) return 'Sin asignar';
    const branch = branches.find(b => b.id === branchId);
    return branch?.name || branchId;
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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Usuarios</h1>
          <p className="text-gray-600 mt-1">Gestiona los empleados y sus roles</p>
        </div>
        <button onClick={() => openModal()} className="btn btn-primary">
          <Plus className="h-4 w-4 mr-2" />
          <span className="hidden sm:inline">Invitar Empleado</span>
          <span className="sm:hidden">Invitar</span>
        </button>
      </div>

      {users.length === 0 ? (
        <div className="card text-center py-12">
          <UsersIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay usuarios</h3>
          <p className="text-gray-600 mb-6">Invita empleados para comenzar</p>
          <button onClick={() => openModal()} className="btn btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Invitar Empleado
          </button>
        </div>
      ) : (
        <>
          <div className="hidden md:block card overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left text-xs font-medium text-gray-500 uppercase py-3 px-4">Usuario</th>
                    <th className="text-left text-xs font-medium text-gray-500 uppercase py-3 px-4">Rol</th>
                    <th className="text-left text-xs font-medium text-gray-500 uppercase py-3 px-4">Sucursal</th>
                    <th className="text-left text-xs font-medium text-gray-500 uppercase py-3 px-4">Estado</th>
                    <th className="text-right text-xs font-medium text-gray-500 uppercase py-3 px-4">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="flex items-center">
                          <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center mr-3">
                            <span className="text-primary-700 font-medium text-sm">
                              {u.name?.charAt(0).toUpperCase() || '?'}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{u.name}</p>
                            <p className="text-sm text-gray-500">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${ROLE_COLORS[u.role]}`}>
                          {ROLE_LABELS[u.role]}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {u.role === 'super_admin' ? (
                          <span className="text-gray-400">Todas</span>
                        ) : (
                          getBranchName(u.branchId)
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          u.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                        }`}>
                          {u.isActive ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => openModal(u)}
                          className="btn btn-ghost btn-sm mr-1"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        {u.id !== user?.id && (
                          <button
                            onClick={() => setConfirmDelete(u.id)}
                            className="btn btn-ghost btn-sm text-red-600 hover:text-red-800"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="md:hidden space-y-3">
            {users.map((u) => (
              <div key={u.id} className="card">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center">
                    <div className="h-12 w-12 rounded-full bg-primary-100 flex items-center justify-center mr-3">
                      <span className="text-primary-700 font-bold text-lg">
                        {u.name?.charAt(0).toUpperCase() || '?'}
                      </span>
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">{u.name}</p>
                      <p className="text-sm text-gray-500">{u.email}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    u.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {u.isActive ? 'Activo' : 'Inactivo'}
                  </span>
                </div>

                <div className="flex flex-wrap gap-2 mb-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${ROLE_COLORS[u.role]}`}>
                    {ROLE_LABELS[u.role]}
                  </span>
                  <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                    {u.role === 'super_admin' ? 'Todas las sucursales' : getBranchName(u.branchId)}
                  </span>
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t">
                  <button
                    onClick={() => openModal(u)}
                    className="btn btn-outline btn-sm flex-1 sm:flex-none"
                  >
                    <Edit2 className="h-4 w-4 mr-1" />
                    Editar
                  </button>
                  {u.id !== user?.id && (
                    <button
                      onClick={() => setConfirmDelete(u.id)}
                      className="btn btn-ghost btn-sm text-red-600 hover:text-red-800"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {confirmDelete && (
            <div className="fixed inset-x-0 bottom-0 bg-red-50 border-t border-red-200 p-4 md:hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
                  <span className="text-sm text-red-800">¿Desactivar este usuario?</span>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleDelete(confirmDelete)}
                    className="btn btn-danger btn-sm"
                  >
                    Desactivar
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
        </>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-end z-50 p-4">
          <div
            className="bg-white rounded-lg shadow-xl w-full max-w-md h-full sm:h-auto sm:my-8 flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center p-4 border-b flex-shrink-0">
              <h3 className="text-lg font-semibold">
                {editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
              </h3>
              <button onClick={closeModal} className="btn btn-ghost btn-sm">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-4 space-y-4 flex-1 overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Mail className="h-4 w-4 inline mr-1" />
                  Email *
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  className="input"
                  placeholder="empleado@ejemplo.com"
                  required
                  disabled={!!editingUser}
                />
                {editingUser && (
                  <p className="text-xs text-gray-500 mt-1">El email no puede ser modificado</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Shield className="h-4 w-4 inline mr-1" />
                  Nombre completo *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="input"
                  placeholder="Juan Pérez"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rol *
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value as UserRole }))}
                  className="input"
                  required
                  disabled={!!editingUser}
                >
                  <option value="branch_admin">Encargado de Sucursal</option>
                  <option value="cashier">Cajero</option>
                  <option value="trainer">Entrenador</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  El empleado recibirá un email para crear su contraseña
                </p>
              </div>

              {/* Selector de Negocio — solo super_admin */}
              {user?.role === 'super_admin' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    <Building className="h-4 w-4 inline mr-1" />
                    Negocio *
                  </label>
                  <select
                    value={formData.businessId || ''}
                    onChange={(e) => {
                      const newBusinessId = e.target.value;
                      setFormData(prev => ({ ...prev, businessId: newBusinessId, branchId: '' }));
                      // Recargar sucursales del nuevo negocio
                      apiService.getBranches(newBusinessId).then(res => {
                        if (res.success && res.data) setBranches(res.data);
                      });
                    }}
                    className="input"
                    required
                    disabled={!!editingUser}
                  >
                    <option value="">Seleccionar negocio...</option>
                    {businesses.map((b) => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Selector de Sucursal — super_admin y admin */}
              {user?.role !== 'branch_admin' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    <Building className="h-4 w-4 inline mr-1" />
                    Sucursal asignada
                  </label>
                  <select
                    value={formData.branchId || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, branchId: e.target.value }))}
                    className="input"
                    disabled={!!editingUser}
                  >
                    <option value="">Sin asignar</option>
                    {branches.map((branch) => (
                      <option key={branch.id} value={branch.id}>{branch.name}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* branch_admin no ve campos de negocio/sucursal — se setean solos */}

              <div className="flex justify-end space-x-2 pt-4 border-t flex-shrink-0">
                <button type="button" onClick={closeModal} className="btn btn-outline">
                  Cancelar
                </button>
                <button type="submit" disabled={saving} className="btn btn-primary">
                  {saving ? 'Guardando...' : editingUser ? 'Actualizar' : 'Crear Usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};