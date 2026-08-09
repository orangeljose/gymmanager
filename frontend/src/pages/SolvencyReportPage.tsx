import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import type { SolvencyReport, Branch } from '@/types';
import toast from 'react-hot-toast';
import { ArrowLeft, Phone, Calendar, DollarSign, Filter, Clock, AlertCircle, CheckCircle } from 'lucide-react';

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

  const getStatusBadge = (days: number) => {
    if (days <= 0) return { label: 'Al día', className: 'bg-green-100 text-green-800' };
    if (days <= 7) return { label: 'Por vencer', className: 'bg-yellow-100 text-yellow-800' };
    if (days <= 30) return { label: 'Vencido reciente', className: 'bg-orange-100 text-orange-800' };
    return { label: 'Vencido', className: 'bg-red-100 text-red-800' };
  };

  const getStatusIcon = (days: number) => {
    if (days <= 0) return <CheckCircle className="h-5 w-5 text-green-600" />;
    if (days <= 7) return <Clock className="h-5 w-5 text-yellow-600" />;
    return <AlertCircle className="h-5 w-5 text-red-600" />;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner h-10 w-10"></div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6">
      <Link to="/reports" className="btn btn-ghost btn-sm mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" />
        Volver a Reportes
      </Link>

      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Seguimiento de Membresías</h1>
          <p className="text-sm text-gray-600 mt-1">Gestioná renovaciones y vencimientos de tus clientes</p>
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
          <div className="w-full sm:w-56">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Estado
            </label>
            <select
              value={daysOverdue}
              onChange={(e) => setDaysOverdue(Number(e.target.value))}
              className="input w-full"
            >
              <option value="-999">Todos</option>
              <option value="-7">Próximos 7 días</option>
              <option value="0">Vencidos</option>
              <option value="7">+7 días vencido</option>
              <option value="30">+30 días vencido</option>
            </select>
          </div>
        </div>
      </div>

      {reportData.length === 0 ? (
        <div className="card text-center py-12">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay membresías por vencer</h3>
          <p className="text-gray-600">Todos tus clientes están al día</p>
        </div>
      ) : (
        <>
          <div className="text-sm text-gray-600 mb-4">
            {reportData.length} cliente{reportData.length !== 1 ? 's' : ''} encontrado{reportData.length !== 1 ? 's' : ''}
          </div>
          <div className="space-y-3">
            {reportData.map((client) => {
              const badge = getStatusBadge(client.daysOverdue);
              return (
                <div key={client.id} className="card">
                  <div className="flex items-start gap-4">
                    <div className="mt-1">{getStatusIcon(client.daysOverdue)}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Link to={`/clients/${client.id}`} className="font-semibold text-gray-900 hover:text-primary-600">
                          {client.name}
                        </Link>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.className}`}>
                          {badge.label}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-3 text-sm text-gray-600">
                        <span className="flex items-center">
                          <Phone className="h-3.5 w-3.5 mr-1" />
                          {client.phone}
                        </span>
                        <span className="flex items-center">
                          <Calendar className="h-3.5 w-3.5 mr-1" />
                          {client.daysOverdue <= 0
                            ? `Vence: ${formatDate(client.membershipEnd)}`
                            : `Venció: ${formatDate(client.membershipEnd)} (${client.daysOverdue} días)`
                          }
                        </span>
                        {client.lastPaymentDate && (
                          <span className="flex items-center">
                            <DollarSign className="h-3.5 w-3.5 mr-1" />
                            Último: {formatCurrency(client.lastPaymentAmount || 0)} ({formatDate(client.lastPaymentDate)})
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};