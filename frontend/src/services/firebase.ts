import { initializeApp } from 'firebase/app';
import { getAuth, signInWithEmailAndPassword, signOut, User as FirebaseUser } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
import { getStorage } from 'firebase/storage';
import type { EnvConfig } from '@/types';

// Firebase configuration
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase services
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);

// Authentication functions
export const firebaseAuth = {
  signIn: async (email: string, password: string) => {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      return {
        success: true,
        user: userCredential.user,
        token: await userCredential.user.getIdToken()
      };
    } catch (error: any) {
      console.error('Firebase sign in error:', error);
      return {
        success: false,
        error: {
          code: error.code,
          message: getAuthErrorMessage(error.code)
        }
      };
    }
  },

  signOut: async () => {
    try {
      await signOut(auth);
      return { success: true };
    } catch (error: any) {
      console.error('Firebase sign out error:', error);
      return {
        success: false,
        error: {
          code: error.code,
          message: getAuthErrorMessage(error.code)
        }
      };
    }
  },

  getCurrentUser: (): FirebaseUser | null => {
    return auth.currentUser;
  },

  getIdToken: async (): Promise<string | null> => {
    const user = auth.currentUser;
    if (user) {
      try {
        return await user.getIdToken();
      } catch (error) {
        console.error('Error getting ID token:', error);
        return null;
      }
    }
    return null;
  },

  onAuthStateChanged: (callback: (user: FirebaseUser | null) => void) => {
    return auth.onAuthStateChanged(callback);
  }
};

// Helper function to get user-friendly error messages
function getAuthErrorMessage(errorCode: string): string {
  switch (errorCode) {
    case 'auth/user-not-found':
      return 'Usuario no encontrado';
    case 'auth/wrong-password':
      return 'Contraseña incorrecta';
    case 'auth/email-already-in-use':
      return 'El correo electrónico ya está en uso';
    case 'auth/weak-password':
      return 'La contraseña es muy débil';
    case 'auth/invalid-email':
      return 'Correo electrónico inválido';
    case 'auth/user-disabled':
      return 'Usuario deshabilitado';
    case 'auth/too-many-requests':
      return 'Demasiados intentos. Intente más tarde';
    case 'auth/network-request-failed':
      return 'Error de conexión. Verifique su internet';
    case 'auth/internal-error':
      return 'Error interno del servidor';
    default:
      return 'Error de autenticación desconocido';
  }
}

// Environment configuration
export const envConfig: EnvConfig = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:5000/api',
  firebaseApiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  firebaseAuthDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
  firebaseProjectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
  firebaseStorageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
  firebaseMessagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
  firebaseAppId: import.meta.env.VITE_FIREBASE_APP_ID || '',
  appName: import.meta.env.VITE_APP_NAME || 'GymManager',
  environment: import.meta.env.VITE_ENVIRONMENT || 'development',
  enableOffline: import.meta.env.VITE_ENABLE_OFFLINE === 'true'
};

export default app;
