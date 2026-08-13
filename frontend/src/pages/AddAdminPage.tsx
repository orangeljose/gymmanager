import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';
import { UserPlus, Mail, Building, Link2, Copy, Check } from 'lucide-react';

export const AddAdminPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedBusinessId, businesses } = useAuth();

  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [invitationLink, setInvitationLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const selectedBusiness = businesses.find(b => b.id === selectedBusinessId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email.trim()) {
      toast.error('El email es requerido');
      return;
    }

    if (!selectedBusinessId) {
      toast.error('Selecciona un negocio del dropdown para invitar a un admin');
      return;
    }

    try {
      setLoading(true);

      // Create invitation for admin with businessId from selector
      const response = await apiService.createInvitation({
        email: email.trim(),
        name: name.trim() || undefined,
        role: 'admin',
        businessId: selectedBusinessId
      });

      if (response.success) {
        setInvitationLink(response.data?.invitationLink || null);
        toast.success(`Invitación creada para ${email}`);
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

  const handleCopy = async () => {
    if (!invitationLink) return;
    try {
      await navigator.clipboard.writeText(invitationLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('No se pudo copiar el link');
    }
  };

  return (
    <div className="p-6 max-w-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Agregar Admin</h1>
        <p className="text-gray-600 mt-1">
          Invita a un nuevo administrador para {selectedBusiness ? selectedBusiness.name : 'tu negocio'}
        </p>
      </div>

      {selectedBusiness && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 flex items-center space-x-3">
          <Building className="h-5 w-5 text-blue-600" />
          <div>
            <p className="text-sm text-blue-700">
              El nuevo admin se unirá a: <strong>{selectedBusiness.name}</strong>
            </p>
          </div>
        </div>
      )}

      <div className="card">
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-primary-700">
            El nuevo admin recibirá un link de invitación por email. 
            Al registrarse, tendrá acceso al negocio {selectedBusiness?.name || 'seleccionado'}.
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

      {invitationLink && (
        <div className="mt-6 card border-2 border-green-200 bg-green-50">
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <Link2 className="h-5 w-5 text-green-700" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-green-900 mb-1">
                Link de invitación generado
              </h3>
              <p className="text-xs text-green-700 mb-2">
                El email no se pudo enviar (dominio no verificado en Resend). Compartí este link con el nuevo admin manualmente.
              </p>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={invitationLink}
                  className="input flex-1 bg-white text-xs"
                  onFocus={(e) => e.target.select()}
                />
                <button onClick={handleCopy} className="btn btn-outline btn-sm whitespace-nowrap">
                  {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                  {copied ? 'Copiado' : 'Copiar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
          Volver a Inicio
        </button>
      </div>
    </div>
  );
};