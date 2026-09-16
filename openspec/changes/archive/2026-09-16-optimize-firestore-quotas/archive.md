# Archive Report: Optimize Firestore Quotas

**Change**: optimize-firestore-quotas
**Archived on**: 2026-09-16
**Final commit**: b61d777 (main, pushed)
**SDD cycle**: Completed — proposal → specs → design → tasks → apply → verify → archive

## Executive Summary

Eliminated the biggest Firestore read burners that exhausted the Spark 50K reads/day quota in ~1 week of light use (~50 payments, ~47 clients; 50K reads in one 3-hour window). Backend now pushes filters into Firestore: income daily/by-method endpoints query `businessId ==`, `createdAt >=/<=` (and `branchId ==` when a branch scope applies) instead of reading all payments (~2,300 reads/report view → ~30); `generate_receipt_number` replaced the full-history scan (~300 reads/payment, growing forever) with a constant-cost Firestore `count()` aggregation + timestamp fallback (never blocks, never fabricates `-001`); the dashboard payments query gained a `createdAt >= now-30d` bound plus a `recentClients` payload (top 5 by createdAt DESC, zero extra reads) so DashboardPage dropped its `getClients({limit:100})` call. Frontend: `useClients` mount auto-fetch removed (ClientForm/Detail never read `clients`), ClientsPage owns the initial + businessId-change fetch with a first-render debounce guard — exactly 1 GET /clients per mount/filter change. Defensive Python `isDeleted` + deleted-client exclusions preserved throughout (Firestore equality omits docs missing a field, so legacy docs stay safe). 24 new tests (19 backend + 5 dashboard), `tsc --noEmit` clean, 0 regressions. Two composite Firestore indexes created manually by the user pre-deploy. Verify verdict: PASS WITH WARNINGS (only pre-existing flaky baseline, 2 untested-by-design platform/UI scenarios, non-blocking suggestions).

## Specs Synced

| Domain | Action | Requirements |
|--------|--------|-------------|
| `payment-flow` | Updated (delta merged into existing main spec) | 1 requirement MODIFIED (`Receipt Number Generation` — count() mechanism replaces full scan), 12 existing preserved; 4 new scenarios added (Quota-efficient generation, Uniqueness and format preserved, Gaps tolerated, Aggregation failure fallback) |
| `dashboard-analytics` | Updated (delta merged into existing main spec) | 5 existing preserved + 4 added (Income Reports Filtered in Firestore, Dashboard Payment Query Filtered, Recent Clients Data Contract, ClientsPage Single Fetch); 13 new scenarios added |

Merge was non-destructive: one MODIFIED requirement (same name, mechanism + scenarios updated in place) and four ADDED requirements appended. All requirements not mentioned in the deltas preserved verbatim.

## Deliverables

- **Backend service**: `count_firestore(collection, filters) -> int` in `firebase_service.py` — Firestore `count()` aggregation, RAISES on failure/ceiling (never fakes 0).
- **Backend service**: `generate_receipt_number` (`payment_service.py`) — `count_firestore(payments, businessId ==) + 1` → `P-YYYYMMDD-XXX`; timestamp fallback `P-YYYYMMDD-HHMMSSfff` on error/ceiling; count query has NO `isDeleted` filter (soft-deleted counted, len+1 semantics preserved).
- **Backend routes**: `reports.py` income daily + by-method — Firestore query with `businessId ==` (super_admin: businessId from request param), `createdAt >= start`, `createdAt <= end`, `branchId ==` when effective; NO `order_by` (Python sorts; ASC indexes suffice); defensive Python isDeleted + deleted-client exclusion + `paymentDate or createdAt` final check kept.
- **Backend route**: dashboard (`reports.py`) — payments query adds `createdAt >= now-30d` bound (businessId/branchId filters already present); `recentClients` (top 5 by createdAt DESC from already-fetched clients, deleted excluded) added to payload — zero extra reads.
- **Frontend types**: `RecentClient` + `DashboardData.recentClients` in `types/index.ts`.
- **Frontend**: `DashboardPage` drops `getClients({limit:100})`, renders "Clientes Recientes" from payload with empty state.
- **Frontend**: `useClients` mount effect removed; `ClientsPage` single-fetch owner (page-level effect on `effectiveBusinessId`, first-render `useRef` guard on debounce, state-only status/branch/Limpiar handlers, explicit fetch on page-change/delete).
- **Tests**: `test_receipt_number.py` (new, 11), `test_reports_income.py` (new, 8), `test_dashboard.py` (extended, 5) — 24 total.
- **Manual (user, Firebase console)**: composite indexes `payments (businessId ASC, createdAt ASC)` and `payments (businessId ASC, branchId ASC, createdAt ASC)` — confirmed created pre-deploy.

## Quality Gates

| Gate | Result |
|------|--------|
| Backend targeted tests | ✅ 24/24 passed (19 new + 5 dashboard) |
| Backend full suite | ⚠️ 78 passed / 7 failed — failures PRE-EXISTING order-dependent flaky subset of `test_dashboard.py` (identical set fails on `main`; test_plans/test_users untouched) |
| Frontend type check | ✅ `tsc --noEmit` 0 errors |
| Spec compliance | ✅ 15/17 scenarios compliant, 2 PARTIAL/UNTESTED (UI display + platform index behavior — non-blocking per verify) |
| Tasks complete | ✅ 12/12 apply tasks + 5.1/5.2 manual indexes confirmed; 5.3 manual browser/console check pending user |
| Coverage | ➖ Not measured (no threshold configured) |

## Known Issues (from verify)

