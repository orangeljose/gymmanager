// User and Authentication Types
export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  businessId: string;
  branchId?: string | null;
  isActive: boolean;
  permissions: string[];
  createdAt: string;
}

export type UserRole = 'super_admin' | 'branch_admin' | 'cashier' | 'trainer';

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

// Business Types
export interface Business {
  id: string;
  name: string;
  rubro: string;
  logo?: string | null;
  ownerId: string;
  createdAt: string;
}

export interface Branch {
  id: string;
  name: string;
  address: string;
  phone: string;
  businessId: string;
  managerId?: string | null;
  isActive: boolean;
  createdAt: string;
}

// Membership Types
export interface MembershipPlan {
  id: string;
  name: string;
  price: number; // in cents
  durationDays: number;
  description?: string;
  businessId: string;
  isActive: boolean;
  benefits?: string[];
  createdAt: string;
}

// Client Types
export interface Client {
  id: string;
  name: string;
  email: string;
  phone: string;
  documentId?: string | null;
  branchId: string;
  businessId: string;
  membershipPlanId: string;
  membershipStart: string;
  membershipEnd: string;
  isActive: boolean;
  status: ClientStatus;
  registeredBy: string;
  notes?: string | null;
  createdAt: string;
}

export type ClientStatus = 'active' | 'expired' | 'suspended';

// Payment Types
export interface Payment {
  id: string;
  clientId: string;
  clientName: string;
  amount: number; // in cents
  method: PaymentMethod;
  methodDetails?: PaymentMethodDetails;
  membershipPlanId: string;
  monthsPaid: number;
  startDate: string;
  endDate: string;
  branchId: string;
  businessId: string;
  registeredBy: string;
  registeredByName: string;
  receiptNumber: string;
  syncedAt?: string | null;
  createdAt: string;
}

export type PaymentMethod = 'cash' | 'card' | 'transfer' | 'other';

export interface PaymentMethodDetails {
  cash?: {
    cashierName?: string;
    receivedAmount?: number;
    change?: number;
  };
  card?: {
    cardLast4?: string;
    cardBrand?: string;
    transactionId?: string;
    authorizationCode?: string;
  };
  transfer?: {
    reference?: string;
    bank?: string;
    accountNumber?: string;
  };
  other?: {
    description?: string;
    reference?: string;
  };
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: {
    code: number;
    message: string;
  };
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
    pages?: number;
  };
}

export interface ApiError {
  success: false;
  error: {
    code: number;
    message: string;
  };
}

// Report Types
export interface SolvencyReport {
  id: string;
  name: string;
  phone: string;
  membershipPlanId: string;
  membershipEnd: string;
  daysOverdue: number;
  lastPaymentDate?: string;
  lastPaymentAmount?: number;
}

export interface IncomeDailyReport {
  date: string;
  amount: number;
  paymentsCount: number;
}

export interface IncomeByMethodReport {
  [method: string]: {
    amount: number;
    percentage: number;
    count: number;
  };
}

// Form Types
export interface ClientFormData {
  businessId?: string;
  name: string;
  email: string;
  phone: string;
  documentId?: string;
  branchId: string;
  membershipPlanId: string;
  notes?: string;
}

export interface PaymentFormData {
  clientId: string;
  amount: number;
  method: PaymentMethod;
  membershipPlanId: string;
  branchId: string;
  methodDetails?: PaymentMethodDetails;
}

export interface BranchFormData {
  name: string;
  address: string;
  phone: string;
  businessId: string;
}

export interface UserFormData {
  email: string;
  name: string;
  role: UserRole;
  businessId: string;
  branchId?: string;
}

// Filter and Search Types
export interface ClientFilters {
  businessId?: string;
  branchId?: string;
  status?: ClientStatus;
  search?: string;
  page?: number;
  limit?: number;
}

export interface PaymentFilters {
  businessId?: string;
  clientId?: string;
  branchId?: string;
  method?: PaymentMethod;
  startDate?: string;
  endDate?: string;
  page?: number;
  limit?: number;
}

export interface ReportFilters {
  branchId?: string;
  startDate?: string;
  endDate?: string;
  daysOverdue?: number;
}

// Offline Storage Types
export interface OfflineClient extends Client {
  lastViewed: string;
}

export interface OfflinePayment extends Omit<Payment, 'id' | 'syncedAt' | 'createdAt'> {
  localId: string;
  registeredAt: string;
  synced: boolean;
}

export interface PendingSync {
  id: string;
  type: 'payment' | 'client' | 'update';
  data: any;
  timestamp: string;
  retryCount: number;
}

// UI State Types
export interface LoadingState {
  [key: string]: boolean;
}

export interface ErrorState {
  [key: string]: string | null;
}

// Navigation Types
export interface NavItem {
  label: string;
  href: string;
  icon: string;
  roles?: UserRole[];
  children?: NavItem[];
}

// Toast Types
export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

// Chart Data Types
export interface ChartDataPoint {
  name: string;
  value: number;
  date?: string;
}

export interface DashboardMetrics {
  activeClients: number;
  todayIncome: number;
  overdueClients: number;
  expiringThisWeek: number;
}

// PWA Types
export interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  prompt(): Promise<void>;
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
}

// Environment Types
export interface EnvConfig {
  apiUrl: string;
  firebaseApiKey: string;
  firebaseAuthDomain: string;
  firebaseProjectId: string;
  firebaseStorageBucket: string;
  firebaseMessagingSenderId: string;
  firebaseAppId: string;
  appName: string;
  environment: string;
  enableOffline: boolean;
}
