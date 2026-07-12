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
  AlertCircle,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useOffline } from '@/hooks/useOffline';
import type { NavItem, UserRole } from '@/types';

interface SubMenuItem {
  label: string;
  href: string;
  roles?: UserRole[];
}

const navigation: (NavItem & { submenu?: SubMenuItem[] })[] = [
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
    label: 'Reportes',
    href: '/reports',
    icon: 'FileText',
    roles: ['super_admin', 'admin', 'branch_admin', 'cashier'],
    submenu: [
      { label: 'Morosos', href: '/reports/solvency', roles: ['super_admin', 'admin', 'branch_admin', 'cashier'] },
      { label: 'Ingresos', href: '/reports/income', roles: ['super_admin', 'admin', 'branch_admin'] }
    ]
  },
  {
    label: 'Administración',
    href: '/admin',
    icon: 'Settings',
    roles: ['super_admin', 'admin'],
    submenu: [
      { label: 'Negocios', href: '/businesses', roles: ['super_admin'] },
      { label: 'Negocio', href: '/admin/businesses/create', roles: ['admin'] },
      { label: 'Planes', href: '/plans', roles: ['super_admin', 'admin', 'branch_admin'] },
      { label: 'Cuentas de Pago', href: '/payment-accounts', roles: ['super_admin', 'admin', 'branch_admin'] },
      { label: 'Recibos', href: '/receipts', roles: ['super_admin', 'admin', 'branch_admin'] },
      { label: 'Sucursales', href: '/branches', roles: ['super_admin'] },
      { label: 'Usuarios', href: '/users', roles: ['super_admin', 'admin', 'branch_admin'] },
      { label: 'Agregar Admin', href: '/add-admin', roles: ['super_admin'] },
      { label: 'Cargar Datos', href: '/admin/data-load', roles: ['super_admin'] }
    ]
  }
];

const iconMap: Record<string, React.ElementType> = {
  Home,
  Users,
  CreditCard,
  FileText,
  Settings
};

export const Layout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState<string[]>([]);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, hasRole, selectedBusinessId, businesses, switchBusiness } = useAuth();
  const { isOnline, hasPendingData } = useOffline();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const toggleMenu = (href: string) => {
    setExpandedMenus(prev =>
      prev.includes(href)
        ? prev.filter(h => h !== href)
        : [...prev, href]
    );
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

  const isSubmenuActive = (submenu: SubMenuItem[]) => {
    return submenu.some(item => location.pathname === item.href);
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
        <div className="flex items-center justify-between h-16 px-6 bg-primary-600">
          <div className="flex items-center">
            <img src="/logo.svg" alt="GoatGym" className="h-8 w-auto mr-2" />
            <h1 className="text-xl font-extrabold tracking-tight text-white">GoatGym</h1>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 rounded-md text-primary-100 hover:text-white hover:bg-primary-500"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <nav className="mt-6 px-3">
          <ul className="space-y-1">
            {filteredNavigation.map((item) => {
              const Icon = iconMap[item.icon as keyof typeof iconMap];
              const active = isActiveRoute(item.href);
              const hasSubmenu = item.submenu && item.submenu.length > 0;
              const isExpanded = expandedMenus.includes(item.href);
              const submenuActive = hasSubmenu && isSubmenuActive(item.submenu!);

              return (
                <li key={item.href}>
                  {hasSubmenu ? (
                    <div>
                      <button
                        onClick={() => toggleMenu(item.href)}
                        className={`
                          w-full group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors
                          ${submenuActive
                            ? 'bg-primary-600 text-white font-semibold shadow-md'
                            : 'text-gray-600 hover:bg-primary-50 hover:text-primary-700'
                          }
                        `}
                      >
                        <Icon className="mr-3 h-5 w-5" />
                        <span className="flex-1 text-left">{item.label}</span>
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-400" />
                        )}
                      </button>
                      {isExpanded && item.submenu && (
                        <ul className="ml-6 mt-1 space-y-1 border-l border-gray-200">
                          {item.submenu
                            .filter(subItem => !subItem.roles || hasRole(subItem.roles))
                            .map((subItem) => (
                            <li key={subItem.href}>
                              <Link
                                to={subItem.href}
                                className={`
                                  block px-3 py-2 text-sm rounded-md transition-colors
                                  ${location.pathname === subItem.href
                                    ? 'bg-primary-100 text-primary-700 font-medium'
                                    : 'text-gray-500 hover:bg-primary-50 hover:text-primary-700'
                                  }
                                `}
                                onClick={() => setSidebarOpen(false)}
                              >
                                {subItem.label}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ) : (
                    <Link
                      to={item.href}
                      className={`
                        group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors
                        ${active
                          ? 'bg-primary-600 text-white font-semibold shadow-md'
                          : 'text-gray-600 hover:bg-primary-50 hover:text-primary-700'
                        }
                      `}
                      onClick={() => setSidebarOpen(false)}
                    >
                      <Icon className="mr-3 h-5 w-5" />
                      {item.label}
                    </Link>
                  )}
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
            className="w-full flex items-center px-3 py-2 text-sm font-medium text-gray-600 rounded-md hover:bg-primary-50 hover:text-primary-700 transition-colors"
          >
            <LogOut className="mr-3 h-4 w-4" />
            Cerrar sesión
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 lg:ml-0">
        {/* Top bar */}
        <header className="bg-primary-600 shadow-md">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-md text-white hover:text-primary-100 hover:bg-primary-500"
            >
              <Menu className="h-6 w-6" />
            </button>

            <div className="flex items-center space-x-4">
              {/* Business selector - solo super_admin */}
              {user?.role === 'super_admin' && businesses.length > 0 && (
                <select
                  value={selectedBusinessId || ''}
                  onChange={(e) => switchBusiness(e.target.value)}
                  className="text-sm border border-primary-400 rounded-md px-3 py-1.5 bg-primary-500 text-white focus:outline-none focus:ring-2 focus:ring-white focus:border-white max-w-[200px] truncate"
                >
                  {businesses.map(b => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              )}

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
