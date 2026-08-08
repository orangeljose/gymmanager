import { envConfig } from './firebase';
import type {
  ApiResponse,
  User,
  Client,
  ClientFilters,
  ClientFormData,
  Payment,
  PaymentFormData,
  PaymentFilters,
  Branch,
  BranchFormData,
  Business,
  MembershipPlan,
  SolvencyReport,
  IncomeDailyReport,
  IncomeByMethodReport,
  ReportFilters,
  PaymentAccount,
  PaymentAccountFormData,
  PlanFormData,
  UserRole,
  Receipt,
  UserFormData,
  DashboardData,
  ReceiptFilters
} from '@/types';

class ApiService {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;

  constructor() {
    this.baseURL = envConfig.apiUrl;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    
    // Debug logging
    console.log('🚀 API Request:', {
      url,
      method: options.method || 'GET',
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      }
    });
    
    try {
      const response = await fetch(url, {
        ...options,
        credentials: 'include', // Importante para CORS con credenciales
        headers: {
          ...this.defaultHeaders,
          ...options.headers,
        },
      });
      
      // Debug response
      console.log('📥 API Response:', {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries())
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || `HTTP error! status: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('API request error:', error);
      throw error;
    }
  }

  private async requestWithAuth<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const token = await this.getAuthToken();
    
    if (!token) {
      throw new Error('No authentication token available');
    }

    return this.request<T>(endpoint, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    });
  }

  private async getAuthToken(): Promise<string | null> {
    try {
      const { firebaseAuth } = await import('./firebase');
      return await firebaseAuth.getIdToken();
    } catch (error) {
      console.error('Error getting auth token:', error);
      return null;
    }
  }

  // Authentication
  async verifyToken(token: string): Promise<ApiResponse<User>> {
    try {
      const response = await this.request<User>('/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ token }),
        credentials: 'include', // Importante para CORS
      });
      return response;
    } catch (error) {
      console.error('apiService.verifyToken error:', error);
      throw error;
    }
  }

  // Clients
  async getClients(filters: ClientFilters = {}): Promise<ApiResponse<Client[]>> {
    const params = new URLSearchParams();
    
    if (filters.branchId) params.append('branchId', filters.branchId);
    if (filters.status) params.append('status', filters.status);
    if (filters.search) params.append('search', filters.search);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.limit) params.append('limit', filters.limit.toString());

    const endpoint = `/clients${params.toString() ? `?${params.toString()}` : ''}`;
    return this.requestWithAuth<Client[]>(endpoint);
  }

  async getClient(id: string): Promise<ApiResponse<Client>> {
    return this.requestWithAuth<Client>(`/clients/${id}`);
  }

  async createClient(data: ClientFormData): Promise<ApiResponse<Client>> {
    try {
      return await this.requestWithAuth<Client>('/clients', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch (err: any) {
      // Extraer mensaje del backend para errores de duplicado
      throw new Error(err.message || 'Error al crear cliente');
    }
  }

  async updateClient(id: string, data: Partial<ClientFormData>): Promise<ApiResponse<Client>> {
    return this.requestWithAuth<Client>(`/clients/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getClientPayments(id: string): Promise<ApiResponse<Payment[]>> {
    return this.requestWithAuth<Payment[]>(`/clients/${id}/payments`);
  }

  // Payments
  async createPayment(data: PaymentFormData): Promise<ApiResponse<Payment>> {
    return this.requestWithAuth<Payment>('/payments', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getReceipts(params: ReceiptFilters = {}): Promise<ApiResponse<{ receipts: Receipt[]; total: number }>> {
    const searchParams = new URLSearchParams();
    if (params.limit) searchParams.append('limit', params.limit.toString());
    if (params.offset) searchParams.append('offset', params.offset.toString());
    if (params.branchId) searchParams.append('branchId', params.branchId);
    if (params.method) searchParams.append('method', params.method);
    if (params.startDate) searchParams.append('startDate', params.startDate);
    if (params.endDate) searchParams.append('endDate', params.endDate);
    const endpoint = `/payments/receipts${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return this.requestWithAuth<{ receipts: Receipt[]; total: number }>(endpoint);
  }

  // Dashboard
  async getDashboard(params: { branchId?: string } = {}): Promise<ApiResponse<DashboardData>> {
    const searchParams = new URLSearchParams();
    if (params.branchId) searchParams.append('branchId', params.branchId);
    const endpoint = `/reports/dashboard${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return this.requestWithAuth<DashboardData>(endpoint);
  }

  async syncOfflinePayments(payments: any[]): Promise<ApiResponse<any>> {
    return this.requestWithAuth<any>('/payments/sync', {
      method: 'POST',
      body: JSON.stringify({ payments }),
    });
  }

  async getPaymentReport(filters: PaymentFilters): Promise<ApiResponse<any>> {
    const params = new URLSearchParams();
    
    if (filters.businessId) params.append('businessId', filters.businessId);
    if (filters.startDate) params.append('startDate', filters.startDate);
    if (filters.endDate) params.append('endDate', filters.endDate);
    if (filters.branchId) params.append('branchId', filters.branchId);
    if (filters.method) params.append('method', filters.method);

    const endpoint = `/payments/report${params.toString() ? `?${params.toString()}` : ''}`;
    return this.requestWithAuth<any>(endpoint);
  }

  // Businesses
  async getBusinesses(): Promise<ApiResponse<Business[]>> {
    return this.requestWithAuth<Business[]>('/businesses');
  }

  async createBusiness(data: { name: string }): Promise<ApiResponse<Business>> {
    return this.requestWithAuth<Business>('/businesses', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteBusiness(id: string): Promise<ApiResponse<{ id: string }>> {
    return this.requestWithAuth<{ id: string }>(`/businesses/${id}`, {
      method: 'DELETE',
    });
  }

  async updateBusiness(id: string, data: { name: string }): Promise<ApiResponse<{ id: string; name: string }>> {
    return this.requestWithAuth<{ id: string; name: string }>(`/businesses/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Branches
  async getBranches(businessId: string): Promise<ApiResponse<Branch[]>> {
    return this.requestWithAuth<Branch[]>(`/branches?businessId=${businessId}`);
  }

  async createBranch(data: BranchFormData): Promise<ApiResponse<Branch>> {
    return this.requestWithAuth<Branch>('/branches', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateBranch(id: string, data: Partial<BranchFormData>): Promise<ApiResponse<Branch>> {
    return this.requestWithAuth<Branch>(`/branches/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteBranch(id: string): Promise<ApiResponse<{ id: string }>> {
    return this.requestWithAuth<{ id: string }>(`/branches/${id}`, {
      method: 'DELETE',
    });
  }

  // Reports
  async getSolvencyReport(filters: ReportFilters): Promise<ApiResponse<SolvencyReport[]>> {
    const params = new URLSearchParams();
    
    if (filters.branchId) params.append('branchId', filters.branchId);
    if (filters.daysOverdue) params.append('daysOverdue', filters.daysOverdue.toString());

    const endpoint = `/reports/solvency${params.toString() ? `?${params.toString()}` : ''}`;
    return this.requestWithAuth<SolvencyReport[]>(endpoint);
  }

  async getIncomeDailyReport(startDate: string, endDate: string, branchId?: string): Promise<ApiResponse<{ totalPeriod: number; daily: IncomeDailyReport[] }>> {
    const params = new URLSearchParams();
    params.append('startDate', startDate);
    params.append('endDate', endDate);
    if (branchId) params.append('branchId', branchId);

    const endpoint = `/reports/income/daily?${params.toString()}`;
    return this.requestWithAuth<{ totalPeriod: number; daily: IncomeDailyReport[] }>(endpoint);
  }

  async getIncomeByMethodReport(startDate?: string, endDate?: string, branchId?: string): Promise<ApiResponse<IncomeByMethodReport>> {
    const params = new URLSearchParams();
    if (startDate) params.append('startDate', startDate);
    if (endDate) params.append('endDate', endDate);
    if (branchId) params.append('branchId', branchId);

    const endpoint = `/reports/income/by-method${params.toString() ? `?${params.toString()}` : ''}`;
    return this.requestWithAuth<IncomeByMethodReport>(endpoint);
  }

  // Membership Plans
  async getMembershipPlans(businessId: string): Promise<ApiResponse<MembershipPlan[]>> {
    return this.requestWithAuth<MembershipPlan[]>(`/membership-plans/${businessId}`);
  }

  async getPlans(params: { businessId?: string; isActive?: boolean }): Promise<ApiResponse<MembershipPlan[]>> {
    const searchParams = new URLSearchParams();
    if (params.businessId) searchParams.append('businessId', params.businessId);
    if (params.isActive !== undefined) searchParams.append('isActive', String(params.isActive));
    const endpoint = `/plans${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return this.requestWithAuth<MembershipPlan[]>(endpoint);
  }

  async getPlan(id: string): Promise<ApiResponse<MembershipPlan>> {
    return this.requestWithAuth<MembershipPlan>(`/plans/${id}`);
  }

  async createPlan(data: PlanFormData): Promise<ApiResponse<MembershipPlan>> {
    return this.requestWithAuth<MembershipPlan>('/plans', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updatePlan(id: string, data: Partial<PlanFormData>): Promise<ApiResponse<MembershipPlan>> {
    return this.requestWithAuth<MembershipPlan>(`/plans/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deletePlan(id: string): Promise<ApiResponse<{ id: string }>> {
    return this.requestWithAuth<{ id: string }>(`/plans/${id}`, {
      method: 'DELETE',
    });
  }

  // Payment Accounts
  async getPaymentAccounts(params: { businessId?: string; type?: string; isActive?: boolean }): Promise<ApiResponse<PaymentAccount[]>> {
    const searchParams = new URLSearchParams();
    if (params.businessId) searchParams.append('businessId', params.businessId);
    if (params.type) searchParams.append('type', params.type);
    if (params.isActive !== undefined) searchParams.append('isActive', String(params.isActive));
    const endpoint = `/payment-accounts${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return this.requestWithAuth<PaymentAccount[]>(endpoint);
  }

  async getPaymentAccount(id: string): Promise<ApiResponse<PaymentAccount>> {
    return this.requestWithAuth<PaymentAccount>(`/payment-accounts/${id}`);
  }

  async createPaymentAccount(data: PaymentAccountFormData): Promise<ApiResponse<PaymentAccount>> {
    return this.requestWithAuth<PaymentAccount>('/payment-accounts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updatePaymentAccount(id: string, data: Partial<PaymentAccountFormData>): Promise<ApiResponse<PaymentAccount>> {
    return this.requestWithAuth<PaymentAccount>(`/payment-accounts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deletePaymentAccount(id: string): Promise<ApiResponse<{ id: string }>> {
    return this.requestWithAuth<{ id: string }>(`/payment-accounts/${id}`, {
      method: 'DELETE',
    });
  }

  // Users
  async getUsers(params: { businessId?: string; isActive?: boolean } = {}): Promise<ApiResponse<User[]>> {
    const searchParams = new URLSearchParams();
    if (params.businessId) searchParams.append('businessId', params.businessId);
    if (params.isActive !== undefined) searchParams.append('isActive', String(params.isActive));
    const endpoint = `/users${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return this.requestWithAuth<User[]>(endpoint);
  }

  async getUser(id: string): Promise<ApiResponse<User>> {
    return this.requestWithAuth<User>(`/users/${id}`);
  }

  async createUser(data: UserFormData): Promise<ApiResponse<User>> {
    return this.requestWithAuth<User>('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(id: string, data: Partial<UserFormData>): Promise<ApiResponse<User>> {
    return this.requestWithAuth<User>(`/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteUser(id: string): Promise<ApiResponse<{ id: string; message: string }>> {
    return this.requestWithAuth<{ id: string; message: string }>(`/users/${id}`, {
      method: 'DELETE',
    });
  }

  // Invitations
  async createInvitation(data: { email: string; name?: string; role: UserRole; businessId?: string }): Promise<ApiResponse<{
    invitationId: string;
    token: string;
    email: string;
    role: string;
    name?: string;
    expiresAt: string;
    invitationLink: string;
  }>> {
    return this.requestWithAuth('/invitations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async validateInvitation(token: string): Promise<ApiResponse<{
    valid: boolean;
    email: string;
    role: string;
    name?: string;
    businessId?: string;
    branchId?: string;
    businessName?: string;
    invitedByName: string;
    requiresOnboarding: boolean;
  }>> {
    return this.request<{
    valid: boolean;
    email: string;
    role: string;
    name?: string;
    businessId?: string;
    branchId?: string;
    businessName?: string;
    invitedByName: string;
    requiresOnboarding: boolean;
  }>(`/invitations/validate/${token}`);
  }

  async acceptInvitation(token: string, uid: string): Promise<ApiResponse<{
    userId: string;
    email: string;
    role: string;
    name?: string;
    businessId?: string;
    branchId?: string;
  }>> {
    return this.requestWithAuth('/invitations/accept', {
      method: 'POST',
      body: JSON.stringify({ token, uid }),
    });
  }

  // Exchange Rate
  async getExchangeRate(): Promise<ApiResponse<{ rate: number; currency: string; source: string; cached: boolean }>> {
    return this.request<{ rate: number; currency: string; source: string; cached: boolean }>('/exchange-rate');
  }
}

export const apiService = new ApiService();
export default apiService;
