import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '@/services/api';
import { firebaseAuth } from '@/services/firebase';
import toast from 'react-hot-toast';
import { Mail, User, Building, ArrowRight, AlertCircle } from 'lucide-react';

interface InvitationData {
  valid: boolean;
  email: string;
  role: string;
  name?: string;
  businessId?: string;
  branchId?: string;
  businessName?: string;
  invitedByName: string;
  requiresOnboarding: boolean;
}

export const InvitePage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [invitation, setInvitation] = useState<InvitationData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Onboarding state (for admin registration - only when requiresOnboarding is true)
  const [businessName, setBusinessName] = useState('');
  const [branchName, setBranchName] = useState('');

  useEffect(() => {
    const urlToken = searchParams.get('token');
    const actualToken = token || urlToken;

    if (actualToken) {
      validateToken(actualToken);
    } else {
      setError('Token de invitación no proporcionado');
      setLoading(false);
    }
  }, [token, searchParams]);

  const validateToken = async (inviteToken: string) => {
    try {
      setLoading(true);
      const response = await apiService.validateInvitation(inviteToken);

      if (response.success && response.data) {
        if (!response.data.valid) {
          setError('Esta invitación no es válida o ha expirado');
        } else {
          setInvitation(response.data);
          setName(response.data.name || '');
        }
      } else {
        setError(response.error?.message || 'Error validando invitación');
      }
    } catch (err: any) {
      setError(err.message || 'Error validando invitación');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!invitation) return;

    if (password.length < 8) {
      toast.error('La contraseña debe tener al menos 8 caracteres');
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Las contraseñas no coinciden');
      return;
    }

    // Validate onboarding fields if required
    if (invitation.requiresOnboarding && (!businessName.trim() || !branchName.trim())) {
      toast.error('El nombre del negocio y sucursal son requeridos');
      return;
    }

    try {
      setSubmitting(true);

      // Create user in Firebase Auth
      const result = await firebaseAuth.createUser(invitation.email, password);

      if (!result.success || !result.user) {
        toast.error(result.error?.message || 'Error creando cuenta');
        setSubmitting(false);
        return;
      }

      const uid = result.user.uid;

      // Only create business and branch if requiresOnboarding is true
      // (for admin registering for the first time with their own business)
      if (invitation.requiresOnboarding && businessName.trim() && branchName.trim()) {
        // Create business via API (uses fresh token internally)
        const businessResponse = await apiService.createBusiness({ name: businessName.trim() });

        if (!businessResponse.success || !businessResponse.data) {
          toast.error(businessResponse.error?.message || 'Error creando negocio');
          setSubmitting(false);
          return;
        }

        const newBusinessId = businessResponse.data.id;

        // Create branch for the new business
        await apiService.createBranch({
          name: branchName.trim(),
          address: '',
          phone: '',
          businessId: newBusinessId
        });
      }

      // Accept invitation (link Firebase UID to Firestore user)
      // Backend will use businessId/branchId from the invitation document
      const acceptResponse = await apiService.acceptInvitation(
        token || searchParams.get('token') || '',
        uid,
        name.trim()
      );

      if (acceptResponse.success) {
        // Sign out to prevent auto-verify trigger that would fail
        // User must login manually with their new credentials
        await firebaseAuth.signOut();
        toast.success('¡Cuenta creada exitosamente!');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else {
        toast.error(acceptResponse.error?.message || 'Error creando usuario');
      }

    } catch (err: any) {
      console.error('Error creating account:', err);
      toast.error(err.message || 'Error creando cuenta');
    } finally {
      setSubmitting(false);
    }
  };

  const getRoleLabel = (role: string) => {
    const labels: Record<string, string> = {
      'admin': 'Administrador',
      'branch_admin': 'Encargado de Sucursal',
      'cashier': 'Cajero',
      'trainer': 'Entrenador'
    };
    return labels[role] || role;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="loading-spinner h-12 w-12 mx-auto mb-4"></div>
          <p className="text-gray-600">Validando invitación...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="card max-w-md w-full text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Invitación Inválida</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => navigate('/login')}
            className="btn btn-primary"
          >
            Ir a Login
          </button>
        </div>
      </div>
    );
  }

  if (!invitation) return null;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="h-16 w-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Mail className="h-8 w-8 text-primary-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Invitación</h1>
          <p className="text-gray-600 mt-2">
            Te han invitado como <span className="font-semibold text-primary-600">{getRoleLabel(invitation.role)}</span>
          </p>
        </div>

        <div className="card">
          {/* Invitation details */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="flex items-center space-x-3 mb-3">
              <User className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500">Email</p>
                <p className="font-medium text-gray-900">{invitation.email}</p>
              </div>
            </div>

            {invitation.businessName && (
              <div className="flex items-center space-x-3 mb-3">
                <Building className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Negocio</p>
                  <p className="font-medium text-gray-900">{invitation.businessName}</p>
                </div>
              </div>
            )}

            <div className="flex items-center space-x-3">
              <User className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500">Invitado por</p>
                <p className="font-medium text-gray-900">{invitation.invitedByName}</p>
              </div>
            </div>
          </div>

          {/* Onboarding section - only for admin registering for first time */}
          {invitation.requiresOnboarding && (
            <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
              <h3 className="font-semibold text-primary-900 mb-2">Crear tu Negocio</h3>
              <p className="text-sm text-primary-700 mb-4">
                Como primer administrador, necesitas crear tu negocio y sucursal para continuar.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre del Negocio *
                  </label>
                  <input
                    type="text"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    className="input"
                    placeholder="Ej: Gimnasio Central"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre de la Sucursal *
                  </label>
                  <input
                    type="text"
                    value={branchName}
                    onChange={(e) => setBranchName(e.target.value)}
                    className="input"
                    placeholder="Ej: Sede Principal"
                    required
                  />
                </div>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre Completo *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input"
                placeholder="Tu nombre"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña *
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="Mínimo 8 caracteres"
                minLength={8}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirmar Contraseña *
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="input"
                placeholder="Repite la contraseña"
                minLength={8}
                required
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="btn btn-primary w-full flex items-center justify-center"
            >
              {submitting ? (
                <>
                  <div className="loading-spinner h-4 w-4 mr-2"></div>
                  Creando cuenta...
                </>
              ) : (
                <>
                  Crear Cuenta
                  <ArrowRight className="h-4 w-4 ml-2" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">
              ¿Ya tienes cuenta?{' '}
              <button
                onClick={() => navigate('/login')}
                className="text-primary-600 hover:text-primary-700 font-medium"
              >
                Iniciar sesión
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};