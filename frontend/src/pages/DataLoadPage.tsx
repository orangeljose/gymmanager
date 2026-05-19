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
    <div className="p-6 max-w-4xl mx-auto">
      <button
        onClick={() => navigate('/admin')}
        className="flex items-center text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Volver a Administración
      </button>

      <div className="flex items-center space-x-3 mb-6">
        <div className="p-2 bg-purple-100 rounded-lg">
          <Upload className="h-6 w-6 text-purple-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cargar Datos</h1>
          <p className="text-sm text-gray-500 mt-1">Importa clientes y pagos desde un archivo Excel</p>
        </div>
      </div>

      {/* Banner de construcción */}
      <div className="mb-8 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-center">
        <Construction className="h-5 w-5 text-amber-500 mr-3 flex-shrink-0" />
        <div>
          <p className="text-amber-800 font-medium">Funcionalidad en desarrollo</p>
          <p className="text-amber-700 text-sm">La lógica de importación se implementará pronto. Por ahora podés ver la estructura esperada.</p>
        </div>
      </div>

      {/* Selector de negocio destino */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Negocio destino
        </label>
        <select
          value={selectedBizId}
          onChange={(e) => setSelectedBizId(e.target.value)}
          className="w-full md:w-80 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="">Seleccionar negocio...</option>
          {businesses.map(b => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>
        {currentBusiness && (
          <p className="text-xs text-gray-500 mt-2">
            Rubro: {currentBusiness.rubro} • ID: {currentBusiness.id}
          </p>
        )}
      </div>

      {/* Área de drop */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-primary-400 transition-colors cursor-not-allowed opacity-60">
          <Download className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-lg text-gray-500 mb-2">Arrastrá tu archivo Excel aquí</p>
          <p className="text-sm text-gray-400">o hacé clic para seleccionarlo</p>
          <p className="text-xs text-gray-400 mt-4">Formatos soportados: .xlsx, .xls</p>
        </div>
      </div>

      {/* Preview de columnas esperadas */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Columnas esperadas</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-4 py-2 text-left font-medium text-gray-600">Nombre Cliente</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Fecha Pago</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Método Pago</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Monto</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Plan</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-gray-100">
                <td className="px-4 py-2 text-gray-400 italic">Ej: Juan Pérez</td>
                <td className="px-4 py-2 text-gray-400 italic">15/01/2026</td>
                <td className="px-4 py-2 text-gray-400 italic">Efectivo</td>
                <td className="px-4 py-2 text-gray-400 italic">35.00</td>
                <td className="px-4 py-2 text-gray-400 italic">Mensual</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
