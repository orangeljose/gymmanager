# Archive Report: clients-expiring-filter

**Change**: clients-expiring-filter
**Archived**: 2026-09-16
**Branch**: main (commit `631c0c2` merged & pushed)
**Mode**: openspec

## Summary

Removed the dead solvency report end-to-end (frontend page, route/nav, api method, types, backend endpoint, dead helper, tests) and added an `expiringSoon=true` filter to `GET /api/clients` with a Firestore `membershipEnd` window `[now, now+7d]`, replacing the ghost "Suspendidos" dropdown option with "Próximos 7 días". Dashboard "Vencidos" counter untouched (uses `/reports/dashboard`).

## Delta → Main Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| client-management | Updated | 2 added, 1 modified, 1 removed requirement (removal had no standalone main-spec match; solvency refs removed from Purpose + "Deleted Client Exclusion") |
| dashboard-analytics | Updated | 1 added, 1 modified requirement |

### client-management

- **ADDED** `Clients List expiringSoon Filter` — inclusive Firestore window, business/branch scope, precedence over `status`, `active`/`expired`-only statuses, 2 composite indexes documented, 7 scenarios
- **ADDED** `Clients Status Filter Dropdown` — exactly Todos/Activos/Vencidos/Próximos 7 días, no "Suspendidos", at most one of status/expiringSoon, 3 scenarios
- **MODIFIED** `Deleted Client Exclusion from Client Queries` — dropped `GET /api/reports/solvency` from scope and deleted "Solvency excludes deleted" scenario; note added
- **REMOVED** `Solvency Report Feature` (delta) — no standalone requirement existed in main spec; references removed via MODIFIED + Purpose cleanup (non-destructive merge, nothing else lost)

### dashboard-analytics

- **ADDED** `Dashboard Counters Independent of Solvency Report` — overdueClients/expiringThisWeek from `/reports/dashboard` only, 2 scenarios
- **MODIFIED** `ClientsPage Single Fetch` — "Próximos 7 días" counts as filter change; new "One fetch per Próximos 7 días selection" scenario

## Source of Truth Updated

- `openspec/specs/client-management/spec.md`
- `openspec/specs/dashboard-analytics/spec.md`

## Archive Contents

- proposal.md ✅
- specs/client-management/spec.md ✅
- specs/dashboard-analytics/spec.md ✅
- design.md ✅
- tasks.md ✅ (14/15 complete; 5.1 manual Firebase indexes — user-side, pre-deploy)
- verify.md ✅ (PASS WITH WARNINGS — no CRITICAL issues)
- archive.md ✅ (this report)

## Verification Recap

- Build: `npx tsc --noEmit` exit 0 ✅
- Tests: 244 passed, 8 failed — all 8 baseline (identical on `main`); new `test_client_expiring.py` 8/8 PASSED; solvency tests removed ✅
- Spec compliance: 14/20 scenarios automated & passing; 6 untested by design (5 frontend UI manual, 1 Firebase index manual) ⚠️
- Verdict: **PASS WITH WARNINGS** — no CRITICAL issues

## Manual Actions / Outstanding

1. **Firebase console (pre-deploy, task 5.1)**: composite indexes on `clients` — `businessId ASC, membershipEnd ASC` and `businessId ASC, branchId ASC, membershipEnd ASC`. Cannot be done from code; index-error message links creation.
2. **SUGGESTION (from verify)**: stale docs still reference removed endpoint — `docs/API_SPEC.md` (L495/506/840), `docs/REQUIREMENTS.md` (L125), `docs/TEST_PLAN.md` (L236/416). Consider cleaning for accuracy.
3. **SUGGESTION (from verify)**: `super_admin` + `expiringSoon=true` without `businessId` → global range scan; consistent with existing unfiltered-list semantics, but a guard is worth considering.

## Risks

None blocking. Rollback: plain `git revert` (status-only filtering works without new indexes; orphan indexes harmless).

## SDD Cycle Complete

Fully planned, implemented, verified, and archived. Ready for the next change.