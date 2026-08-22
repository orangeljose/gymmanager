# Tasks: Payment Deletion with Membership Recalculation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450–550 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend services) → PR 2 (backend routes) → PR 3 (frontend) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Membership recalc + delete_payment + filtering (services) | PR 1 | Base: main/tracker; unit tests included |
| 2 | DELETE route + receipts/reports filtering | PR 2 | Depends on PR 1; route tests included |
| 3 | Frontend delete button + confirm modal | PR 3 | Independent of PR 1–2 |

## Phase 1: Backend Services

- [x] 1.1 `backend/services/membership_service.py` — add `_advance_end(end_date, duration_days, anchor_date)` returning `max(end_date, anchor_date) + timedelta(days=duration_days)`; refactor `calculate_new_end_date` to call it with `anchor=now`.
- [x] 1.2 Add `MembershipService.recalculate_membership(client_id)`: fetch client payments, filter `not p.get('isDeleted', False)`, sort by `paymentDate or createdAt`, rebuild `membershipStart`/`membershipEnd` cumulatively via `_advance_end`; no payments → `isActive:False, status:'expired'`.
- [x] 1.3 `backend/services/payment_service.py` — add `delete_payment(payment_id, current_user) -> {'status':'not_found'|'forbidden'|'success','data':...}`: fetch payment, 404 if missing/deleted, inline branch check (super_admin skip; user `branchId` must equal `payment.branchId`), else `update_document(..., {'isDeleted':True})` + `recalculate_membership`.
- [x] 1.4 `register_payment` — persist `monthsPaid` (default 1) and `isDeleted: False` in the `payment_data` dict.
- [x] 1.5 Filter `isDeleted` in `get_client_payments` and `get_payment_report` (in-Python `if p.get('isDeleted', False): continue`).

## Phase 2: Backend Routes

- [x] 2.1 `backend/routes/payments.py` — add `DELETE /<payment_id>` with `@require_auth @require_role(['super_admin','admin','branch_admin'])`; map service status → 200/404/403.
- [x] 2.2 `backend/routes/payments.py` `get_receipts` — skip `isDeleted` payments in the transform loop and the `total` count.
- [x] 2.3 `backend/routes/reports.py` — skip `isDeleted` in Python loops of `get_daily_income_report`, `get_income_by_method_report`, `get_dashboard`, and the `last_payment` lookup in `get_solvency_report`.

## Phase 3: Frontend

- [x] 3.1 `frontend/src/types/index.ts` — add optional `isDeleted?: boolean` to `Payment`.
- [x] 3.2 `frontend/src/services/api.ts` — add `deletePayment(id: string)` calling `DELETE /payments/${id}`.
- [x] 3.3 `frontend/src/pages/ClientDetailPage.tsx` — add `Trash2` delete button per row gated by `['super_admin','admin','branch_admin'].includes(user?.role)`, inline confirm modal (mirror `PaymentForm` `fixed inset-0` pattern), refresh client + payments on success.

## Phase 4: Tests

- [x] 4.1 `backend/tests/unit/test_membership_recalculate.py` — recalc parity: none/single/oldest/newest/middle/gap-reanchor; `_advance_end` unit.
- [x] 4.2 `backend/tests/unit/test_payment_delete.py` — `delete_payment` statuses + `isDeleted` filter in `get_client_payments`.
- [x] 4.3 `backend/tests/routes/test_payment_delete.py` — 200/404/403 role+branch matrix (super_admin/admin/branch_admin/cashier/trainer; cross-branch 403).
- [ ] 4.4 Run `pytest backend/tests` green; manual check cashier sees no delete button.
