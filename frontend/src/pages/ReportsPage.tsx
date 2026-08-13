import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, DollarSign } from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const reportSections = [
    {
      title: 'Reporte de Membresías',
      description: 'Clientes con membresías vencidas o por vencer',
      href: '/reports/solvency',
      icon: AlertTriangle,
      color: 'bg-yellow-100 text-yellow-600',
      stats: 'Clientes morosos'
    },
    {
      title: 'Reporte de Ingresos',
      description: 'Resumen de pagos por período y método',
      href: '/reports/income',
      icon: DollarSign,
      color: 'bg-green-100 text-green-600',
      stats: 'Ingresos por período'
    }
  ];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Reportes</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reportSections.map((section) => (
          <Link
            key={section.href}
            to={section.href}
            className="card hover:shadow-md transition-shadow cursor-pointer"
          >
            <div className="flex items-start space-x-4">
              <div className={`p-4 rounded-xl ${section.color}`}>
                <section.icon className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{section.title}</h3>
                <p className="text-sm text-gray-600 mt-1">{section.description}</p>
                <div className="mt-3 flex items-center text-xs text-gray-500">
                  <section.icon className="h-3 w-3 mr-1" />
                  {section.stats}
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};