import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import type { UserRole } from '@/types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: UserRole[];
  requiredPermissions?: string[];
  fallbackPath?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRoles,
  requiredPermissions,
  fallbackPath = '/login'
}) => {
  const { isAuthenticated, isLoading, hasRole, hasPermission } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center space-y-4">
          <div className="loading-spinner h-12 w-12"></div>
          <p className="text-gray-600">Verificando autenticación...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to={fallbackPath} state={{ from: location }} replace />;
  }

  // Check role requirements
  if (requiredRoles && requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some(role => hasRole(role));
    if (!hasRequiredRole) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Acceso Denegado</h1>
            <p className="text-gray-600 mb-6">
              No tienes los permisos necesarios para acceder a esta página.
            </p>
            <button
              onClick={() => window.history.back()}
              className="btn btn-primary"
            >
              Volver
            </button>
          </div>
        </div>
      );
    }
  }

  // Check permission requirements
  if (requiredPermissions && requiredPermissions.length > 0) {
    const hasRequiredPermission = requiredPermissions.some(permission => hasPermission(permission));
    if (!hasRequiredPermission) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Acceso Denegado</h1>
            <p className="text-gray-600 mb-6">
              No tienes los permisos necesarios para acceder a esta página.
            </p>
            <button
              onClick={() => window.history.back()}
              className="btn btn-primary"
            >
              Volver
            </button>
          </div>
        </div>
      );
    }
  }

  // User is authenticated and has required permissions
  return <>{children}</>;
};
