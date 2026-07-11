# Design: UX Polish & Payment Flow

## Technical Approach

Six deliverables implemented as three work units: **(1)** bug fixes (exchange_rate registration, overdueClients query, Russian word removal, Dashboard currency to USD), **(2)** Dashboard analytics + expiry badges + plan names on ClientsPage + receipts filters, **(3)** shared `PaymentForm` component extraction + new `/payments/new` route. Backend changes are additive (new endpoint, extended query params). Frontend follows existing patterns: Zustand-style hooks, Tailwind utility classes, debounced API calls.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| Dashboard data fetching | A) New `GET /reports/dashboard` endpoint vs B) Call 3 existing endpoints | A = 1 round-trip, clean; B = no new backend code, 3 parallel calls | **A**: Single aggregated endpoint reduces waterfall and simplifies loading states |
| PaymentForm extraction scope | A) Shared component for all 3 consumers vs B) Shared for 2, keep wizard inline | A = DRY but complex props; B = simpler props, wizard flow is distinct | **B**: ClientFormPage wizard has unique flow (create client → then payment), different submission logic. Extract for ClientDetailPage modal + PaymentsNewPage only |
| Expiry badge data source | A) Client-side compute from membershipEnd vs B) New API field `daysUntilExpiry` | A = zero backend change, real-time; B = single source of truth, portable | **A**: Already computed in 3 places (DashboardPage, ClientsPage, ClientDetailPage). Add reusable helper `getDaysRemaining(date)` → badge when ≤7 days |
| Receipts filter backend | A) Extend `GET /receipts` params vs B) Use existing `GET /report` | A = adds method/dateFilter to existing endpoint; B = report endpoint has different response shape | **A**: Extend receipts endpoint — same response shape, just add `method`, `startDate`, `endDate` query params |
| Dashboard currency | A) Hardcode USD (matches rest of app) vs B) Add currency field to Business model | A = immediate fix, consistent; B = data model change | **A**: Switch MXN → USD. Rest of app already uses USD. Adding business currency settings is out of scope |

## Data Flow

```
DashboardPage
  └─ GET /api/reports/dashboard  ← NEW endpoint
       ├─ activeClients: count from clients collection
       ├─ todayIncome: sum from payments WHERE createdAt=today
       ├─ overdueClients: count from clients WHERE membershipEnd < now AND isActive=true
       ├─ expiringThisWeek: count from clients WHERE membershipEnd in [today, today+7]
       ├─ incomeChart: last 30 days grouped by date (reuses income/daily logic)
        ├─ topPayingClients: top 5 by payment count in last 30 days
       └─ retentionRate: activeClients / totalClients * 100

PaymentForm (shared component)
  ├─ Props: businessId, clientId?, initialData?, onSubmit(payload), onCancel
  ├─ Internal: useState for form fields, method-toggled conditional sections
  ├─ Data: usePlans(businessId) for plan selector + amount auto-fill
  └─ Data: usePaymentAccounts(businessId) for zelle/pago_movil destination accounts

PaymentsNewPage (new)
  ├─ Step 1: Search clients → debounced apiService.getClients({search})
  ├─ Step 2: Show selected client summary card
  └─ Step 3: <PaymentForm> → apiService.createPayment(payload)

ReceiptsPage (modified)
  └─ GET /api/payments/receipts?limit=&offset=&branchId=&method=&startDate=&endDate=
       └─ Backend: add method/date filters to existing query_firestore call
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/routes/__init__.py` | Modify | Add `exchange_bp` import and export |
| `backend/app.py` | Modify | Import and register `exchange_bp` |
| `backend/routes/reports.py` | Modify | Add `GET /reports/dashboard` endpoint |
| `backend/routes/payments.py` | Modify | Add `method`, `startDate`, `endDate` params to `GET /receipts` |
| `frontend/src/components/PaymentForm.tsx` | Create | Shared payment form with method-conditional fields |
| `frontend/src/pages/PaymentsNewPage.tsx` | Create | Client search → summary → PaymentForm flow |
| `frontend/src/App.tsx` | Modify | Add `/payments/new` route (cashier+) |
| `frontend/src/pages/DashboardPage.tsx` | Modify | Call new endpoint, add chart + topSpenders widgets, fix currency (MXN→USD), fix overdueClients query |
| `frontend/src/pages/ClientsPage.tsx` | Modify | Resolve plan names via usePlans, add expiry badge on rows |
| `frontend/src/pages/ClientDetailPage.tsx` | Modify | Use extracted PaymentForm in modal, add expiry badge |
| `frontend/src/pages/ClientFormPage.tsx` | Modify | Fix Russian word (line 145: `получил` → `pudo obtener`) |
| `frontend/src/pages/ReceiptsPage.tsx` | Modify | Add filter bar (method, date range, branch) |
| `frontend/src/types/index.ts` | Modify | Add `DashboardData` type, extend `ReceiptFilters` |
| `frontend/src/services/api.ts` | Modify | Add `getDashboard()` and extend `getReceipts()` params |

## Interfaces / Contracts

**New endpoint**: `GET /api/reports/dashboard`
Query: `?branchId=string` (optional, super_admin only)
Response:
```json
{
  "success": true,
  "data": {
    "activeClients": 42,
    "todayIncome": 175000,
    "overdueClients": 5,
    "expiringThisWeek": 8,
    "incomeChart": [{"date": "2026-07-01", "amount": 35000}, ...],
    "topPayingClients": [{"clientId": "x", "clientName": "Juan", "paymentCount": 5}, ...],
    "retentionRate": 85.5
  }
}
```

**PaymentForm component props**:
```typescript
interface PaymentFormProps {
  businessId: string;
  clientId: string;          // Required — ID of the client being charged
  clientName: string;        // Display name of the client
  currentPlanId: string;     // Pre-selected plan ID (from client's current membership)
  branchId: string;          // Branch where payment is registered
  initialAmount?: number;    // Pre-filled amount in cents (from plan price)
  onSuccess: (receiptNumber?: string) => void;  // Called with receipt number on success
  onCancel: () => void;
  isModal?: boolean;         // Renders with modal chrome vs standalone card
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (backend) | `GET /reports/dashboard` returns correct counts | Flask test client with seeded Firestore data |
| Unit (frontend) | `PaymentForm` renders method-specific fields | React Testing Library, verify conditional fields toggle correctly |
| Integration | Dashboard data flow end-to-end | Seed Firestore, call endpoint, verify response shape and values |
| Manual | `/payments/new` full flow | Search client, fill payment, submit — verify receipt appears in ReceiptsPage |

## Open Questions

- [x] Firestore composite indexes for receipt filters: check existing indexes before adding new ones
- [ ] Should `Business` model get a `currency` field? (Out of scope — using USD for now is consistent with rest of app)
