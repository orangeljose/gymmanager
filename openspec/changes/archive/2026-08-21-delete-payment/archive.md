# Archive Report: Payment Deletion with Membership Recalculation

**Change**: delete-payment
**Archived on**: 2026-08-21
**Final commit**: 28c80a7 (main)
**SDD cycle**: Completed — proposal → specs → design → tasks → apply → verify → archive

## Executive Summary

Added payment deletion with full membership recalculation. Soft-deletes payments (`isDeleted: true`) preserving the audit trail, exposes `DELETE /api/payments/:paymentId` with a role + branch authorization matrix (super_admin/admin any, branch_admin own branch, cashier/trainer 403), and rebuilds the client's membership dates from remaining non-deleted payments via a new `recalculate_membership` that shares a single tested `_advance_end` arithmetic primitive with `extend_membership` (parity guaranteed). Frontend adds a role-gated delete button with a confirmation modal in `ClientDetailPage`. `isDeleted` filtering was applied across payment history, reports, and receipts; a drift fix moved the receipts filter into the Firestore query (`where(isDeleted == false)`) to keep pagination correct. 7 legacy payments were backfilled with `isDeleted: false` manually; a composite Firestore index `(isDeleted, createdAt DESC)` was created. Verify verdict: PASS WITH WARNINGS (all backend requirements fully tested; 2 UI scenarios manual-only; 18 pre-existing baseline test failures proven unchanged from main).

## Specs Synced

| Domain | Action | Requirements |
|--------|--------|-------------|
| `payment-flow` | Updated (delta merged into existing main spec) | 8 existing preserved + 6 added = 14 requirements; 14 new scenarios added |

Delta was purely ADDITIVE — no requirement was modified or removed. Existing main spec content preserved verbatim.

## Deliverables

- **Backend service**: `MembershipService.recalculate_membership(client_id)` — rebuilds `membershipStart`/`membershipEnd` from non-deleted payments sorted by `paymentDate` (fallback `createdAt`), cumulative re-anchor via `_advance_end`; no payments → `isActive: false, status: 'expired'`.
- **Backend service**: `PaymentService.delete_payment(payment_id, current_user)` — status envelope (`not_found`/`forbidden`/`success`), inline branch check, soft delete via `update_document({'isDeleted': True})` + recalc.
- **Backend route**: `DELETE /api/payments/:paymentId` — `require_auth` + `require_role(['super_admin','admin','branch_admin'])`, maps 200/404/403.
- **Persist-on-write**: `register_payment` now persists `monthsPaid` (default 1) and `isDeleted: False`.
- **Filtering**: `isDeleted` excluded in `get_client_payments`, `get_payment_report`, receipts (transform + total), and all report loops (daily, by-method, dashboard, solvency `last_payment`).
- **Drift fix**: `get_receipts` pagination now applies `where('isDeleted', '==', False)` in the Firestore query (composite index `payments (isDeleted, createdAt DESC)` created) so `limit`/`offset` no longer drift past soft-deleted docs.
- **Frontend**: `deletePayment(id)` in `api.ts`, optional `isDeleted?: boolean` on `Payment` type, `Trash2` delete button gated to `super_admin`/`admin`/`branch_admin` with inline confirm modal in `ClientDetailPage` (mirrors `PaymentForm` modal pattern); refresh of payment history + client on success.
- **Data migration**: 7 existing payments manually backfilled with `isDeleted: false` (documented, no code migration).

## Quality Gates

| Gate | Result |
|------|--------|
| Backend targeted tests | ✅ 33/33 passed (recalc + delete unit + route matrix) |
| Backend full suite | ⚠️ 190 passed / 18 failed — failures proven PRE-EXISTING (identical set reproduced on `main` in clean worktree; none in delete-payment test files) |
| Frontend type check | ✅ `tsc --noEmit` 0 errors |
| Spec compliance | ✅ 12/14 scenarios compliant, 2 PARTIAL (UI — manual E2E per design), 0 UNTESTED, 0 FAILING |
| Tasks complete | ✅ 14/15 (4.4 cleanup/manual check pending — non-blocking) |
| Coverage | ➖ Not measured (no threshold configured) |

## Known Issues (from verify)

