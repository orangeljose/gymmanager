# Tasks: UX Polish & Payment Flow

## Review Workload Forecast
- **Total estimated changes**: ~500 lines across 3 PRs
- **Chained PRs recommended**: Yes
- **Chain strategy**: stacked-to-main
- **400-line budget risk**: Medium (split into 3 slices)
- **Decision needed before apply**: Yes (resolved → chained PRs)

---

## Phase 1: Backend Foundation (PR 1 — ✅ DONE on `ux-polish-payment-flow-pt1`)

- [x] 1.1 Register exchange_rate blueprint in app.py
- [x] 1.2 Fix Russian word in ClientFormPage (получил → pudo obtener)
- [x] 1.3 Fix Dashboard currency display (MXN → USD)
- [x] 1.4 Fix Dashboard overdueClients count
- [x] 1.5 Create GET /reports/dashboard endpoint
- [x] 1.6 Extend GET /receipts query params (method, startDate, endDate, branchId)
- [x] 1.7 Add DashboardData, TopSpendingClient, ReceiptFilters types

---

## Phase 2: Dashboard Analytics + UX Polish (PR 2 — ✅ DONE on `ux-polish-payment-flow-pt2`)

- [x] 2.1 Add getDashboard() to api service
- [x] 2.2 Migrate DashboardPage to use /reports/dashboard endpoint
- [x] 2.3 Add 30-day income BarChart (Recharts)
- [x] 2.4 Add top 5 spending clients widget
- [x] 2.5 Add retention rate metric card
- [x] 2.6 Add expiringThisWeek count badge on Dashboard metrics
- [x] 2.7 Resolve plan names in ClientsPage via usePlans hook
- [x] 2.8 Add expiry badges and row highlighting on ClientsPage
- [x] 2.9 Add filter bar to ReceiptsPage (method, date range, branch)
- [x] 2.10 Update getReceipts() signature to accept full ReceiptFilters

---

## Phase 3: Payment Form + New Page (PR 3 — 📍 CURRENT on `ux-polish-payment-flow-pt3`)

- [x] 3.1 Extract PaymentForm component from ClientDetailPage modal
- [x] 3.2 Create PaymentsNewPage at /payments/new
- [x] 3.3 Add client search + summary step in PaymentsNewPage
- [x] 3.4 Wire PaymentForm to createPayment API
- [x] 3.5 Add /payments/new route to App.tsx (cashier+)
- [x] 3.6 Update ClientDetailPage to use extracted PaymentForm
- [x] 3.7 Add expiry badge to ClientDetailPage

## Commits (PR 3)
1. `feat(payments): extract PaymentForm component and add expiry badge to ClientDetailPage`
2. `feat(payments): add PaymentsNewPage with client search and register route`
