import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { firebaseAuth } from '@/services/firebase';
import { apiService } from '@/services/api';
import type { AuthState } from '@/types';

interface AuthContextType extends AuthState {
  error: string | null;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<{ success: boolean; error?: string }>;
  clearError: () => void;
  hasRole: (role: string | string[]) => boolean;
  hasPermission: (permission: string) => boolean;
  canAccessResource: (businessId?: string, branchId?: string) => boolean;
  switchBusiness: (businessId: string) => void;
  loadBusinesses: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    selectedBusinessId: null,
    businesses: []
  });

  const [error, setError] = useState<string | null>(null);

  // Restaurar selectedBusinessId desde localStorage al iniciar
  useEffect(() => {
    const saved = localStorage.getItem('gm_selectedBusinessId');
    if (saved) {
      setAuthState(prev => ({ ...prev, selectedBusinessId: saved }));
    }
  }, []);

  // Fetch businesses solo para super_admin cuando el usuario cambia
  useEffect(() => {
    if (authState.user?.role === 'super_admin') {
      apiService.getBusinesses().then(res => {
        if (res.success && res.data) {
          setAuthState(prev => ({
            ...prev,
            businesses: res.data,
            selectedBusinessId: prev.selectedBusinessId || res.data[0]?.id || null
          }));
        }
      }).catch(console.error);
    } else if (authState.user) {
      setAuthState(prev => ({
        ...prev,
        selectedBusinessId: authState.user?.businessId || null,
        businesses: []
      }));
    }
  }, [authState.user?.id, authState.user?.role]);

  const switchBusiness = useCallback((businessId: string) => {
    setAuthState(prev => ({ ...prev, selectedBusinessId: businessId }));
    localStorage.setItem('gm_selectedBusinessId', businessId);
  }, []);

  const loadBusinesses = useCallback(async () => {
    if (authState.user?.role !== 'super_admin') return;
    try {
      const res = await apiService.getBusinesses();
      if (res.success && res.data) {
        setAuthState(prev => ({
          ...prev,
          businesses: res.data
        }));
      }
    } catch (e) {
      console.error('Error loading businesses:', e);
    }
  }, [authState.user?.role]);

  // Initialize auth state
  useEffect(() => {
    const unsubscribe = firebaseAuth.onAuthStateChanged(async (firebaseUser) => {
      if (firebaseUser) {
        try {
          await new Promise(resolve => setTimeout(resolve, 2000));
          const token = await firebaseAuth.getIdToken();
          
          if (token) {
            const response = await apiService.verifyToken(token);
            if (response.success && response.data) {
              setAuthState(prev => ({
                ...prev,
                user: response.data,
                isLoading: false,
                isAuthenticated: true
              }));
            } else {
              setAuthState(prev => ({
                ...prev,
                user: null,
                isLoading: false,
                isAuthenticated: false
              }));
              setError(response.error?.message || 'Error de verificación');
            }
          } else {
            setAuthState(prev => ({
              ...prev,
              user: null,
              isLoading: false,
              isAuthenticated: false
            }));
          }
        } catch (error) {
          console.error('Error verifying token:', error);
          setAuthState(prev => ({
            ...prev,
            user: null,
            isLoading: false,
            isAuthenticated: false
          }));
          setError('Error de autenticación');
        }
      } else {
        setAuthState(prev => ({
          ...prev,
          user: null,
          isLoading: false,
          isAuthenticated: false
        }));
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
        return { success: true };
      } else {
        setError(result.error?.message || 'Error al iniciar sesión');
        setAuthState(prev => ({ ...prev, isLoading: false }));
        return { success: false, error: result.error?.message };
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
        return { success: true };
      } else {
        setError(result.error?.message || 'Error al cerrar sesión');
        setAuthState(prev => ({ ...prev, isLoading: false }));
        return { success: false, error: result.error?.message };
      }
    } catch (error: any) {
      const errorMessage = error.message || 'Error al cerrar sesión';
      setError(errorMessage);
      setAuthState(prev => ({ ...prev, isLoading: false }));
      return { success: false, error: errorMessage };
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const hasRole = useCallback((role: string | string[]): boolean => {
    if (!authState.user) return false;
    if (Array.isArray(role)) return role.includes(authState.user.role);
    return authState.user.role === role;
  }, [authState.user]);

  const hasPermission = useCallback((permission: string): boolean => {
    if (!authState.user) return false;
    if (authState.user.role === 'super_admin') return true;
    return authState.user.permissions.includes(permission);
  }, [authState.user]);

  const canAccessResource = useCallback((businessId?: string, branchId?: string): boolean => {
    if (!authState.user) return false;
    if (authState.user.role === 'super_admin') return true;
    if (businessId && authState.user.businessId !== businessId) return false;
    if (branchId && authState.user.branchId && authState.user.branchId !== branchId) return false;
    return true;
  }, [authState.user]);

  const value: AuthContextType = {
    ...authState,
    error,
    login,
    logout,
    clearError,
    hasRole,
    hasPermission,
    canAccessResource,
    switchBusiness,
    loadBusinesses
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
