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

export type UserRole = 'super_admin' | 'admin' | 'branch_admin' | 'cashier' | 'trainer';

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  selectedBusinessId: string | null;
  businesses: Business[];
}

// Business Types
export interface Business {
  id: string;
  name: string;
  logo?: string | null;
  ownerId: string;
  createdAt: string | { seconds: number };
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
  price: number;
  durationDays: number;
  description?: string;
  businessId: string;
  isActive: boolean;
  benefits?: string[];
  createdAt: string;
  pricesByMethod?: Record<string, number>;
}

export type PaymentAccountType = 'zelle' | 'pago_movil' | 'bank' | 'binance';

export interface PaymentAccount {
  id: string;
  type: PaymentAccountType;
  identifier: string;
  label: string;
  description?: string;
  businessId: string;
  isActive: boolean;
  createdAt: string;
  bankName?: string;  // Para pago_movil
  cedula?: string;     // Para pago_movil
}

export interface PaymentAccountFormData {
  type: PaymentAccountType;
  identifier: string;
  label?: string;
  description?: string;
  businessId?: string; // Solo para create, no se envía en update
  bankName?: string;   // Para pago_movil
  cedula?: string;      // Para pago_movil
}

export interface PlanFormData {
  name: string;
  price: number;
  durationDays: number;
  description?: string;
  benefits: string[];
  businessId?: string; // Solo para create, no se envía en update
  pricesByMethod?: Record<string, number | undefined>;
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
  isDeleted?: boolean; // Soft delete flag (backend)
}

export type ClientStatus = 'active' | 'expired';

// Payment Types
export interface Payment {
  id: string;
  clientId: string;
  clientName: string;
  amount: number; // in cents
  method: PaymentMethod;
  reference?: string | null;
  paymentAccountId?: string | null;
  membershipPlanId: string;
  planName?: string;
  planPrice?: number;
  startDate: string;
  endDate: string;
  branchId: string;
  businessId: string;
  registeredBy: string;
  registeredByName: string;
  receiptNumber: string;
  syncedAt?: string | null;
  createdAt: string;
  paymentDate?: string; // Fecha real del pago (si diffiere de createdAt)
  isDeleted?: boolean; // Soft delete flag (backend)
}

export type PaymentMethod = 'cash' | 'card' | 'transfer' | 'zelle' | 'pago_movil' | 'binance' | 'other';

export interface Receipt {
  id: string;
  receiptNumber: string;
  createdAt: string;
  clientName: string;
  planName: string;
  amount: number;
  method: PaymentMethod;
  reference?: string | null;
  paymentAccountId?: string | null;
  registeredByName: string;
}

// Attendance Types
export type AttendanceMethod = 'manual' | 'qr' | 'biometric';

export interface AttendanceRecord {
  id: string;
  businessId: string;
  branchId: string | null;
  clientId: string;
  clientName: string;
  method: AttendanceMethod;
  date: string;        // YYYY-MM-DD (zona horaria del negocio)
  checkInAt: string;   // ISO UTC
  registeredBy: string;
  registeredByName: string;
  createdAt: string;
  alreadyCheckedIn?: boolean;
}

export interface AttendanceSeriesPoint {
  date: string;
  count: number;
}

export interface AttendanceTopAttendee {
  clientId: string;
  clientName: string;
  count: number;
}

export interface AttendanceStats {
  today: number;
  week: number;
  month: number;
  series7: AttendanceSeriesPoint[];
  series30: AttendanceSeriesPoint[];
  last7Days?: AttendanceSeriesPoint[];
  topAttendees: AttendanceTopAttendee[];
}

export interface AttendanceReportDailyPoint {
  date: string;
  count: number;
}

export interface AttendanceReport {
  total: number;
  avgDaily: number;
  peakDay: { date: string; count: number } | null;
  daily: AttendanceReportDailyPoint[];
  topAttendees: AttendanceTopAttendee[];
}

export interface AttendanceSummary {
  total: number;
  byMethod: Record<string, number>;
}

export interface ClientAttendanceStats {
  total: number;
  thisMonth: number;
  lastVisit: string | null;
}

export interface AttendanceFilters {
  date?: string;
  businessId?: string;
  branchId?: string;
  clientId?: string;
  page?: number;
  limit?: number;
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
    accounts?: Record<string, { amount: number; count: number }>;
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
  paymentDate?: string;
  paymentAccountId?: string;
  methodDetails?: {
    cardLast4?: string;
    transactionId?: string;
    reference?: string;
    bank?: string;
    accountNumber?: string;
    senderEmail?: string;
    phoneSender?: string;
    paymentCode?: string;
    destinationAccountId?: string;
    cashierName?: string;
    receivedAmount?: number;
    change?: number;
    description?: string;
  };
}

