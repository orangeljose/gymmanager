import React from 'react';
import { Link } from 'react-router-dom';
import { CreditCard, Tag, Building, Users, PlusCircle } from 'lucide-react';

export const AdministrationPage: React.FC = () => {
  const adminSections = [
    {
      title: 'Crear Negocio',
      description: 'Crea un nuevo negocio con su configuración inicial',
      href: '/admin/businesses/create',
      icon: PlusCircle,
      color: 'bg-indigo-100 text-indigo-600'
    },
    {
      title: 'Planes de Membresía',
      description: 'Crea y gestiona los planes disponibles para tus clientes',
      href: '/plans',
      icon: Tag,
      color: 'bg-blue-100 text-blue-600'
    },
    {
      title: 'Cuentas de Pago',
      description: 'Administra las cuentas donde recibes pagos (Zelle, Pago Móvil, Bancarias)',
      href: '/payment-accounts',
      icon: CreditCard,
      color: 'bg-green-100 text-green-600'
    },
    {
      title: 'Sucursales',
      description: 'Gestiona las sedes de tu negocio',
      href: '/branches',
      icon: Building,
      color: 'bg-purple-100 text-purple-600'
    },
    {
      title: 'Usuarios',
      description: 'Administra los empleados y sus roles',
      href: '/users',
      icon: Users,
      color: 'bg-orange-100 text-orange-600'
    }
  ];

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Administración</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {adminSections.map((section) => (
          <Link
            key={section.href}
            to={section.href}
            className="card hover:shadow-md transition-shadow cursor-pointer"
          >
            <div className="flex items-start space-x-4">
              <div className={`p-3 rounded-lg ${section.color}`}>
                <section.icon className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{section.title}</h3>
                <p className="text-sm text-gray-600 mt-1">{section.description}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};