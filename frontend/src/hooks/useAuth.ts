import { useState, useEffect, useCallback } from 'react';
import { firebaseAuth } from '@/services/firebase';
import { apiService } from '@/services/api';
import type { AuthState } from '@/types';

export const useAuth = () => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false
  });

  const [error, setError] = useState<string | null>(null);

  // Initialize auth state
  useEffect(() => {
    const unsubscribe = firebaseAuth.onAuthStateChanged(async (firebaseUser) => {
      if (firebaseUser) {
        try {
          
          // Add small delay to avoid "Token used too early" error
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          // Get ID token
          const token = await firebaseAuth.getIdToken();
          
          // Only verify token if we have a valid token
          if (token) {
            // Verify token with backend and get user data
            const response = await apiService.verifyToken(token);
          
            if (response.success && response.data) {
              setAuthState({
                user: response.data,
                isLoading: false,
                isAuthenticated: true
              });
            } else {
              setAuthState({
                user: null,
                isLoading: false,
                isAuthenticated: false
              });
              setError(response.error?.message || 'Error de verificación');
            }
          } else {
            // No token available, set as unauthenticated
            setAuthState({
              user: null,
              isLoading: false,
              isAuthenticated: false
            });
          }
        } catch (error) {
          console.error('Error verifying token:', error);
          setAuthState({
            user: null,
            isLoading: false,
            isAuthenticated: false
          });
          setError('Error de autenticación');
        }
      } else {
        setAuthState({
          user: null,
          isLoading: false,
          isAuthenticated: false
        });
      }
    });

    return () => unsubscribe();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    setAuthState(prev => ({ ...prev, isLoading: true }));

    try {
      const result = await firebaseAuth.signIn(email, password);
      
      if (result.success) {
        // The onAuthStateChanged listener will handle updating the state
        return { success: true };
      } else {
        setError(result.error?.message || 'Error al iniciar sesión');
        setAuthState(prev => ({ ...prev, isLoading: false }));
        return { 
          success: false, 
          error: result.error?.message || 'Error al iniciar sesión' 
        };
      }
    } catch (error: any) {
      const errorMessage = error.message || 'Error al iniciar sesión';
      setError(errorMessage);
      setAuthState(prev => ({ ...prev, isLoading: false }));
      return { success: false, error: errorMessage };
    }
  }, []);

  const logout = useCallback(async () => {
    setError(null);
    setAuthState(prev => ({ ...prev, isLoading: true }));

    try {
      const result = await firebaseAuth.signOut();
      
      if (result.success) {
        // The onAuthStateChanged listener will handle updating the state
        return { success: true };
      } else {
        setError(result.error?.message || 'Error al cerrar sesión');
        setAuthState(prev => ({ ...prev, isLoading: false }));
        return { 
          success: false, 
          error: result.error?.message || 'Error al cerrar sesión' 
        };
      }
    } catch (error: any) {
      const errorMessage = error.message || 'Error al cerrar sesión';
      setError(errorMessage);
      setAuthState(prev => ({ ...prev, isLoading: false }));
      return { success: false, error: errorMessage };
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Helper function to check if user has specific role
  const hasRole = useCallback((role: string | string[]): boolean => {
    if (!authState.user) return false;
    
    if (Array.isArray(role)) {
      return role.includes(authState.user.role);
    }
    
    return authState.user.role === role;
  }, [authState.user]);

  // Helper function to check if user has specific permission
  const hasPermission = useCallback((permission: string): boolean => {
    if (!authState.user) return false;
    
    // Super admin has all permissions
    if (authState.user.role === 'super_admin') return true;
    
    return authState.user.permissions.includes(permission);
  }, [authState.user]);

  // Helper function to check if user can access resource based on business/branch
  const canAccessResource = useCallback((businessId?: string, branchId?: string): boolean => {
    if (!authState.user) return false;
    
    // Super admin can access everything
    if (authState.user.role === 'super_admin') return true;
    
    // Check business access
    if (businessId && authState.user.businessId !== businessId) return false;
    
    // Check branch access for non-super admins
    if (branchId && authState.user.branchId && authState.user.branchId !== branchId) {
      return false;
    }
    
    return true;
  }, [authState.user]);

  return {
    ...authState,
    error,
    login,
    logout,
    clearError,
    hasRole,
    hasPermission,
    canAccessResource
  };
};
