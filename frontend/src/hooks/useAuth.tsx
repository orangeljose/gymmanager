import { useState, useEffect, useCallback, useRef, createContext, useContext } from 'react';
import { firebaseAuth } from '@/services/firebase';
import { apiService } from '@/services/api';
import type { AuthState } from '@/types';

interface AuthContextType extends AuthState {
  error: string | null;
  authError: string | null;
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
  const [authError, setAuthError] = useState<string | null>(null);

  // Flag para que onAuthStateChanged no interfiera durante login activo
  const isLoggingIn = useRef(false);

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
    let isCancelled = false;

    const unsubscribe = firebaseAuth.onAuthStateChanged(async (firebaseUser) => {
      if (isCancelled) return;
      
      // Si hay un login en progreso, no verificar — el token puede ser parcial
      if (isLoggingIn.current) {
        console.log('⏭️ onAuthStateChanged ignorado (login en progreso)');
        return;
      }
      
      console.log('🔔 onAuthStateChanged:', firebaseUser ? `uid=${firebaseUser.uid}` : 'null (signed out)');

      if (!firebaseUser) {
        setAuthState(prev => ({
          ...prev,
          user: null,
          isLoading: false,
          isAuthenticated: false
        }));
        return;
      }

      try {
        console.log('🔑 Solicitando token (forceRefresh)...');
        const token = await firebaseUser.getIdToken(true);  // forzar refresh
        console.log('🔑 Token recibido (longitud:', token?.length, 'primeros 50:', token?.substring(0, 50) + '...');
        
        if (!token) {
          setAuthError('No se pudo obtener el token de autenticación');
          return;
        }

        console.log('📤 Enviando verifyToken al backend...');
        const response = await apiService.verifyToken(token);
        console.log('📥 Respuesta verifyToken:', JSON.stringify(response));
        if (response.success && response.data) {
          setAuthState(prev => ({
            ...prev,
            user: response.data,
            isLoading: false,
            isAuthenticated: true
          }));
        } else {
          setAuthError(response.error?.message || 'Error de verificación');
          setAuthState(prev => ({
            ...prev,
            user: null,
            isLoading: false,
            isAuthenticated: false
          }));
        }
      } catch (error) {
        console.error('Error verifying token:', error);
        setAuthError('Error de autenticación. Verifica tu conexión.');
      } finally {
        if (!isCancelled) {
          setAuthState(prev => {
            if (prev.isLoading) {
              return { ...prev, isLoading: false, isAuthenticated: false };
            }
            return prev;
          });
        }
      }
    });

    // Safety timeout
    const safetyTimeout = setTimeout(() => {
      if (!isCancelled) {
        setAuthState(prev => {
          if (prev.isLoading) {
            return { ...prev, isLoading: false, isAuthenticated: false };
          }
          return prev;
        });
      }
    }, 5000);

    return () => {
      isCancelled = true;
      unsubscribe();
      clearTimeout(safetyTimeout);
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    setAuthError(null);
    console.log('🔐 login() iniciado para:', email);
    setAuthState(prev => ({ ...prev, isLoading: true }));
    isLoggingIn.current = true;  // ⚡ Bloquear onAuthStateChanged ANTES de signIn

    try {
      // Paso 1: Autenticar con Firebase
      const result = await firebaseAuth.signIn(email, password);
      console.log('🔐 signIn result:', result.success ? 'SUCCESS' : 'FAIL', result.error?.message || '');
      
      if (!result.success) {
        setError(result.error?.message || 'Error al iniciar sesión');
        setAuthState(prev => ({ ...prev, isLoading: false }));
        isLoggingIn.current = false;
        return { success: false, error: result.error?.message };
      }

      // Pequeña espera para asegurar propagación del token en Firebase
      await new Promise(r => setTimeout(r, 3000));
      const token = result.token!;
      console.log('🔑 Verificando token con backend (longitud:', token?.length, ')');
      
      const response = await apiService.verifyToken(token);
      console.log('📥 Respuesta backend:', response.success ? 'OK' : 'FAIL', response.error?.message || '');
      
      if (response.success && response.data) {
        setAuthState(prev => ({
          ...prev,
          user: response.data,
          isLoading: false,
          isAuthenticated: true
        }));
        isLoggingIn.current = false;
        return { success: true };
      } else {
        const errMsg = response.error?.message || 'Error de verificación';
        setError(errMsg);
        setAuthState(prev => ({ ...prev, isLoading: false, isAuthenticated: false }));
        isLoggingIn.current = false;
        return { success: false, error: errMsg };
      }
    } catch (error: any) {
      const errorMessage = error.message || 'Error al iniciar sesión';
      console.error('❌ Error en login:', errorMessage);
      setError(errorMessage);
      setAuthState(prev => ({ ...prev, isLoading: false }));
      isLoggingIn.current = false;
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

  const clearError = useCallback(() => {
    setError(null);
    setAuthError(null);
  }, []);

  const hasRole = useCallback((role: string | string[]): boolean => {
    if (!authState.user) return false;
    if (Array.isArray(role)) return role.includes(authState.user.role);
    return authState.user.role === role;
  }, [authState.user]);

  const hasPermission = useCallback((permission: string): boolean => {
    if (!authState.user) return false;
    if (authState.user.role === 'super_admin') return true;
    // Si permissions está vacío, usar los permisos del rol
    const perms = authState.user.permissions;
    if (perms && perms.length > 0) {
      return perms.includes(permission);
    }
    const ROLE_PERMS: Record<string, string[]> = {
      admin: ['read_clients', 'write_clients', 'read_payments', 'write_payments', 'read_reports', 'manage_business'],
      branch_admin: ['read_clients', 'write_clients', 'read_payments', 'write_payments', 'read_reports'],
      cashier: ['read_clients', 'write_payments', 'read_reports'],
      trainer: ['read_clients']
    };
    return (ROLE_PERMS[authState.user.role] || []).includes(permission);
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
    authError,
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
