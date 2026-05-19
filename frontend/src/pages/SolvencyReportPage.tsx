import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { SolvencyReport, Branch } from '@/types';
import toast from 'react-hot-toast';
import { ArrowLeft, AlertTriangle, Phone, Calendar, DollarSign, Filter } from 'lucide-react';

export const SolvencyReportPage: React.FC = () => {
  const { user, selectedBusinessId } = useAuth();
  const effectiveBusinessId = selectedBusinessId || user?.businessId || "";
  const [reportData, setReportData] = useState<SolvencyReport[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterBranch, setFilterBranch] = useState<string>('');
  const [daysOverdue, setDaysOverdue] = useState<number>(0);

  useEffect(() => {
    loadBranches();
  }, [effectiveBusinessId]);

  useEffect(() => {
    loadReport();
  }, [effectiveBusinessId, filterBranch, daysOverdue]);

  const loadBranches = async () => {
    if (!effectiveBusinessId) return;
    try {
      const response = await apiService.getBranches(effectiveBusinessId);
      if (response.success && response.data) {
        setBranches(response.data);
      }
    } catch (error) {
      console.error('Error loading branches:', error);
    }
  };

  const loadReport = async () => {
    if (!effectiveBusinessId) return;
    try {
      setLoading(true);
      const filters: any = { daysOverdue };
      if (filterBranch) filters.branchId = filterBranch;

      const response = await apiService.getSolvencyReport(filters);
      if (response.success && response.data) {
        setReportData(response.data);
      }
    } catch (error) {
      toast.error('Error cargando reporte');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('es-VE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(cents / 100);
  };

  const getOverdueClass = (days: number) => {
    if (days > 30) return 'bg-red-100 text-red-800';
    if (days > 7) return 'bg-orange-100 text-orange-800';
    return 'bg-yellow-100 text-yellow-800';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <Link to="/reports" className="btn btn-ghost btn-sm mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" />
        Volver a Reportes
      </Link>

      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reporte de Morosidad</h1>
          <p className="text-gray-600 mt-1">Clientes con membresías vencidas</p>
        </div>
      </div>

      <div className="card mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <Filter className="h-4 w-4 inline mr-1" />
              Sucursal
            </label>
            <select
              value={filterBranch}
              onChange={(e) => setFilterBranch(e.target.value)}
              className="input w-full"
            >
              <option value="">Todas las sucursales</option>
              {branches.map((branch) => (
                <option key={branch.id} value={branch.id}>{branch.name}</option>
              ))}
            </select>
          </div>
          <div className="w-full sm:w-48">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Días de atraso mínimo
            </label>
            <select
              value={daysOverdue}
              onChange={(e) => setDaysOverdue(Number(e.target.value))}
              className="input w-full"
            >
              <option value="0">Todos</option>
              <option value="1">Más de 1 día</option>
              <option value="7">Más de 7 días</option>
              <option value="30">Más de 30 días</option>
              <option value="60">Más de 60 días</option>
              <option value="90">Más de 90 días</option>
            </select>
          </div>
        </div>
      </div>

      {reportData.length === 0 ? (
        <div className="card text-center py-12">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="h-8 w-8 text-green-600" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay clientes morosos</h3>
          <p className="text-gray-600">Todos tus clientes están al día con sus pagos</p>
        </div>
      ) : (
        <>
          <div className="text-sm text-gray-600 mb-4">
            {reportData.length} cliente{reportData.length !== 1 ? 's' : ''} encontrado{reportData.length !== 1 ? 's' : ''}
          </div>
          <div className="space-y-3">
            {reportData.map((client) => (
              <div key={client.id} className="card">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold text-gray-900">{client.name}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getOverdueClass(client.daysOverdue)}`}>
                        {client.daysOverdue} días vencido
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                      <div className="flex items-center">
                        <Phone className="h-4 w-4 mr-1" />
                        {client.phone}
                      </div>
                      <div className="flex items-center">
                        <Calendar className="h-4 w-4 mr-1" />
                        Venció: {formatDate(client.membershipEnd)}
                      </div>
                      {client.lastPaymentDate && (
                        <div className="flex items-center">
                          <DollarSign className="h-4 w-4 mr-1" />
                          Último pago: {formatCurrency(client.lastPaymentAmount || 0)} ({formatDate(client.lastPaymentDate)})
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};