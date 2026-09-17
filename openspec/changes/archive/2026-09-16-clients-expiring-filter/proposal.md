# Proposal: Clients Expiring Filter & Solvency Report Removal

## Intent

Two linked cleanup/UX goals:

1. **Solvency report is dead code**: page absent from the menu, reachable only by direct URL, consumes Firestore reads nobody needs. Remove it end-to-end.
2. **ClientsPage dropdown offers a ghost status**: "Suspendidos" (`suspended`) is accepted by the API but no action in the app can set it. Replace it with "Próximos 7 días" — a date-range filter (`membershipEnd` within the next 7 days) matching real renewal-intent data.

## Scope

### In Scope
- Remove solvency report: `SolvencyReportPage.tsx`, route in `App.tsx`, link in `ReportsPage.tsx`, `getSolvencyReport` in `api.ts`, `SolvencyReport`/`ReportFilters` types (verify no other usage), `GET /api/reports/solvency` in `backend/routes/reports.py` + related tests
- Add `expiringSoon=true` query param to `GET /api/clients` — Firestore range filter on `membershipEnd`
- Remove ghost `suspended` from valid statuses (`backend/models/client.py`)
- Replace "Suspendidos" dropdown option with "Próximos 7 días" on ClientsPage; wire through `useClients`/`fetchClients`
- Document required composite index

### Out of Scope
- Dashboard "Vencidos" counter (uses `/api/reports/dashboard`, computed independently — unaffected)
- New UI beyond the dropdown filter
- Changing the 7-day window definition

## Capabilities

### New Capabilities

None

### Modified Capabilities
- `client-management`: remove `GET /api/reports/solvency` from "Deleted Client Exclusion from Client Queries"; add `expiringSoon` filter requirement (replacing `suspended` status) to the client list query
- `dashboard-analytics`: extend "ClientsPage Single Fetch" to cover the new "Próximos 7 días" filter option (one fetch per filter change still holds)

## Approach

- **Backend (Option A)**: `GET /api/clients?expiringSoon=true` → Firestore query `businessId == X` (+ `branchId == Y` when scoped), `isDeleted == false`, `membershipEnd >= now`, `membershipEnd <= now+7d`. Requires composite index (businessId, branchId?, isDeleted, membershipEnd) — create via Firebase console; the index-error message provides the direct link (pattern already used by income reports). Keeps pagination and quota-efficiency.
- **Frontend**: "Próximos 7 días" maps to `expiringSoon=true`; passed through `useClients`/`fetchClients`.
- **Solvency removal**: delete page, route, nav entry, api method, types; remove endpoint and tests.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/pages/SolvencyReportPage.tsx` | Removed | Dead page |
| `frontend/src/App.tsx` | Modified | Remove solvency route |
| `frontend/src/pages/ReportsPage.tsx` | Modified | Remove solvency link |
| `frontend/src/services/api.ts` | Modified | Remove `getSolvencyReport`; add `expiringSoon` param |
| `frontend/src/types/index.ts` | Modified | Remove `SolvencyReport`/`ReportFilters` |
| `frontend/src/pages/ClientsPage.tsx` | Modified | New dropdown option |
| `backend/routes/reports.py` | Modified | Remove `GET /api/reports/solvency` |
| `backend/routes/clients.py` | Modified | `expiringSoon` param |
| `backend/models/client.py` | Modified | Drop `suspended` from valid statuses |
| Firebase console | Modified | Composite index |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Missing composite index fails filtered query | Med | Document index in design; index-error link guides creation; verify in apply phase |
| Removed types used elsewhere | Low | Grep for `SolvencyReport`/`ReportFilters` before removal |
| Tests reference solvency endpoint | Med | Remove/update with endpoint removal |

## Rollback Plan

- Solvency removal: plain git revert (files restored, endpoint returns) — no data migration involved.
- expiringSoon: revert to status-only filtering; leaving the composite index in place is harmless.

## Dependencies

- Firebase console access to create the composite index
- No external packages

## Success Criteria

- [ ] App builds and existing tests pass after solvency removal; `/reports/solvency` no longer reachable
- [ ] "Próximos 7 días" returns only clients expiring within 7 days, correct with pagination and branch scope
- [ ] "Suspendidos" option gone from UI; backend no longer accepts `suspended`
- [ ] Dashboard "Vencidos" counter unchanged