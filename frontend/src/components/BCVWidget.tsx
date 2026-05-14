import React, { useState, useEffect } from 'react';
import { apiService } from '@/services/api';
import { RefreshCw } from 'lucide-react';

interface BCVWidgetProps {
  className?: string;
}

export const BCVWidget: React.FC<BCVWidgetProps> = ({ className = '' }) => {
  const [rate, setRate] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  const fetchRate = async () => {
    try {
      setLoading(true);
      const response = await apiService.getExchangeRate();
      if (response.success && response.data) {
        setRate(response.data.rate);
        setLastUpdate(new Date().toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' }));
      }
    } catch (error) {
      console.error('Error fetching BCV rate:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRate();
    const interval = setInterval(fetchRate, 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (rate === null) return null;

  return (
    <div className={`flex items-center space-x-2 px-3 py-2 bg-gray-100 rounded-lg text-sm ${className}`}>
      <span className="text-gray-600">Tasa BCV:</span>
      <span className="font-semibold text-gray-900">
        {rate.toFixed(2)} Bs/$
      </span>
      <button
        onClick={fetchRate}
        disabled={loading}
        className="text-gray-500 hover:text-gray-700 disabled:opacity-50"
        title="Actualizar tasa"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
      </button>
      {lastUpdate && (
        <span className="text-xs text-gray-400">{lastUpdate}</span>
      )}
    </div>
  );
};