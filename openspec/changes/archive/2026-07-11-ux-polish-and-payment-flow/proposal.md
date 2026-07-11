# Proposal: UX Polish & Payment Flow

## Intent

Address 3 bugs blocking correct operation (dead exchange-rate endpoint, Dashboard showing zero overdue + wrong currency, Russian error message in ClientFormPage), fill UX gaps on 4 existing pages (plan names, receipts filters, expiry indicators, analytics), and deliver the missing standalone `/payments/new` page that the Dashboard links to (currently 404).

## Scope

### In Scope (6 deliverables)

1. **Bug fixes**: Register `exchange_rate` blueprint in `app.py`, fix Dashboard `overdueClients` count + currency, remove Russian word in `ClientFormPage`
2. **Plan names in ClientsPage**: Resolve plan IDs to display names using cached plan map
3. **Enhanced Dashboard**: 30-day income bar chart, client retention rate, top-spending clients widget
4. **Expiry notifications**: Badge/indicator on client list and detail for memberships expiring within 7 days
5. **ReceiptsPage filters**: Filter by payment method, date range, branch — server-side with Firestore composite queries
6. **Standalone payment page**: `/payments/new` route, extract shared `PaymentForm` from `ClientDetailPage` modal, fix Dashboard dead link

### Out of Scope

- SolvencyReportPage pagination
- BusinessCreatePage edit flow
- DataLoadPage completion
- UsersPage delete confirmation on desktop

## Capabilities

### New Capabilities

- `payment-flow`: Standalone payment registration page at `/payments/new` with shared `PaymentForm` component extracted from existing inline implementation
- `dashboard-analytics`: Income trend chart, client retention metric, and top-spending clients widget on DashboardPage
- `expiry-notifications`: Visual badge/indicator on ClientDetailPage and ClientsPage for memberships expiring within 7 days

### Modified Capabilities

None (no existing specs to modify; all behavior changes above are captured as new capabilities or inline bug fixes).

## Approach

**Backend**: One-line fix in `app.py` to register exchange_rate blueprint. Dashboard analytics: new aggregated endpoints in `routes/reports.py` using Firestore composite queries with date-range filtering. Receipts filters: extend existing `GET /api/receipts` with query params (`method`, `dateFrom`, `dateTo`, `branchId`). Expiry data: add `daysUntilExpiry` computed field to client response in `routes/clients.py`.

**Frontend**: Extract `PaymentForm` component from `ClientDetailPage` modal, reuse in new `PaymentsNewPage`. Resolve plan names via `usePlans` hook already in cache. Add `recharts` for Dashboard charts. Expiry badge: computed indicator on client row/card from membership data. ReceiptsPage: client-side filter controls dispatching to server with debounced params. Fix Dashboard `overdueClients`: correct the Firestore query filter. Clean `ClientFormPage` validation error message.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app.py` | Modified | Register exchange_rate blueprint |
| `backend/routes/exchange_rate.py` | No code change | Already implemented, was just unregistered |
| `backend/routes/reports.py` | Modified | New aggregated analytics endpoints |
| `backend/routes/payments.py` | Modified | Add query param filtering for receipts |
| `backend/routes/clients.py` | Modified | Add daysUntilExpiry computed field |
| `frontend/src/pages/DashboardPage.tsx` | Modified | Analytics widgets, overdueClients fix |
| `frontend/src/pages/ClientsPage.tsx` | Modified | Plan name resolution, expiry badges |
| `frontend/src/pages/ClientFormPage.tsx` | Modified | Remove Russian word |
| `frontend/src/pages/ClientDetailPage.tsx` | Modified | Extract PaymentForm, add expiry badge |
| `frontend/src/pages/ReceiptsPage.tsx` | Modified | Filter controls |
| `frontend/src/pages/PaymentsNewPage.tsx` | New | Standalone payment page |
| `frontend/src/components/PaymentForm.tsx` | New | Shared component extracted from modal |
| `frontend/src/App.tsx` | Modified | Add `/payments/new` route |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Firestore composite indexes needed for new receipt filter queries | Med | Check existing indexes; add index config if missing, test before deploy |
| `recharts` bundle size increases PWA load time | Low | Tree-shake imports; verify bundle size before merge |
| Plan name resolution race condition on slow connections | Low | Use already-cached `usePlans` hook; show skeleton while loading |
| Extracted PaymentForm breaks existing ClientDetailPage modal | Med | Keep both consumers; write integration test for modal path |

## Rollback Plan

- **Backend**: Revert `app.py` registration line. Rollback API changes one route file at a time via feature flags or direct revert commits.
- **Frontend**: Rollback route additions in `App.tsx`. Revert component extractions. Dashboard analytics can be feature-toggled via env var if needed.
- **DB**: No destructive migrations. New indexes are additive — safe to leave if rollback occurs.

## Dependencies

- `recharts` npm package (MIT license, ~165KB gzipped added to bundle)

## Success Criteria

- [ ] `/api/exchange-rate` returns 200 (not 404)
- [ ] Dashboard shows real overdue client count with correct business currency
- [ ] ClientFormPage has no Russian-language strings
- [ ] ClientsPage displays plan names, not raw IDs
- [ ] Dashboard renders income chart, retention %, top clients
- [ ] Clients expiring within 7 days show a visible badge
- [ ] ReceiptsPage filters by method, date range, and branch
- [ ] `/payments/new` loads and registers payments; Dashboard link works
- [ ] Existing payment flow via ClientDetailPage modal still works
