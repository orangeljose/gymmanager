# Proposal: Phase 1 — Expenses (Egresos)

## Intent

Gyms record membership income in `payments` but cannot register expenses (payroll, rent, services, repairs, ad-hoc purchases). Real profit is invisible and there is no cash-out ledger. This is Phase 1 of `cash-management` — the simplest, standalone, independently shippable slice.

## Scope

### In Scope
- `expenses` CRUD scoped by business+branch, with soft delete + audit.
- `backend/routes/expenses.py` blueprint: list (filters + pagination), create, update, soft-delete, summary.
- `ExpensesPage.tsx`: stat cards (hoy/semana/mes), category badges, filters (category + date range), by-category chart, "Registrar Egreso" (admin+ only).
- Nav "Egresos" (`TrendingDown`) + `/expenses` route + api.ts/types.
- Firestore composite index `expenses (businessId, date)`.

### Out of Scope
- **No separate income collection.** Income = existing `payments` (memberships) + product sales (Phase 2). Phase 1 is expenses-only.
- Products/stock, `cash_daily` counters, consolidated cash report → later phases.
- Multi-currency conversion, arqueo, supplier entities.

## Capabilities

### New Capabilities
- `cash-expenses`: register/list/update/soft-delete expenses by category, scoped by business+branch; period + by-category summary.

### Modified Capabilities
- None.

## Approach

Mirror `machines.py`: `expenses_bp`, `_scope_ids()`, `_index_error_response`, `_error`, soft-delete audit. The query pushes equality on `businessId` only; `branchId`, `category`, and `date` range are filtered in Python (low volume). Summary = ONE scoped 30-day query grouped in Python — **no `cash_daily` counters** (expenses are low-volume, unlike attendance/sales); document this tradeoff.

Data model `expenses`: id, category (`payroll|supplies|services|rent|maintenance|other`), amountCents (int > 0), description, date (YYYY-MM-DD), businessId, branchId, registeredBy, registeredByName, createdAt, isDeleted, deletedBy/deletedAt.

Endpoints — **admin+ only; cashier/trainer → 403**:
GET/POST `/api/expenses`, PUT/DELETE `/api/expenses/:id`, GET `/api/expenses/summary`.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/routes/expenses.py` | New | Blueprint (5 endpoints) |
| `backend/app.py`, `backend/routes/__init__.py` | Modified | Register blueprint |
| `backend/tests/routes/test_expenses.py` | New | Route + permission tests |
| `frontend/src/pages/ExpensesPage.tsx` | New | UI |
| `frontend/src/services/api.ts`, `types/index.ts` | Modified | Fetchers + types |
| `frontend/src/components/Layout.tsx`, `App.tsx` | Modified | Nav + route |
| Firestore `expenses` + index | New | `(businessId, date)` manual |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Missing composite index | High | Document; `_index_error_response` link |
| Cross-branch leakage | Low | `_scope_ids()` + scope guard |
| Cashier over-permission | Low | `require_role(ADMIN_ROLES)` + tests |
| Unbounded date range | Med | Default 30d window; bounded query |

## Rollback Plan

Additive only. Remove `expenses.py`, unregister the blueprint, revert FE page/api/nav/route. Collection left dormant; no existing collection is mutated. Soft-deleted docs preserve audit.

## Dependencies

- Manual Firestore index `expenses (businessId ASC, date ASC)`.
- `recharts` (already installed).

## Success Criteria

- [ ] Expense CRUD scoped by business+branch, soft-delete + audit, no full scan.
- [ ] Summary returns hoy/semana/mes totals + by-category from one 30d query.
- [ ] Cashier/trainer get 403 on all expense endpoints (tests).
- [ ] Composite index documented.
