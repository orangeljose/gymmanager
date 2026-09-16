# Tasks: Optimize Firestore Quotas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~380–520 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 backend → PR 2 frontend |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend quota fixes + tests | PR 1 | base: main (stacked) or feature branch; indexes required pre-deploy |
| 2 | Frontend single-fetch + recentClients | PR 2 | depends on PR 1 (recentClients contract) |

## Phase 1: Backend Foundation

- [x] 1.1 `backend/services/firebase_service.py`: add `count_firestore(collection, filters) -> int` (Firestore count aggregation); RAISES on failure/ceiling, never fakes 0

## Phase 2: Backend Core

- [x] 2.1 `backend/services/payment_service.py` `generate_receipt_number` (L20): replace scan with `count_firestore(payments, businessId==)` + 1 → `P-YYYYMMDD-XXX`; on error/ceiling fallback `P-YYYYMMDD-HHMMSSfff` (never `-001`)
- [x] 2.2 `backend/routes/reports.py` `get_daily_income_report` (L217): Firestore query with `businessId==`, `createdAt>=start`, `createdAt<=end`, `branchId==` when effective (super_admin: businessId from request param); keep Python isDeleted + deleted-client + date filter
- [x] 2.3 `backend/routes/reports.py` `get_income_by_method_report` (L409): same filters as 2.2
- [x] 2.4 `backend/routes/reports.py` `get_dashboard` (L589): payments query adds `createdAt >= now-30d`; compute `recentClients` (top 5 by createdAt DESC from already-fetched clients, deleted excluded) into response — zero extra reads

## Phase 3: Frontend

- [ ] 3.1 `frontend/src/types/index.ts`: add `RecentClient` + `DashboardData.recentClients`
- [ ] 3.2 `frontend/src/pages/DashboardPage.tsx`: drop `getClients({limit:100})`; render "Clientes Recientes" from payload `recentClients` incl. empty state
- [ ] 3.3 `frontend/src/hooks/useClients.ts`: remove mount effect (shared by 3 pages; ClientForm/Detail never read `clients`)
- [ ] 3.4 `frontend/src/pages/ClientsPage.tsx`: page owns initial + businessId-change fetch (`useEffect` on `effectiveBusinessId`); debounce effect gets first-render `useRef` guard + `page: 1`; status/branch/Limpiar handlers state-only; page-change/delete keep explicit `fetchClients`

## Phase 4: Tests (backend)

- [x] 4.1 Create `backend/tests/unit/test_receipt_number.py`: seq = count+1; timestamp fallback on error/ceiling; count query has NO isDeleted filter (spec: Quota-efficient, Gaps, Aggregation failure)
- [x] 4.2 Create `backend/tests/unit/test_reports_income.py`: query args (biz/branch/createdAt bounds); super_admin businessId from param; Python isDeleted + deleted-client exclusion (spec: Report reads, Branch filter, Deleted payments)
- [x] 4.3 Extend `backend/tests/unit/test_dashboard.py`: recentClients ≤5, DESC order, deleted excluded, empty array; payments query called with `createdAt>=` (existing reset-singleton pattern)

## Phase 5: Manual — Firestore Composite Indexes (BEFORE deploy)

- [ ] 5.1 [MANUAL — user, Firebase console] Create `payments` index: `businessId ASC, createdAt ASC`
- [ ] 5.2 [MANUAL — user, Firebase console] Create `payments` index: `businessId ASC, branchId ASC, createdAt ASC`
- [ ] 5.3 Verify: full backend test suite passes; browser network tab — ClientsPage 1 GET /clients per mount/filter; dashboard makes no /clients call