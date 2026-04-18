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
  MembershipPlan,
  SolvencyReport,
  IncomeDailyReport,
  IncomeByMethodReport,
  ReportFilters
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
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...this.defaultHeaders,
          ...options.headers,
        },
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
    return this.requestWithAuth<Client>('/clients', {
      method: 'POST',
      body: JSON.stringify(data),
    });
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

  // Branches
  async getBranches(businessId: string): Promise<ApiResponse<Branch[]>> {
    return this.requestWithAuth<Branch[]>(`/branches/${businessId}`);
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

  // Businesses
  async getBusinesses(): Promise<ApiResponse<any[]>> {
    return this.requestWithAuth<any[]>('/businesses');
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
}

export const apiService = new ApiService();
export default apiService;
