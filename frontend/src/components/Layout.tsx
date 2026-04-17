import React, { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  Home, 
  Users, 
  CreditCard, 
  FileText, 
  Settings, 
  LogOut,
  Menu,
  X,
  Wifi,
  WifiOff,
  AlertCircle
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useOffline } from '@/hooks/useOffline';
import type { UserRole, NavItem } from '@/types';

const navigation: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: 'Home'
  },
  {
    label: 'Clientes',
    href: '/clients',
    icon: 'Users'
  },
  {
    label: 'Pagos',
    href: '/payments',
    icon: 'CreditCard',
    roles: ['cashier', 'branch_admin', 'super_admin']
  },
  {
    label: 'Reportes',
    href: '/reports',
    icon: 'FileText',
    roles: ['branch_admin', 'super_admin']
  },
  {
    label: 'Administración',
    href: '/admin',
    icon: 'Settings',
    roles: ['super_admin']
  }
];

const iconMap = {
  Home,
  Users,
  CreditCard,
  FileText,
  Settings
};

export const Layout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, hasRole } = useAuth();
  const { isOnline, hasPendingData } = useOffline();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const filteredNavigation = navigation.filter(item => {
    if (!item.roles) return true;
    return hasRole(item.roles);
  });

  const isActiveRoute = (href: string) => {
    if (href === '/dashboard') {
      return location.pathname === href;
    }
    return location.pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 lg:hidden bg-gray-600 bg-opacity-75"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">GymManager</h1>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <nav className="mt-6 px-3">
          <ul className="space-y-1">
            {filteredNavigation.map((item) => {
              const Icon = iconMap[item.icon as keyof typeof iconMap];
              const active = isActiveRoute(item.href);
              
              return (
                <li key={item.href}>
                  <Link
                    to={item.href}
                    className={`
                      group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors
                      ${active 
                        ? 'bg-primary-100 text-primary-700 border-r-2 border-primary-600' 
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                      }
                    `}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <Icon className="mr-3 h-5 w-5" />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center">
              <div className="h-8 w-8 rounded-full bg-primary-600 flex items-center justify-center">
                <span className="text-white text-sm font-medium">
                  {user?.name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.role?.replace('_', ' ')}</p>
              </div>
            </div>
          </div>
          
          <button
            onClick={handleLogout}
            className="w-full flex items-center px-3 py-2 text-sm font-medium text-gray-600 rounded-md hover:bg-gray-50 hover:text-gray-900 transition-colors"
          >
            <LogOut className="mr-3 h-4 w-4" />
            Cerrar sesión
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 lg:ml-0">
        {/* Top bar */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
            >
              <Menu className="h-6 w-6" />
            </button>

            <div className="flex items-center space-x-4">
              {/* Connection status */}
              <div className="flex items-center space-x-2">
                {isOnline ? (
                  <div className="flex items-center text-green-600">
                    <Wifi className="h-4 w-4 mr-1" />
                    <span className="text-xs font-medium">Conectado</span>
                  </div>
                ) : (
                  <div className="flex items-center text-red-600">
                    <WifiOff className="h-4 w-4 mr-1" />
                    <span className="text-xs font-medium">Sin conexión</span>
                  </div>
                )}
              </div>

              {/* Pending data indicator */}
              {hasPendingData && (
                <div className="flex items-center text-yellow-600">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  <span className="text-xs font-medium">Datos pendientes</span>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
