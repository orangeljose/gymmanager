# Design: Payment Deletion with Membership Recalculation

## Technical Approach

Add a soft-delete endpoint (`DELETE /api/payments/:paymentId`) guarded by role + branch authorization, plus `MembershipService.recalculate_membership()` that rebuilds a client's membership dates from their remaining non-deleted payments. Frontend adds a role-gated delete button + confirmation modal. Deletion sets `isDeleted: true` and preserves the audit trail.

## Architecture Decisions

### Decision 1: Branch authorization — inline check, not `validate_branch_access`

| Option | Tradeoff | Decision |
|---|---|---|
| `@validate_branch_access(...)` decorator | branchId unknown until fetch; decorator needs a static id | ❌ |
| Inline check after fetch | matches existing `register_payment`/`get_payment_report` pattern | ✅ |

**Choice**: Route applies `require_auth` + `require_role(['super_admin','admin','branch_admin'])`; the service does an inline branch check after fetching the payment.
**Rationale**: Existing payments routes already validate branch inline; `validate_branch_access` requires a static `target_branch_id`. Rule: `super_admin` skips; a user with `branchId` set must match `payment.branchId`; an admin without `branchId` may delete cross-branch (existing "admin sin sucursal" convention).

### Decision 2: Sort by `paymentDate`, fallback `createdAt`

**Choice**: Sort key `payment.get('paymentDate') or payment.get('createdAt')`, ascending.
**Rationale**: Spec mandates ascending `paymentDate`; legacy payments may lack it (field added later), so fall back to `createdAt` (the pre-existing order field). Membership follows real payment chronology.

### Decision 3: Rebuild-from-scratch with re-anchor parity

**Choice**: Extract `_advance_end(end_date, duration_days, anchor_date)` returning `max(end_date, anchor_date) + timedelta(days=duration_days)`. Refactor `calculate_new_end_date` to call it with `anchor=now` (preserving `extend_membership` behavior); `recalculate_membership` uses `anchor=payment_date`.
**Rationale**: Deduplicates the cumulative-extension arithmetic; single tested primitive keeps parity (mitigates the proposal's divergence risk).

### Decision 4: `monthsPaid` not persisted → default 1 + persist going forward

**Choice**: `duration_days = plan.durationDays * payment.get('monthsPaid', 1)`. Also make `register_payment` persist `monthsPaid` and `isDeleted: False`.
**Rationale**: `monthsPaid` is read but never written to the payment doc, and `validate_payment_amount` forces `amount == plan.price` (single month). Defaulting to 1 is correct today and future-proof.

### Decision 5: In-Python `isDeleted` filtering (never Firestore `where`)

| Option | Tradeoff | Decision |
|---|---|---|
| Firestore `where('isDeleted','==',False)` | excludes legacy docs missing the field | ❌ |
| In-Python `if p.get('isDeleted', False): skip` | treats missing field as active; matches spec | ✅ |

### Decision 6: Delete logic in `PaymentService.delete_payment()`; status envelope

**Choice**: New `PaymentService.delete_payment(payment_id, current_user) -> Dict` returning `{'status': 'not_found' | 'forbidden' | 'success', 'data': ...}`; the route maps to 404/403/200.
**Rationale**: Keeps Firestore reads/writes in the service layer (consistent with `register_payment`); route stays a thin HTTP mapper.

### Decision 7: Frontend — inline confirm modal, no new component

**Choice**: Add `deletePayment()` to `api.ts`; `ClientDetailPage` uses a `deleteTarget` state + inline overlay modal (mirrors `PaymentForm`'s inline `fixed inset-0` modal pattern); `Trash2` icon button gated by `['super_admin','admin','branch_admin'].includes(user.role)`.
**Rationale**: No existing generic confirm component; inline modal matches the codebase's only modal precedent and avoids a new shared component for one use.

## Data Flow

```
ClientDetailPage ── DELETE /api/payments/:id ──▶ require_auth / require_role
        ▲                                            │ (403 cashier/trainer)
        │                                            ▼
   refresh client+payments ◀── 200 {membership} ── PaymentService.delete_payment
                                                          │ fetch → 404? branch? → isDeleted:true
                                                          ▼
                                          MembershipService.recalculate_membership
                                                          │ non-deleted payments → sort → rebuild
                                                          ▼
                                      update client membershipStart/End/plan/isActive/status
```

## Algorithm: `recalculate_membership(client_id)`

```python
payments = query_firestore('payments', clientId==client_id)
active = [p for p in payments if not p.get('isDeleted', False)]
if not active:
    update_document('clients', client_id, dict(
        membershipStart=None, membershipEnd=None, membershipPlanId=None,
        isActive=False, status='expired')); return

active.sort(key=lambda p: p.get('paymentDate') or p.get('createdAt'))
running_end = None
last_plan_id = None
for p in active:
    plan = get_plan_by_id(p['membershipPlanId'])
    dur = plan['durationDays'] * p.get('monthsPaid', 1)
    running_end = _advance_end(running_end, dur, parse_date(p))
    last_plan_id = p['membershipPlanId']

is_active = running_end > now
update_document('clients', client_id, dict(
    membershipStart=parse_date(active[0]), membershipEnd=running_end,
    membershipPlanId=last_plan_id, isActive=is_active,
    status='active' if is_active else 'expired'))
```

`parse_date(p)` returns the payment's `paymentDate` (fallback `createdAt`) as tz-aware datetime; `_advance_end` re-anchors at the payment date when the running end has lapsed.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/routes/payments.py` | Modify | `DELETE /<payment_id>` endpoint; filter `isDeleted` in `/receipts` |
| `backend/services/payment_service.py` | Modify | `delete_payment()`; persist `monthsPaid`+`isDeleted:False` in `register_payment`; filter `isDeleted` in `get_client_payments`/`get_payment_report` |
| `backend/services/membership_service.py` | Modify | `recalculate_membership()` + `_advance_end()`; refactor `calculate_new_end_date` |
| `backend/routes/reports.py` | Modify | filter `isDeleted` in daily / by-method / dashboard loops |
| `frontend/src/services/api.ts` | Modify | `deletePayment(id)` |
| `frontend/src/pages/ClientDetailPage.tsx` | Modify | delete button + confirm modal + refresh |
| `frontend/src/types/index.ts` | Modify | optional `isDeleted?: boolean` on `Payment` |

## Interfaces / Contracts

`DELETE /api/payments/:paymentId` → `200 {success, data:{clientId, membershipStart, membershipEnd, membershipPlanId, isActive, status}}`; `404` unknown or already-deleted; `403` forbidden role/branch.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit (`backend/tests/unit`) | `recalculate_membership` parity: none/single/oldest/newest/middle/gap-reanchor | mock `FirebaseService`; assert dates |
| Unit | `delete_payment` statuses + `isDeleted` filter | mock `FirebaseService` |
| Routes (`backend/tests/routes`) | 200/404/403 role matrix | Flask test client |
| E2E | button visibility per role, confirm modal, refresh | manual + Vitest if present |

## Migration / Rollout

Owner manually backfills `isDeleted: false` on the 7 existing payments (documented). No Firestore index migration. Rollback = set `isDeleted: false` and re-run `recalculate_membership` (no destructive writes).

## Open Questions

- [ ] Should `delete_payment` also record `deletedBy`/`deletedAt` audit fields? (Not in spec; would strengthen the audit trail.)
