# Proposal: Payment Deletion with Membership Recalculation

## Intent

Users make mistakes when registering payments, but there is currently NO way to delete one. Since membership dates are calculated **cumulatively** (`extend_membership` adds `plan.durationDays * months_paid` to the current `membershipEnd`), deleting a payment requires rebuilding the client's membership dates from the remaining payments. This change adds soft-delete + full membership recalculation so mistakes are correctable without losing the audit trail.

## Scope

### In Scope

- Soft-delete a payment (`isDeleted: true`) — preserves audit trail
- `DELETE /api/payments/:paymentId` endpoint with role + branch authorization
- `MembershipService.recalculate_membership(client_id)` — rebuild `membershipStart`/`membershipEnd` from all non-deleted payments, sorted chronologically
- Filter `isDeleted` payments out of all payment queries (history, reports, receipts)
- Delete button + confirmation modal in `ClientDetailPage` payment history

### Out of Scope

- Hard delete / permanent purge of payment records
- Restore (undelete) of a soft-deleted payment
- Editing an existing payment's amount/date (separate change)
- Receipt renumbering after deletion

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `payment-flow`: Adds payment deletion + membership recalculation. Requirements change: payment history MUST exclude soft-deleted payments; deleting a payment MUST trigger membership recalculation; authorization rules for deletion are new.

## Approach

**Backend**: Add `DELETE /api/payments/:paymentId` guarded by `@require_role(['super_admin','admin','branch_admin'])` + `validate_branch_access` (branch_admin limited to own branch; cashier/trainer → 403). Soft-delete via `update_document('payments', id, {isDeleted: True})`. Then call `recalculate_membership(client_id)`: fetch non-deleted payments sorted by `paymentDate`, rebuild `membershipStart`/`membershipEnd` from scratch (same cumulative rules as `extend_membership`); if none remain → `isActive: False, status: 'expired'`.

**Frontend**: Add `deletePayment(id)` to `api.ts`; add delete button per payment row in `ClientDetailPage` (hidden for cashier), with confirmation modal; on success, refresh client + payment history.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/routes/payments.py` | Modified | New DELETE endpoint + auth guards |
| `backend/services/payment_service.py` | Modified | Soft-delete method; filter `isDeleted` in queries |
| `backend/services/membership_service.py` | Modified | `recalculate_membership()` |
| `backend/services/firebase_service.py` | Reused | `update_document` for soft delete |
| `frontend/src/services/api.ts` | Modified | `deletePayment()` client method |
| `frontend/src/pages/ClientDetailPage.tsx` | Modified | Delete button + confirmation modal |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing payments lack `isDeleted`; Firestore `== False` excludes missing-field docs | High | Backfill `isDeleted: False` migration, or filter in Python after fetch |
| Recalculation diverges from `extend_membership` cumulative logic | Med | Extract shared date-arithmetic helper; unit-test parity |
| Offline-pending payments (IndexedDB) deleted before sync | Low | Reject delete for unsynced `localId` payments; require server id |
| branch_admin deletes cross-branch payment | Low | Reuse `validate_branch_access`; integration test returns 403 |

## Rollback Plan

Soft delete is reversible: restore by setting `isDeleted: False` and re-running `recalculate_membership`. Endpoint revert = one route removal. No destructive writes — no data-loss rollback required.

## Dependencies

- None (no new packages; reuses Firestore, existing middleware)

## Success Criteria

- [ ] `DELETE /api/payments/:id` soft-deletes and returns recalculated membership
- [ ] Deleting only payment → client `isActive: false`, `status: 'expired'`
- [ ] Deleting oldest payment shortens membership per cumulative recalculation
- [ ] cashier → 403; trainer → 403; branch_admin cross-branch → 403
- [ ] Payment history/report/receipts exclude soft-deleted payments
- [ ] Delete button + confirmation modal works in ClientDetailPage
