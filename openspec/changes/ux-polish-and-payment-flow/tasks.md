# Tasks: UX Polish & Payment Flow

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 700-780 (14 files: 3 create, 11 modify) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | PR | Lines | Base | Notes |
|------|------|-----|-------|------|-------|
| 1 | Backend foundation + 3 bug fixes | PR 1 | ~130 | main | exchange bp, dashboard endpoint, receipt filters, Russian word |
| 2 | Dashboard analytics, expiry badges, plan names, receipt filters | PR 2 | ~300 | main | Depends on PR 1 API |
| 3 | PaymentForm extraction + /payments/new page | PR 3 | ~330 | main | Depends on PR 2 types/api |

---

## Phase 1: Bug Fixes + Backend Foundation

- [x] 1.1 Register `exchange_bp` in `backend/routes/__init__.py`: add import and export
- [x] 1.2 Register `exchange_bp` in `backend/app.py`: import from routes, call `app.register_blueprint(exchange_bp)` in `create_app()`
- [x] 1.3 Add `GET /reports/dashboard` in `backend/routes/reports.py`: returns activeClients, todayIncome, overdueClients, expiringThisWeek, incomeChart (30-day daily sums), topSpendingClients (top 5 by count), retentionRate
- [x] 1.4 Extend `GET /receipts` in `backend/routes/payments.py`: parse optional `method`, `startDate`, `endDate` query params, append to Firestore filters
- [x] 1.5 Fix Russian word in `frontend/src/pages/ClientFormPage.tsx` line 145: replace `получил` → `pudo obtener`
- [x] 1.6 Add `DashboardData`, `TopSpendingClient`, `ReceiptFilters` types to `frontend/src/types/index.ts`

## Phase 2: Frontend Analytics + UI Improvements

- [ ] 2.1 Add `getDashboard(branchId?)` and extend `getReceipts()` with `method`/`startDate`/`endDate` params in `frontend/src/services/api.ts`
- [ ] 2.2 Rewrite `frontend/src/pages/DashboardPage.tsx`: call `getDashboard()` instead of client-side calculation, add Recharts `BarChart` for incomeChart, add topSpendingClients list widget, fix `formatCurrency` MXN→USD, fix overdueClients to use backend value
- [ ] 2.3 Resolve plan names in `frontend/src/pages/ClientsPage.tsx`: use `usePlans` hook to map `membershipPlanId` → display name in table
- [ ] 2.4 Add expiry badge in `frontend/src/pages/ClientsPage.tsx`: helper `getDaysRemaining(date)` → yellow "Expires in N days" / red "Expires today" badge when ≤7 days
- [ ] 2.5 Add expiry badge in `frontend/src/pages/ClientDetailPage.tsx`: same helper + badge in client header section
- [ ] 2.6 Add filter bar in `frontend/src/pages/ReceiptsPage.tsx`: method dropdown, date range, branch selector (super_admin), wired to debounced `getReceipts()`

## Phase 3: PaymentForm + /payments/new

- [ ] 3.1 Create `frontend/src/components/PaymentForm.tsx`: props (businessId, clientId?, initialPlanId?, initialAmount?, onSubmit, onCancel, isModal?); method-conditional fields (reference, destination account); amount validation with plan-price warning; submit gating
- [ ] 3.2 Replace inline modal in `frontend/src/pages/ClientDetailPage.tsx` with extracted `<PaymentForm>`, verify existing behavior unchanged
- [ ] 3.3 Create `frontend/src/pages/PaymentsNewPage.tsx`: debounced client search, selected-client summary card (name, plan, expiry, status), `<PaymentForm>` wired to `createPayment()`, success toast with receipt number
- [ ] 3.4 Add `/payments/new` route in `frontend/src/App.tsx`: import `PaymentsNewPage`, add `ProtectedRoute` (cashier/branch_admin/super_admin); fix Dashboard "Register Payment" link to `/payments/new`

## Phase 4: Verification

- [ ] 4.1 Verify `GET /api/exchange-rate` returns 200 (not 404)
- [ ] 4.2 Verify `GET /api/reports/dashboard` returns correct counts with seeded Firestore data
- [ ] 4.3 Verify `GET /api/payments/receipts?method=cash&startDate=...&endDate=...` filters correctly
- [ ] 4.4 Verify `/payments/new` end-to-end: search client → fill payment → submit → receipt in ReceiptsPage
- [ ] 4.5 Verify existing ClientDetailPage payment modal still works with extracted component
- [ ] 4.6 Verify Dashboard: chart renders, top-5 widget, retention %, correct currency, correct overdue count