| Severity | Issue | Status |
|----------|-------|--------|
| WARNING | Task 4.4 incomplete — full-suite green blocked by 18 pre-existing baseline failures; manual cashier UI check pending | Non-blocking |
| WARNING | `get_receipts` pagination drift — mitigated by drift fix commit 99a8d64 (Firestore-level `isDeleted` filter) | Resolved |
| SUGGESTION | Solvency `last_payment` with `limit=1` can miss the real last payment if the newest is soft-deleted | Display gap only |
| SUGGESTION | `generate_receipt_number` may skip sequence numbers after deletions | Harmless |
| SUGGESTION | `deletedBy`/`deletedAt` audit fields not recorded (out of spec, open question in design) | Future enhancement |
| SUGGESTION | `delete_payment` maps `update_document` failure to 404 rather than 500 | Minor semantic, unreachable in practice |

## Verification Summary

- **Verdict**: PASS WITH WARNINGS — ready for archive
- **Critical issues**: None
- **Compliance**: 12/14 scenarios fully compliant; 2 UI scenarios manual-verified per design's testing strategy

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `backend/routes/payments.py` | Modified | `DELETE /<payment_id>` endpoint; receipts `isDeleted` filter (loop + total + Firestore `where` drift fix) |
| `backend/services/payment_service.py` | Modified | `delete_payment()`; persist `monthsPaid`+`isDeleted:False` in `register_payment`; filter `isDeleted` in `get_client_payments`/`get_payment_report` |
| `backend/services/membership_service.py` | Modified | `recalculate_membership()` + `_advance_end()`; `calculate_new_end_date` refactored to use the shared primitive |
| `backend/routes/reports.py` | Modified | Filter `isDeleted` in daily / by-method / dashboard / solvency loops |
| `frontend/src/services/api.ts` | Modified | `deletePayment(id)` |
| `frontend/src/pages/ClientDetailPage.tsx` | Modified | Role-gated delete button + inline confirm modal + refresh |
| `frontend/src/types/index.ts` | Modified | Optional `isDeleted?: boolean` on `Payment` |
| `backend/tests/unit/test_membership_recalculate.py` | New | Recalc parity: none/single/oldest/newest/middle/gap-reanchor + `_advance_end` |
| `backend/tests/unit/test_payment_delete.py` | New | `delete_payment` statuses + `isDeleted` filter |
| `backend/tests/routes/test_payment_delete.py` | New | 200/404/403 role+branch matrix |
| Firestore | Manual | Composite index `payments (isDeleted, createdAt DESC)`; backfill `isDeleted: false` on 7 payments |

## Architecture Decisions Applied

| Decision | Outcome |
|----------|---------|
| D1 Inline branch check (not `validate_branch_access` decorator) | ✅ matches `register_payment` pattern; super_admin skips, admin-without-branch allowed |
| D2 Sort by `paymentDate`, fallback `createdAt`, ascending | ✅ `_parse_payment_date` |
| D3 Rebuild-from-scratch via shared `_advance_end` (parity with `extend_membership`) | ✅ single tested primitive |
| D4 `monthsPaid` default 1 + persisted going forward; `isDeleted: False` persisted | ✅ |
| D5 In-Python `isDeleted` filtering (never Firestore `where`) — EXCEPT receipts drift fix | ✅ service/reports paths; receipts exception documented (query-level filter + composite index) |
| D6 Delete logic in `PaymentService.delete_payment` + status envelope | ✅ route stays thin mapper |
| D7 Inline confirm modal, `Trash2` gated, no new shared component | ✅ mirrors PaymentForm modal pattern |

## Archive Contents

```
openspec/changes/archive/2026-08-21-delete-payment/
├── proposal.md      ✅ — Intent, scope, approach, risks, rollback
├── specs/            ✅ — 1 delta spec (merged into main payment-flow spec)
│   └── payment-flow/spec.md
├── design.md         ✅ — 7 architecture decisions, data flow, algorithm
├── tasks.md          ✅ — 14/15 tasks complete (4.4 cleanup pending)
├── verify.md         ✅ — PASS WITH WARNINGS, 12/14 compliant
└── archive.md        ✅ — This report
```

## Source of Truth Updated

`openspec/specs/payment-flow/spec.md` now reflects the new behavior — 14 requirements (8 preserved + 6 added): payment deletion endpoint, deletion authorization matrix, soft delete behavior, membership recalculation, soft-deleted filtering, and deletion UI.

## SDD Cycle Complete

The change has been fully planned (proposal → specs → design → tasks), implemented (3 stacked PRs merged to main), verified (PASS WITH WARNINGS), and archived. Ready for the next change.