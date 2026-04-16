import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

// Components
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { OfflineIndicator } from '@/components/OfflineIndicator';

// Pages
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ClientsPage } from '@/pages/ClientsPage';
import { ClientDetailPage } from '@/pages/ClientDetailPage';
import { ClientFormPage } from '@/pages/ClientFormPage';
import { ReportsPage } from '@/pages/ReportsPage';
import { SolvencyReportPage } from '@/pages/SolvencyReportPage';
import { IncomeReportPage } from '@/pages/IncomeReportPage';
import { AdministrationPage } from '@/pages/AdministrationPage';
import { BranchesPage } from '@/pages/BranchesPage';
import { UsersPage } from '@/pages/UsersPage';

// Loading component
const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="flex flex-col items-center space-y-4">
      <div className="loading-spinner h-12 w-12"></div>
      <p className="text-gray-600">Cargando...</p>
    </div>
  </div>
);

const App: React.FC = () => {
  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* Protected routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            {/* Default redirect */}
            <Route index element={<Navigate to="/dashboard" replace />} />
            
            {/* Dashboard */}
            <Route path="dashboard" element={
              <Suspense fallback={<LoadingSpinner />}>
                <DashboardPage />
              </Suspense>
            } />
            
            {/* Clients */}
            <Route path="clients" element={
              <Suspense fallback={<LoadingSpinner />}>
                <ClientsPage />
              </Suspense>
            } />
            <Route path="clients/:id" element={
              <Suspense fallback={<LoadingSpinner />}>
                <ClientDetailPage />
              </Suspense>
            } />
            <Route path="clients/new" element={
              <ProtectedRoute requiredRoles={['branch_admin', 'super_admin']}>
                <Suspense fallback={<LoadingSpinner />}>
                  <ClientFormPage />
                </Suspense>
              </ProtectedRoute>
            } />
            <Route path="clients/:id/edit" element={
              <ProtectedRoute requiredRoles={['branch_admin', 'super_admin']}>
                <Suspense fallback={<LoadingSpinner />}>
                  <ClientFormPage />
                </Suspense>
              </ProtectedRoute>
            } />
            
            {/* Reports */}
            <Route path="reports" element={
              <ProtectedRoute requiredRoles={['branch_admin', 'super_admin']}>
                <Suspense fallback={<LoadingSpinner />}>
                  <ReportsPage />
                </Suspense>
              </ProtectedRoute>
            }>
              <Route path="solvency" element={
                <Suspense fallback={<LoadingSpinner />}>
                  <SolvencyReportPage />
                </Suspense>
              } />
              <Route path="income" element={
                <Suspense fallback={<LoadingSpinner />}>
                  <IncomeReportPage />
                </Suspense>
              } />
            </Route>
            
            {/* Administration */}
            <Route path="admin" element={
              <ProtectedRoute requiredRoles={['super_admin']}>
                <Suspense fallback={<LoadingSpinner />}>
                  <AdministrationPage />
                </Suspense>
              </ProtectedRoute>
            }>
              <Route path="branches" element={
                <Suspense fallback={<LoadingSpinner />}>
                  <BranchesPage />
                </Suspense>
              } />
              <Route path="users" element={
                <Suspense fallback={<LoadingSpinner />}>
                  <UsersPage />
                </Suspense>
              } />
            </Route>
            
            {/* Catch all */}
            <Route path="*" element={
              <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                  <h1 className="text-2xl font-bold text-gray-900 mb-2">Página no encontrada</h1>
                  <p className="text-gray-600 mb-6">
                    La página que estás buscando no existe.
                  </p>
                  <button
                    onClick={() => window.history.back()}
                    className="btn btn-primary"
                  >
                    Volver
                  </button>
                </div>
              </div>
            } />
          </Route>
        </Routes>
        
        {/* Global components */}
        <OfflineIndicator />
        <Toaster 
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#4ade80',
                secondary: '#ffffff',
              },
            },
            error: {
              duration: 5000,
            },
          }}
        />
      </div>
    </Router>
  );
};

export default App;