export interface PaymentFormDataCreate {
  clientId: string;
  amount: number;
  method: PaymentMethod;
  membershipPlanId: string;
  branchId: string;
  methodDetails?: Record<string, any>;
  paymentDate?: string;
  paymentAccountId?: string;
}

export interface BranchFormData {
  name: string;
  address: string;
  phone: string;
  businessId?: string; // Solo para create, no se envía en update
}

export interface UserFormData {
  email: string;
  name: string;
  role: UserRole;
  branchId?: string;
  businessId?: string; // Solo para create, no se envía en update
}

// Invitation Types
export interface Invitation {
  id: string;
  token: string;
  email: string;
  name?: string;
  role: UserRole;
  businessId?: string;
  branchId?: string;
  invitedBy: string;
  invitedByName: string;
  status: 'pending' | 'accepted' | 'expired';
  expiresAt: string;
  createdAt: string;
}

export interface InvitationFormData {
  email: string;
  name?: string;
  role: UserRole;
}

// Filter and Search Types
export interface ClientFilters {
  businessId?: string;
  branchId?: string;
  status?: ClientStatus;
  expiringSoon?: boolean; // Tiene precedencia sobre status cuando es true
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

// Dashboard API Types
export interface DashboardData {
  activeClients: number;
  todayIncome: number;
  overdueClients: number;
  expiringThisWeek: number;
  incomeChart: IncomeChartPoint[];
  topPayingClients: TopPayingClient[];
  retentionRate: number;
  recentPayments: RecentPayment[];
  recentClients: RecentClient[];
}

export interface RecentClient {
  id: string;
  name: string;
  email: string;
  membershipEnd: string;
  status: string;
}

export interface RecentPayment {
  id: string;
  clientId: string;
  clientName: string;
  amount: number;
  method: string;
  createdAt: string;
}

export interface IncomeChartPoint {
  date: string;
  amount: number;
}

export interface TopPayingClient {
  clientId: string;
  clientName: string;
  paymentCount: number;
}

export interface ReceiptFilters {
  method?: PaymentMethod;
  startDate?: string;
  endDate?: string;
  branchId?: string;
  limit?: number;
  offset?: number;
}

// Machine / Equipment Types
export type MachineStatus = 'operational' | 'maintenance' | 'out_of_service';
export type MachineKind = 'machine' | 'item';
export type MachineCategory = 'cardio' | 'strength' | 'functional' | 'free_weights' | 'accessory' | 'other';
export type MachineMaintenanceType = 'preventive' | 'repair';
export type MachineMaintenanceStatus = 'scheduled' | 'in_progress' | 'completed';
export type MachineResolvedStatus = 'operational' | 'out_of_service';

export interface Machine {
  id: string;
  kind?: MachineKind;          // ausente en docs legacy ⇒ 'machine'
  name: string;
  brand?: string | null;
  model?: string | null;
  category: MachineCategory;
  purchaseDate?: string | null;
  warrantyUntil?: string | null;
  businessId: string;
  branchId?: string | null;
  status: MachineStatus;
  nextMaintenanceDate?: string | null;
  quantity?: number;           // ítems, default 1
  weightKg?: number | null;    // ítems, opcional
  isActive: boolean;
  registeredBy?: string;
  registeredByName?: string;
  deletedBy?: string;
  deletedAt?: string;
  createdAt: string;
}

export interface MachineMaintenance {
  id: string;
  machineId: string;
  machineName: string;
  type: MachineMaintenanceType;
  description?: string | null;
  date: string;
  costCents?: number | null;
  technician?: string | null;
  status: MachineMaintenanceStatus;
  resolvedStatus?: MachineResolvedStatus | null;
  businessId: string;
  branchId?: string | null;
  registeredBy: string;
  registeredByName: string;
  createdAt: string;
}

export interface MachineFormData {
  kind?: MachineKind;
  name: string;
  brand?: string;
  model?: string;
  category: MachineCategory;
  purchaseDate?: string;
  warrantyUntil?: string;
  businessId?: string;
  branchId?: string | null;
  status?: MachineStatus;
  nextMaintenanceDate?: string;
  quantity?: number;
  weightKg?: number | null;
}

export interface MachineMaintenanceFormData {
  type: MachineMaintenanceType;
  status: MachineMaintenanceStatus;
  date: string;
  description?: string;
  costCents?: number;
  technician?: string;
  resolvedStatus?: MachineResolvedStatus;
  nextMaintenanceDate?: string;
}

export interface MachinesSummary {
  total: number;
  byStatus: Record<MachineStatus, number>;
  upcomingMaintenance: Machine[];
  recentRepairs: MachineMaintenance[];
  items: { itemTypes: number; totalUnits: number };
}

export interface MachineFilters {
  businessId?: string;
  branchId?: string;
  kind?: MachineKind | '';
  category?: MachineCategory | '';
  status?: MachineStatus | '';
  search?: string;
  page?: number;
  limit?: number;
}

// Expense Types (Egresos)
export type ExpenseCategory = 'payroll' | 'supplies' | 'services' | 'rent' | 'maintenance' | 'other';

export interface Expense {
  id: string;
  category: ExpenseCategory;
  amountCents: number;          // centavos; el UI muestra dólares
  description?: string | null;
  date: string;                 // YYYY-MM-DD
  method: PaymentMethod;
  paymentAccountId?: string | null;
  businessId: string;
  branchId?: string | null;
  registeredBy: string;
  registeredByName: string;
  createdAt: string;
  isDeleted?: boolean;
  deletedBy?: string;
  deletedAt?: string;
}

export interface ExpenseSummary {
  today: number;                // centavos
  week: number;                 // centavos
  month: number;                // centavos
  byCategory: Record<ExpenseCategory, number>;  // centavos
}

export interface ServiceReportDailyPoint {
  date: string;
  totalCents: number;
}

export interface ServiceReport {
  totalCents: number;                              // centavos
  count: number;                                   // número de egresos en el período
  byCategory: Record<ExpenseCategory, number>;     // categoría → centavos
  daily: ServiceReportDailyPoint[];
}

export interface ExpenseFilters {
  businessId?: string;
  branchId?: string;
  category?: ExpenseCategory | '';
  startDate?: string;
  endDate?: string;
  search?: string;
  page?: number;
  limit?: number;
}

export interface ExpenseFormData {
  category: ExpenseCategory;
  amountCents: number;
  description?: string;
  date: string;
  method: PaymentMethod;
  paymentAccountId?: string | null;
  businessId?: string;          // Solo para create
  branchId?: string | null;
}

// Product / Inventory Types (Fase 2 — Productos, Stock y Movimientos)
export type ProductCategory = 'supplement' | 'drink' | 'apparel' | 'accessory' | 'other';
export type MovementType = 'sale' | 'purchase';

export interface Product {
  id: string;
  name: string;
  category: ProductCategory;
  costPriceCents: number;       // centavos; el UI muestra dólares
  salePriceCents: number;       // centavos
  stockQty: number;
  lowStockThreshold: number;
  businessId: string;
  branchId?: string | null;
  isActive: boolean;
  registeredBy: string;
  registeredByName?: string;
  createdAt: string;
  deletedBy?: string;
  deletedAt?: string;
}

export interface ProductMovement {
  id: string;
  productId: string;
  type: MovementType;
  qty: number;
  unitPriceCents: number;
  totalCents: number;
  date: string;                 // YYYY-MM-DD
  method: PaymentMethod;
  paymentAccountId?: string | null;
  businessId: string;
  branchId?: string | null;
  registeredBy: string;
  registeredByName: string;
  createdAt: string;
  note?: string | null;
}

export interface ProductSummary {
  totalProducts: number;
  totalStockValue: number;      // centavos
  lowStockCount: number;
  outOfStockCount: number;
}

export interface ProductFilters {
  businessId?: string;
  branchId?: string;
  category?: ProductCategory | '';
  lowStock?: boolean;
  search?: string;
  page?: number;
  limit?: number;
}

export interface ProductFormData {
  name: string;
  category: ProductCategory;
  costPriceCents: number;
  salePriceCents: number;
  stockQty?: number;            // Solo para create (stock inicial)
  lowStockThreshold?: number;
  businessId?: string;          // Solo para create
  branchId?: string | null;
}

export interface ProductMovementFormData {
  type: MovementType;
  qty: number;
  unitPriceCents?: number;      // venta: default salePriceCents; compra: requerido
  updateCostPrice?: boolean;    // compra: actualizar costPriceCents
  date?: string;
  note?: string;
  method?: PaymentMethod;
  paymentAccountId?: string | null;
}

export interface ProductReportDailyPoint {
  date: string;
  salesCents: number;
  purchasesCents: number;
}

export interface ProductReport {
  sales: { count: number; totalCents: number };
  purchases: { count: number; totalCents: number };
  net: number;                  // sales.totalCents - purchases.totalCents
  daily: ProductReportDailyPoint[];
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
