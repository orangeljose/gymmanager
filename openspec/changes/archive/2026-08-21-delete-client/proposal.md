# Proposal: Client Deletion (Soft Delete, Payments Preserved)

## Intent

The gym owner needs to remove clients who left the gym or were registered by mistake. User-confirmed decision (Option A): **soft delete the client but preserve ALL their payments** — historical income must remain accurate. Deleted clients disappear from operational views (list, solvency, dashboard, quick-pay) while their payments stay in income reports and receipt history.

## Scope

### In Scope

- Soft delete client (`isDeleted: true`), reusing the delete-payment pattern
- `DELETE /api/clients/:clientId` with role + branch authorization
- Filter deleted clients from: `GET /clients`, `GET /clients/:id` (404), `/reports/solvency`, `/reports/dashboard` (activeClients, overdue, expiring), quick-pay search
- Payments of deleted clients untouched (Option A)
- Delete button + confirm modal in `ClientDetailPage` (+ row action in `ClientsPage`)
- Backfill `isDeleted: false` on existing clients (idempotent)

### Out of Scope

- Hard delete / permanent purge
- Restore (undelete) UI
- Editing clients (separate change)
- Trainer access to deletion

## Capabilities

### New Capabilities

- `client-management`: client soft-deletion endpoint, authorization matrix, and deleted-client filtering across operational queries

### Modified Capabilities

- `dashboard-analytics`: client-derived metrics (activeClients, overdue, expiring) MUST exclude soft-deleted clients; topPayingClients SHALL keep them as historical record
- `payment-flow`: quick-pay client search MUST exclude soft-deleted clients

## Approach

**Backend**: Add `DELETE /api/clients/:clientId` guarded by `@require_role(['super_admin','admin','branch_admin'])` + `validate_branch_access` (branch_admin own branch only; cashier/trainer → 403). Soft-delete via `update_document('clients', id, {isDeleted: True})`. Do NOT modify payment documents. Apply in-Python `isDeleted` filtering (Firestore `== False` omits missing-field docs) in `clients.py` list/detail (404 when deleted) and `reports.py` solvency + dashboard. **Decision**: client-derived metrics exclude deleted clients; payment-derived metrics (income, top payers) keep them for historical accuracy.

**Frontend**: `deleteClient(id)` in `api.ts`; delete button + confirm modal in `ClientDetailPage` (hidden for cashier), mirrored as a row action in `ClientsPage`; refresh after success.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/routes/clients.py` | Modified | New DELETE endpoint + auth guards; filter isDeleted in list/detail |
| `backend/routes/reports.py` | Modified | Exclude isDeleted clients in solvency + dashboard |
| `backend/services/firebase_service.py` | Reused | `update_document` for soft delete |
| `frontend/src/services/api.ts` | Modified | `deleteClient()` method |
| `frontend/src/pages/ClientDetailPage.tsx` | Modified | Delete button + confirm modal |
| `frontend/src/pages/ClientsPage.tsx` | Modified | Delete row action |
| `frontend/src/pages/PaymentsNewPage.tsx` | Modified | Search excludes deleted clients |
| `frontend/src/types/index.ts` | Modified | `isDeleted` on Client type |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Legacy clients lack `isDeleted`; Firestore `== False` omits them | High | In-Python defensive filtering (delete-payment precedent) |
| branch_admin deletes cross-branch client | Low | Reuse `validate_branch_access`; 403 test |
| Deleted client still in topPayingClients | Low | Documented historical-intent decision |
| Backfill race with concurrent writes | Low | Idempotent boolean write; safe default |

## Rollback Plan

Fully reversible: restore by setting `isDeleted: false`. Endpoint revert = one route removal. Payments are never modified — no data-loss rollback required.

## Dependencies

- None (reuses Firestore + existing auth middleware)

## Success Criteria

- [ ] DELETE soft-deletes client; cashier/trainer → 403; branch_admin cross-branch → 403
- [ ] GET deleted client by id → 404
- [ ] Deleted client absent from list, solvency, dashboard counts, quick-pay search
- [ ] Client's payments + income reports unchanged after deletion
- [ ] Delete button + confirm modal works (ClientDetailPage and ClientsPage)