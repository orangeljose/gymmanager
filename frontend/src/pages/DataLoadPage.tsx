import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, ArrowLeft, Download, Construction } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

export const DataLoadPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedBusinessId, businesses } = useAuth();
  const [selectedBizId, setSelectedBizId] = useState(selectedBusinessId || '');

  const currentBusiness = businesses.find(b => b.id === selectedBizId);

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      <button
        onClick={() => navigate('/admin')}
        className="flex items-center text-gray-600 hover:text-gray-900 mb-4 sm:mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Volver a Administración
      </button>

      <div className="flex items-center space-x-3 mb-4 sm:mb-6">
        <div className="p-2 bg-purple-100 rounded-lg">
          <Upload className="h-5 w-5 sm:h-6 sm:w-6 text-purple-600" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Cargar Datos</h1>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">Importa clientes y pagos desde un archivo Excel</p>
        </div>
      </div>

      {/* Banner de construcción */}
      <div className="mb-6 sm:mb-8 p-3 sm:p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2 sm:gap-3">
        <Construction className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-amber-800 font-medium text-sm sm:text-base">Funcionalidad en desarrollo</p>
          <p className="text-amber-700 text-xs sm:text-sm mt-0.5">La lógica de importación se implementará pronto. Por ahora podés ver la estructura esperada.</p>
        </div>
      </div>

      {/* Selector de negocio destino */}
      <div className="bg-white rounded-lg shadow-sm p-4 sm:p-6 mb-4 sm:mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Negocio destino
        </label>
        <select
          value={selectedBizId}
          onChange={(e) => setSelectedBizId(e.target.value)}
          className="w-full sm:w-80 px-3 sm:px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
        >
          <option value="">Seleccionar negocio...</option>
          {businesses.map(b => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>
        {currentBusiness && (
          <p className="text-xs text-gray-500 mt-2">
            ID: {currentBusiness.id}
          </p>
        )}
      </div>

      {/* Área de drop */}
      <div className="bg-white rounded-lg shadow-sm p-4 sm:p-6 mb-4 sm:mb-6">
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 sm:p-12 text-center hover:border-primary-400 transition-colors cursor-not-allowed opacity-60">
          <Download className="h-8 w-8 sm:h-12 sm:w-12 text-gray-400 mx-auto mb-3 sm:mb-4" />
          <p className="text-base sm:text-lg text-gray-500 mb-1 sm:mb-2">Arrastrá tu archivo Excel aquí</p>
          <p className="text-xs sm:text-sm text-gray-400">o hacé clic para seleccionarlo</p>
          <p className="text-xs text-gray-400 mt-3 sm:mt-4">Formatos soportados: .xlsx, .xls</p>
        </div>
      </div>

      {/* Columnas esperadas - versión mobile */}
      <div className="md:hidden space-y-3 mb-4">
        <h3 className="text-sm font-semibold text-gray-900">Columnas esperadas</h3>
        {[
          { label: 'Nombre Cliente', ejemplo: 'Juan Pérez' },
          { label: 'Fecha Pago', ejemplo: '15/01/2026' },
          { label: 'Método Pago', ejemplo: 'Efectivo' },
          { label: 'Monto', ejemplo: '35.00' },
          { label: 'Plan', ejemplo: 'Mensual' },
        ].map((col, i) => (
          <div key={i} className="bg-white rounded-lg shadow-sm p-3 flex justify-between items-center">
            <span className="text-xs font-medium text-gray-600">{col.label}</span>
            <span className="text-xs text-gray-400 italic">Ej: {col.ejemplo}</span>
          </div>
        ))}
      </div>

      {/* Columnas esperadas - versión desktop */}
      <div className="hidden md:block bg-white rounded-lg shadow-sm p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4">Columnas esperadas</h3>
        <div className="overflow-x-auto -mx-4 sm:mx-0">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-3 sm:px-4 py-2 text-left font-medium text-gray-600">Nombre Cliente</th>
                <th className="px-3 sm:px-4 py-2 text-left font-medium text-gray-600">Fecha Pago</th>
                <th className="px-3 sm:px-4 py-2 text-left font-medium text-gray-600">Método Pago</th>
                <th className="px-3 sm:px-4 py-2 text-left font-medium text-gray-600">Monto</th>
                <th className="px-3 sm:px-4 py-2 text-left font-medium text-gray-600">Plan</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-gray-100">
                <td className="px-3 sm:px-4 py-2 text-gray-400 italic">Ej: Juan Pérez</td>
                <td className="px-3 sm:px-4 py-2 text-gray-400 italic">15/01/2026</td>
                <td className="px-3 sm:px-4 py-2 text-gray-400 italic">Efectivo</td>
                <td className="px-3 sm:px-4 py-2 text-gray-400 italic">35.00</td>
                <td className="px-3 sm:px-4 py-2 text-gray-400 italic">Mensual</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};