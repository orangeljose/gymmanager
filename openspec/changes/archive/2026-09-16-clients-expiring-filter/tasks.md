# Tasks: Clients Expiring Filter & Solvency Removal

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~750-850 (≈530 del, ≈250 add) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → 2 → 3 → 4 (stacked) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

NOTE: Spec scenario "Rejected parameter values" (client-management) requires 400 on `expiringSoon`+`status` and invalid values; design D1 chose precedence-over-status (no 400). Tasks follow D1 — reconcile spec before verify.

### Suggested Work Units

| Unit | Goal | PR |
|------|------|-----|
| 1 | Backend solvency removal (reports.py, tests, README) | PR 1 |
| 2 | Frontend solvency removal (page, card, api, types) | PR 2 |
| 3 | Backend expiringSoon + status tightening + tests | PR 3 |
| 4 | Frontend dropdown + api param + types | PR 4 |

## Phase 1: Backend expiringSoon

- [x] 1.1 `backend/routes/clients.py` — add `timedelta` to datetime import (L5); parse `expiringSoon` (`in ('true','1')`, else 400); when active, skip `status` block, append Firestore filters `membershipEnd >= now` and `<= now+7d` (`datetime.now(timezone.utc)`); keep Python `isDeleted` exclusion, sort, pagination (get_clients ~L85-96)
- [x] 1.2 `backend/routes/clients.py` — `valid_statuses` → `['active','expired']` (L87); update docstring L25 (add expiringSoon, drop suspended)
- [x] 1.3 `backend/models/client.py` — `valid_statuses` → `['active','expired']` (L85)

## Phase 2: Frontend expiringSoon

- [x] 2.1 `frontend/src/types/index.ts` — `ClientStatus` → `'active'|'expired'` (L113); add `expiringSoon?: boolean` to `ClientFilters` (L292)
- [x] 2.2 `frontend/src/services/api.ts` — append `expiringSoon=true` when `filters.expiringSoon` (getClients L131-143)
- [x] 2.3 `frontend/src/pages/ClientsPage.tsx` — replace `suspended` option with `<option value="expiring">Próximos 7 días</option>` (L169); widen `statusFilter` to `ClientStatus | 'expiring' | ''` (L18); add `buildClientFilters(page?)` mapping `'expiring'`→`{expiringSoon:true}`; use it in debounced effect (L60), page change (L71), delete-refresh (L112). Keep 'Suspendido' fallback labels (L80 etc.)

## Phase 3: Solvency removal

- [x] 3.1 `backend/routes/reports.py` — delete `_get_membership_end` (L15-31) + `/solvency` endpoint (L35-238)
- [x] 3.2 Delete `frontend/src/pages/SolvencyReportPage.tsx`
- [x] 3.3 `frontend/src/pages/ReportsPage.tsx` — remove "Reporte de Membresías" card (L7-14) + unused `AlertTriangle` import (L3)
- [x] 3.4 `frontend/src/services/api.ts` — remove `getSolvencyReport` (L298-306) + `SolvencyReport`/`ReportFilters` imports (L15, L18); grep for other usage first
- [x] 3.5 `frontend/src/types/index.ts` — remove `SolvencyReport` (L180) + `ReportFilters` (L312). `App.tsx` verified clean — no change

## Phase 4: Tests

- [x] 4.1 Delete `backend/tests/unit/test_solvency_report.py`
- [x] 4.2 `backend/tests/unit/test_client_delete.py` — remove `TestSolvencyExcludesDeleted` (L246-265) + docstring line (L10)
- [x] 4.3 `backend/tests/models/test_client.py` — `test_valid_status_update` (L215-217) `'suspended'`→`'expired'`; add test rejecting `'suspended'`
- [x] 4.4 New `backend/tests/unit/test_client_expiring.py` — mocked `query_firestore`, assert filters in kwargs: both bounds (inclusive now/now+7d), status ignored when both sent, `isDeleted` still Python-filtered (test_reports_income pattern)

## Phase 5: Manual + cleanup

- [ ] 5.1 MANUAL (pre-deploy): Firebase console — composite indexes on `clients`: `businessId ASC, membershipEnd ASC` and `businessId ASC, branchId ASC, membershipEnd ASC` (index-error message links creation) — **documented in apply report; cannot be done from code**
- [x] 5.2 `backend/README.md` — remove solvency line (L110); document `expiringSoon` (L98)