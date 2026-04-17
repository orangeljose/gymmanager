import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, Mail, Lock, Dumbbell } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useOffline } from '@/hooks/useOffline';

export const LoginPage: React.FC = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, error } = useAuth();
  const { isOnline } = useOffline();

  const from = location.state?.from?.pathname || '/dashboard';

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear error for this field when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.email.trim()) {
      newErrors.email = 'El correo electrónico es requerido';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'El correo electrónico no es válido';
    }

    if (!formData.password.trim()) {
      newErrors.password = 'La contraseña es requerida';
    } else if (formData.password.length < 6) {
      newErrors.password = 'La contraseña debe tener al menos 6 caracteres';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    if (!isOnline) {
      setErrors({ 
        submit: 'No hay conexión a internet. Verifique su conexión e intente nuevamente.' 
      });
      return;
    }

    const result = await login(formData.email, formData.password);
    
    if (result.success) {
      navigate(from, { replace: true });
    } else {
      setErrors({ submit: result.error || 'Error al iniciar sesión' });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-primary-600 rounded-full flex items-center justify-center">
            <Dumbbell className="h-8 w-8 text-white" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            GymManager
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Inicia sesión para administrar tu gimnasio
          </p>
        </div>

        {/* Login form */}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            {/* Email field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Correo electrónico
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={formData.email}
                  onChange={handleInputChange}
                  className={`
                    input pl-10
                    ${errors.email ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
                  `}
                  placeholder="correo@ejemplo.com"
                />
              </div>
              {errors.email && (
                <p className="mt-1 text-sm text-red-600">{errors.email}</p>
              )}
            </div>

            {/* Password field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Contraseña
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  className={`
                    input pl-10 pr-10
                    ${errors.password ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
                  `}
                  placeholder="•••••••••"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-sm text-red-600">{errors.password}</p>
              )}
            </div>
          </div>

          {/* Submit error */}
          {errors.submit && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-sm text-red-800">{errors.submit}</p>
            </div>
          )}

          {/* Submit button */}
          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary btn-md w-full flex justify-center"
            >
              {isLoading ? (
                <div className="loading-spinner h-5 w-5 mr-2"></div>
              ) : null}
              {isLoading ? 'Iniciando sesión...' : 'Iniciar sesión'}
            </button>
          </div>

          {/* Connection status */}
          {!isOnline && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
              <p className="text-sm text-yellow-800">
                <strong>Sin conexión a internet</strong> - Algunas funciones pueden no estar disponibles.
              </p>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="text-center">
          <p className="text-sm text-gray-600">
            ¿Problemas para iniciar sesión?{' '}
            <button className="font-medium text-primary-600 hover:text-primary-500">
              Contacta al administrador
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};
