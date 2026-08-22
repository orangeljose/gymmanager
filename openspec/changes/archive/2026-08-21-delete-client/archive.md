# Archive Report: delete-client

**Change**: delete-client
**Archived**: 2026-08-21
**Verify verdict**: PASS WITH WARNINGS (no CRITICAL issues)
**Commit**: ba19bb2 (merged to main and pushed)

## Summary

Client deletion with soft delete (Option A — payments preserved). `DELETE /api/clients/:clientId` soft-deletes a client via `update_document('clients', id, {'isDeleted': True, 'deletedBy': uid, 'deletedAt': timestamp})` with a role+branch authorization matrix (super_admin/admin any, branch_admin own branch, cashier/trainer 403). Deleted clients are excluded from operational queries (list, detail, payments-history, solvency, dashboard client metrics) using defensive in-Python filtering (`c.get('isDeleted', False)`) — never Firestore `== False`. Payment-derived metrics (income, topPayingClients) keep deleted clients for historical accuracy. Frontend adds role-gated delete buttons with confirm modals in `ClientDetailPage` (navigate away) and `ClientsPage` (refetch). User-confirmed additions: `PUT /clients/:id` returns 404 for deleted clients; audit fields `deletedBy`/`deletedAt` recorded; manual idempotent backfill `isDeleted: false` on legacy clients.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| client-management | Created | Full spec copied (main spec did not exist): 6 requirements — Delete Client Endpoint, Client Deletion Authorization, Soft Delete Preserves Payments, Deleted Client Exclusion from Client Queries, Backfill isDeleted, Client Deletion UI |
| dashboard-analytics | Updated | 2 ADDED (Client-Derived Metrics Exclude Deleted Clients; Top Paying Clients Keep Deleted Clients), 1 MODIFIED (Fix Overdue Clients Count — added soft-deleted exclusion + new scenario) |
| payment-flow | Updated | 1 MODIFIED (Client Search and Summary — non-deleted client search + Deleted Client Excluded from Search scenario) |

REMOVED requirements: none.

## Archive Contents

- proposal.md ✅
- specs/ ✅ (client-management, dashboard-analytics, payment-flow)
- design.md ✅
- tasks.md ✅ (13/15 complete — 5.1 backfill docs + 5.2 verification check-off remain open; both Phase 5 cleanup, non-blocking)
- verify.md ✅ (PASS WITH WARNINGS)

## Source of Truth Updated

- `openspec/specs/client-management/spec.md` — created
- `openspec/specs/dashboard-analytics/spec.md` — merged
- `openspec/specs/payment-flow/spec.md` — merged

## Verification

- [x] Main specs updated correctly (client-management created; dashboard-analytics and payment-flow merged, pre-existing requirements preserved)
- [x] Change folder moved to `openspec/changes/archive/2026-08-21-delete-client/`
- [x] Archive contains all artifacts (proposal, specs, design, tasks, verify, archive report)
- [x] Active changes directory no longer contains `delete-client`

## Traceability

| Artifact | Location |
|----------|----------|
| Proposal | `openspec/changes/archive/2026-08-21-delete-client/proposal.md` |
| Specs (delta) | `openspec/changes/archive/2026-08-21-delete-client/specs/` |
| Design | `openspec/changes/archive/2026-08-21-delete-client/design.md` |
| Tasks | `openspec/changes/archive/2026-08-21-delete-client/tasks.md` |
| Verify | `openspec/changes/archive/2026-08-21-delete-client/verify.md` |
| Archive report | `openspec/changes/archive/2026-08-21-delete-client/archive.md` |

## Notes / Warnings Carried Forward

- Task 5.1 (document idempotent backfill `isDeleted: false` in PR description) — pending; backfill itself manually performed per summary.
- Task 5.2 (pytest/tsc check-off) — effectively satisfied by verify (26 new tests pass, tsc clean); mark done after PR wrap-up.
- No dedicated test for `GET /api/clients?search=<deleted-name>` and `GET /api/clients/:id/payments` → 404 on deleted — suggested follow-ups, non-blocking.
- 18 pre-existing baseline test failures (order-dependent module-binding) confirmed identical at base commit — not regressions.

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. Ready for the next change.