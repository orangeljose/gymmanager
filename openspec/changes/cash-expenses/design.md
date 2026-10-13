# Design: Phase 1 — Expenses (Egresos)

## Technical Approach

Mirror `routes/machines.py`: a single `expenses_bp` over one collection (`expenses`), business/branch scoping from `g.current_user` via `_scope_ids()`, an equality filter on `businessId` only in Firestore, and all category/date/search filtering plus summary aggregation in Python (expenses are low-volume, 10–50 docs/business). Soft delete + audit and `_index_error_response` follow the machines blueprint. No daily counters (unlike attendance/sales).

## Architecture Decisions

| # | Decision | Choice | Rationale / Alternatives |
|---|----------|--------|--------------------------|
| 1 | Blueprint & registration | New `routes/expenses.py` (`expenses_bp`, prefix `/api/expenses`); export in `routes/__init__.py` AND import+register in `app.py` | Matches machines exactly (both sites). |
| 2 | Scope resolution | Reuse `_scope_ids()` shape: super_admin reads `businessId`/`branchId` query params; others from `g.current_user` | Identical to machines; single source of scope truth. |
| 3 | Query filtering | Firestore applies `businessId` equality only; `branchId`, `category`, `date` range, `search` filtered in Python | Low volume; avoids composite indexes on `expenses`. Rejected date-range pushdown: negligible gain, adds index burden. |
| 4 | Summary | ONE scoped `businessId` query → Python group by today / rolling-7d / rolling-30d + `byCategory` | No `cash_daily` counters; expenses are low-volume (unlike attendance). |
| 5 | Soft delete | `DELETE` → `update{isDeleted:true, deletedBy, deletedAt}`; list/summary exclude `isDeleted`; PUT → 404 | Follows delete-client audit pattern. Field is `isDeleted` (per proposal). |
| 6 | Permissions | `require_role(ADMIN_ROLES)` on all 5 endpoints; `ADMIN_ROLES=[super_admin,admin,branch_admin]` | Cashier/trainer 403; expense data is financial. |
| 7 | Frontend page | `ExpensesPage.tsx` with 3 stat cards (Hoy/Semana/Mes), category badges, category + date-range filters, `ExpenseForm.tsx` modal for create/edit | Mirrors MachinesPage list+cards+modal; no separate `/expenses/new` route. |
| 8 | Nav placement | Top-level "Egresos" (`TrendingDown`) after "Equipamiento" | Simplest for Phase 1; restructure under a "Finanzas"/"Caja" group when Phase 2/3 add entries. |
| 9 | Index | Document `expenses (businessId ASC, date ASC)` for manual creation; `_index_error_response` links it | Supports date sort/range; created manually on Spark. |

## Data Flow

    ExpensesPage ──getExpenses(filters)──► GET /api/expenses ──where(businessId)==──► Firestore expenses
         │                                                                                  │
         └──getExpensesSummary()──► GET /api/expenses/summary ◄── python 7d/30d totals ──────┘
    ExpenseForm (modal) ──createExpense/updateExpense──► POST/PUT /api/expenses[/:id]
    List row ──deleteExpense(id)──► DELETE /api/expenses/:id ──► soft delete + audit

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/routes/expenses.py` | Create | Blueprint, 5 endpoints |
| `backend/routes/__init__.py` | Modify | Export `expenses_bp` |
| `backend/app.py` | Modify | Import + `register_blueprint(expenses_bp)` |
| `backend/tests/routes/test_expenses.py` | Create | CRUD, permissions, scope, summary, validation (isolation-safe fixture) |
| `frontend/src/pages/ExpensesPage.tsx` | Create | List, filters, stat cards, category badges |
| `frontend/src/components/ExpenseForm.tsx` | Create | Create/edit modal |
| `frontend/src/services/api.ts` | Modify | 5 expense methods |
| `frontend/src/types/index.ts` | Modify | Expense types |
| `frontend/src/App.tsx` | Modify | `/expenses` route (admin+) |
| `frontend/src/components/Layout.tsx` | Modify | Nav "Egresos" + `TrendingDown` icon |

## Interfaces / Contracts

Endpoints (all admin+): `GET /api/expenses`, `POST /api/expenses`, `GET /api/expenses/summary`, `PUT /api/expenses/:id`, `DELETE /api/expenses/:id`.

```ts
export type ExpenseCategory = 'payroll'|'supplies'|'services'|'rent'|'maintenance'|'other';

export interface Expense {
  id: string; category: ExpenseCategory; amountCents: number; description?: string|null;
  date: string; businessId: string; branchId?: string|null;
  registeredBy: string; registeredByName: string; createdAt: string;
  isDeleted?: boolean; deletedBy?: string; deletedAt?: string;
}

export interface ExpenseFilters {
  businessId?: string; branchId?: string; category?: ExpenseCategory|'';
  startDate?: string; endDate?: string; search?: string; page?: number; limit?: number;
}

export interface ExpenseSummary {
  today: number; week: number; month: number; byCategory: Record<ExpenseCategory, number>;
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Route unit | CRUD, validation (amountCents/category/date), soft-delete audit, scope, summary aggregation | pytest `test_expenses.py` with `prime_app_modules` autouse fixture (super_admin prime + patch call-sites services/routes/middleware) |
| Permission | cashier/trainer → 403 on all 5 endpoints | Same file, role matrix |
| Integration | list filters + pagination over scoped mock data | `make_client` factory per test |
| E2E | create → list → edit → delete → summary refresh | Manual smoke |

## Migration / Rollout

Additive only. The new `expenses` collection starts empty; no existing collection is mutated. Manual Firestore index creation is the only operational step. Rollback: remove `expenses.py`, unregister the blueprint, revert FE page/api/nav/route.

## Open Questions

None — scope resolved. Phase 2/3 (products/sales, cash consolidation, `cash_daily`) tracked separately.