| Severity | Issue | Status |
|----------|-------|--------|
| WARNING | `test_dashboard.py` 12 pre-existing order-dependent failures (`_make_client`-based tests) — verified identical on `main`; file stays flaky until legacy tests migrate to `_dashboard_with` | Pre-existing, non-blocking |
| WARNING | "Missing composite index" scenario UNTESTED (no Firestore emulator in setup); platform-guaranteed behavior, mitigated by pre-deploy manual indexes (user confirmed) | Non-blocking |
| WARNING | "Receipt number assigned" display scenario has no automated test (no frontend test infra; generation fully tested, display is pre-existing untouched UI) | Non-blocking |
| SUGGESTION | `recentClients[].membershipEnd` passed through raw — normalize to ISO string in backend if doc stores a Timestamp (contract exactness; widget doesn't render it today) | Future |
| SUGGESTION | `get_dashboard` uses deprecated `datetime.utcnow()` (Python 3.13 deprecation) — migrate to `datetime.now(timezone.utc)` with naive normalization | Future |
| SUGGESTION | At ~1000 payments/business the count() ceiling forces every receipt to timestamp fallback (format change) — consider design's upgrade path B (business-doc counter) proactively | Future (deferred) |

## Verification Summary

- **Verdict**: PASS WITH WARNINGS — ready for archive
- **Critical issues**: None
- **Compliance**: 15/17 scenarios fully compliant; 2 partial/untested (UI display, platform index behavior) — non-blocking

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `backend/services/firebase_service.py` | Modified | `count_firestore(collection, filters)` — count aggregation, raises on failure/ceiling |
| `backend/services/payment_service.py` | Modified | `generate_receipt_number` — count()+1, timestamp fallback, no isDeleted in count |
| `backend/routes/reports.py` | Modified | Income daily/by-method filtered queries (businessId/createdAt/branchId); dashboard `createdAt >= now-30d` + `recentClients` |
| `frontend/src/types/index.ts` | Modified | `RecentClient` + `DashboardData.recentClients` |
| `frontend/src/pages/DashboardPage.tsx` | Modified | Dropped `getClients({limit:100})`; renders recentClients + empty state |
| `frontend/src/hooks/useClients.ts` | Modified | Removed mount auto-fetch effect |
| `frontend/src/pages/ClientsPage.tsx` | Modified | Single-fetch owner + first-render debounce guard + state-only handlers |
| `backend/tests/unit/test_receipt_number.py` | New | count seq, timestamp fallback (error/ceiling), no isDeleted filter (11 tests) |
| `backend/tests/unit/test_reports_income.py` | New | filter construction, super_admin resolution, Python exclusions (8 tests) |
| `backend/tests/unit/test_dashboard.py` | Modified | recentClients contract + payments query window (5 new tests) |
| Firestore | Manual | Composite indexes 1 (`businessId ASC, createdAt ASC`) and 2 (`businessId ASC, branchId ASC, createdAt ASC`) — created by user |

## Architecture Decisions Applied

| Decision | Outcome |
|----------|---------|
| D1 Receipt number: `count()` aggregation + timestamp fallback (never `-001`) | ✅ count()+1, ceiling >= 1000 raises → caller falls back to `P-YYYYMMDD-HHMMSSfff`; upgrade path B documented for ~1000 payments |
| D2 Income range on `createdAt`, not `paymentDate` | ✅ createdAt always set (SERVER_TIMESTAMP) + legacy-safe; `paymentDate or createdAt` Python check kept as final in-memory filter |
| D3 Dashboard: recentClients from already-fetched list + 30-day bound | ✅ zero extra reads; payments query bounded `createdAt >= now-30d` |
| D4 ClientsPage single fetch owner | ✅ hook effect removed; page effect + first-render guard; handlers state-only; search debounced |
| D5 Composite indexes 1 & 2 (manual, pre-deploy); no order_by → no DESC variants | ✅ user confirmed both created; no order_by added to queries |

## Deferred (out of scope, from proposal/verify)

- Request-level URL cache in `api.ts`
- Auth `getIdToken(true)` removal; `require_auth` per-request user read
- Search min-length enforcement
- N+1 loops: solvency last-payment, membership recalculate, sync batches
- Receipts 1,000-doc scan (`payments.py` L396)
- ClientDetailPage/PaymentsNewPage duplicated plans + payment-accounts fetches
- Business-doc counter for receipt numbering (upgrade path B, before ~1000 payments/business)

## Archive Contents

```
openspec/changes/archive/2026-09-16-optimize-firestore-quotas/
├── proposal.md      ✅ — Intent, scope, approach, risks, rollback
├── specs/            ✅ — 2 delta specs (merged into main specs)
│   ├── payment-flow/spec.md
│   └── dashboard-analytics/spec.md
├── design.md         ✅ — 5 architecture decisions, data flow, contracts
├── tasks.md          ✅ — 12/12 apply tasks complete + 5.1/5.2 confirmed (5.3 manual pending user)
├── verify.md         ✅ — PASS WITH WARNINGS, 15/17 compliant
└── archive.md        ✅ — This report
```

## Source of Truth Updated

- `openspec/specs/payment-flow/spec.md` — `Receipt Number Generation` now mandates the constant-cost count() mechanism (13 requirements total: 12 preserved + 1 modified).
- `openspec/specs/dashboard-analytics/spec.md` — 9 requirements (5 preserved + 4 added): Income Reports Filtered in Firestore, Dashboard Payment Query Filtered, Recent Clients Data Contract, ClientsPage Single Fetch.

## SDD Cycle Complete

The change has been fully planned (proposal → specs → design → tasks), implemented (2 stacked PRs merged to main as b61d777), verified (PASS WITH WARNINGS), and archived. Ready for the next change.