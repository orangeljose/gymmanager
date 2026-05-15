import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';
import { UserPlus, Mail } from 'lucide-react';

export const AddAdminPage: React.FC = () => {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email.trim()) {
      toast.error('El email es requerido');
      return;
    }

    try {
      setLoading(true);

      // Create invitation for admin
      const response = await apiService.createInvitation({
        email: email.trim(),
        name: name.trim() || undefined,
        role: 'admin'
      });

      if (response.success) {
        toast.success('Invitación enviada. El nuevo admin recibirá un email para crear su cuenta y negocio.');
        // Reset form
        setEmail('');
        setName('');
      } else {
        toast.error(response.error?.message || 'Error al enviar invitación');
      }
    } catch (error: any) {
      toast.error(error.message || 'Error al procesar solicitud');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Agregar Admin</h1>
        <p className="text-gray-600 mt-1">
          Invita a un nuevo administrador para crear su propio negocio y sucursales
        </p>
      </div>

      <div className="card">
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-primary-700">
            <strong>Nota:</strong> El nuevo admin recibirá un link de invitación por email. 
            Al registrarse, podrá crear su propio negocio y primera sucursal.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <Mail className="h-4 w-4 inline mr-1" />
              Email del nuevo Admin *
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input"
              placeholder="admin@ejemplo.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nombre (opcional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input"
              placeholder="Carlos Pérez"
            />
          </div>

          <div className="pt-4">
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary w-full flex items-center justify-center"
            >
              {loading ? (
                <>
                  <div className="loading-spinner h-4 w-4 mr-2"></div>
                  Enviando invitación...
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4 mr-2" />
                  Enviar Invitación
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      <div className="mt-6 flex justify-between">
        <button
          onClick={() => navigate('/users')}
          className="btn btn-outline"
        >
          Ver Usuarios
        </button>
        <button
          onClick={() => navigate('/dashboard')}
          className="btn btn-ghost"
        >
          Volver al Dashboard
        </button>
      </div>
    </div>
  );
};