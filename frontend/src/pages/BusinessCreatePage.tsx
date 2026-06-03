import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building, ArrowLeft, CheckCircle, Edit2 } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';

export const BusinessCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { user, loadBusinesses } = useAuth();

  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [existingBusiness, setExistingBusiness] = useState<{ id: string; name: string } | null>(null);

  // Si el admin ya tiene negocio, cargarlo
  useEffect(() => {
    if (user?.role === 'admin' && user.businessId) {
      apiService.getBusinesses().then(res => {
        if (res.success && res.data) {
          const myBusiness = res.data.find(b => b.id === user.businessId);
          if (myBusiness) {
            setExistingBusiness({ id: myBusiness.id, name: myBusiness.name });
            setName(myBusiness.name);
          }
        }
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!name.trim()) {
      setError('El nombre del negocio es requerido');
      return;
    }

    setSaving(true);
    try {
      if (existingBusiness) {
        // Editar negocio existente
        const response = await apiService.updateBusiness(existingBusiness.id, { name: name.trim() });
        if (response.success) {
          setSuccess('Negocio actualizado exitosamente');
          setIsEditing(false);
          loadBusinesses();
          // Actualizar el nombre en el estado local
          setExistingBusiness(prev => prev ? { ...prev, name: name.trim() } : null);
        } else {
          setError(response.error?.message || 'Error al actualizar el negocio');
        }
      } else {
        // Crear nuevo negocio
        const response = await apiService.createBusiness({
          name: name.trim()
        });
        if (response.success) {
          setSuccess(`Negocio "${name.trim()}" creado exitosamente`);
          setName('');
          loadBusinesses();
          setTimeout(() => navigate('/dashboard'), 2000);
        } else {
          if (response.error?.code === 409) {
            setError(`Ya existe un negocio con el nombre "${name.trim()}"`);
          } else {
            setError(response.error?.message || 'Error al crear el negocio');
          }
        }
      }
    } catch (err: any) {
      setError(err.message || 'Error al procesar');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    // Restaurar el nombre original
    setName(existingBusiness?.name || '');
    setIsEditing(false);
    setError(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  // Si el admin ya tiene negocio y NO está editando, mostrar vista de solo lectura
  if (existingBusiness && !isEditing) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver al Dashboard
        </button>

        <div className="flex items-center space-x-3 mb-6">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Building className="h-6 w-6 text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Mi Negocio</h1>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Nombre del Negocio</p>
              <p className="text-xl font-semibold text-gray-900">{existingBusiness.name}</p>
            </div>
            <button
              onClick={() => setIsEditing(true)}
              className="btn btn-outline flex items-center"
            >
              <Edit2 className="h-4 w-4 mr-2" />
              Editar
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Vista de edición o creación
  return (
    <div className="p-6 max-w-2xl mx-auto">
      {existingBusiness && (
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver al Dashboard
        </button>
      )}

      <div className="flex items-center space-x-3 mb-6">
        <div className="p-2 bg-blue-100 rounded-lg">
          <Building className="h-6 w-6 text-blue-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">
          {existingBusiness ? 'Editar Negocio' : 'Crear Mi Negocio'}
        </h1>
      </div>

      {success && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center">
          <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
          <p className="text-green-700">{success}</p>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
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

          {!existingBusiness && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rubro
              </label>
              <input
                type="text"
                value="Gimnasio"
                disabled
                className="w-full px-4 py-2 border border-gray-200 rounded-md bg-gray-50 text-gray-500 cursor-not-allowed"
              />
              <p className="text-xs text-gray-500 mt-1">Por ahora solo trabajamos con Gimnasios</p>
            </div>
          )}

          <div className="flex justify-end space-x-3">
            {existingBusiness && isEditing && (
              <button
                type="button"
                onClick={handleCancelEdit}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                disabled={saving}
              >
                Cancelar
              </button>
            )}
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="px-6 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Guardando...' : (existingBusiness ? 'Guardar Cambios' : 'Crear Negocio')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};