# Tasks: Phase 1 — Expenses (Egresos)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,250–1,650 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 backend blueprint+tests → PR2 FE wiring → PR3 FE pages/form |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend `expenses.py` + registration + `test_expenses.py` | PR 1 | base `main`; self-contained, verifiable via pytest |
| 2 | FE types + api.ts + `/expenses` route + nav | PR 2 | base `main`; depends on PR 1 API shape |
| 3 | FE `ExpenseForm.tsx` + `ExpensesPage.tsx` | PR 3 | base `main`; depends on PR 2 |
| 4 | Document composite index + manual smoke | ops | no code PR |

## Phase 1: Foundation / Contracts

- [x] 1.1 `frontend/src/types/index.ts`: add `ExpenseCategory`, `Expense`, `ExpenseFilters`, `ExpenseFormData`, `ExpenseSummary`
- [x] 1.2 `backend/routes/expenses.py`: `expenses_bp` prefix `/api/expenses`; constants `EXPENSE_CATEGORIES`, `ADMIN_ROLES`; helpers `_scope_ids`, `_error`, `_index_error_response`, `_fetch_active_expense`
- [x] 1.3 Register: export `expenses_bp` in `backend/routes/__init__.py`; import + `register_blueprint` in `backend/app.py`

## Phase 2: Backend Endpoints (all `@require_role(ADMIN_ROLES)`)

- [x] 2.1 `GET /` — one scoped `businessId` query; Python filter `branchId`/`category`/`startDate`/`endDate`/`search`; exclude `isDeleted:true`; sort `date` DESC; paginate + `meta{total,page,limit,pages}`
- [x] 2.2 `POST /` — validate `category in EXPENSE_CATEGORIES`, `amountCents` int > 0 (bool excluded), `date` YYYY-MM-DD, branch scope; set `isDeleted:false`, `registeredBy/Name`, `createdAt`; 201
- [x] 2.3 `PUT /<id>` — 404 if missing/`isDeleted`; scope 403; validate changed fields; 200
- [x] 2.4 `DELETE /<id>` — 404 if missing/`isDeleted`; soft delete `{isDeleted:true, deletedBy, deletedAt}`; 200
- [x] 2.5 `GET /summary` — ONE scoped query; Python group today / rolling-7d / rolling-30d + `byCategory`; exclude `isDeleted`

## Phase 3: Backend Tests (`backend/tests/routes/test_expenses.py`)

- [x] 3.1 Port fixtures: `prime_app_modules` + `make_client`; patch `routes.expenses`, `middleware.auth_middleware`, `services.firebase_service`
- [x] 3.2 List: category + date-range filters, pagination, `isDeleted` excluded, cross-branch 403
- [x] 3.3 Create valid 201 / invalid 400 (`amountCents:0`, `category:travel`, `date:01-2026`); update 200; unknown/deleted 404
- [x] 3.4 Soft delete preserves fields + audit; subsequent list/summary exclude it
- [x] 3.5 Permissions matrix: cashier/trainer 403 on all 5 endpoints; unauth 401
- [x] 3.6 Summary: today/week/month totals + `byCategory` from one query
- [x] 3.7 Run `pytest backend/tests/routes/test_expenses.py` — green

## Phase 4: Frontend Wiring

- [x] 4.1 `frontend/src/services/api.ts`: `getExpenses`, `createExpense`, `updateExpense`, `deleteExpense`, `getExpensesSummary`
- [x] 4.2 `frontend/src/App.tsx`: `/expenses` route with `ProtectedRoute requiredRoles={super_admin,admin,branch_admin}`
- [x] 4.3 `frontend/src/components/Layout.tsx`: top-level "Egresos" (`TrendingDown`) after "Equipamiento"; register icon in `iconMap`

## Phase 5: Frontend Pages

- [x] 5.1 `frontend/src/components/ExpenseForm.tsx` — create/edit modal (category, amountCents, date, description)
- [x] 5.2 `frontend/src/pages/ExpensesPage.tsx` — Hoy/Semana/Mes stat cards, category badges, category + date filters, by-category chart (`recharts`), pagination, delete, open form
- [x] 5.3 Apply GoatGym theme; run `npm run build` (frontend)

## Phase 6: Ops & Verification

- [x] 6.1 Document composite index `expenses (businessId ASC, date ASC)` in `openspec/changes/cash-expenses/indexes.md`
- [ ] 6.2 Manual smoke (live Firebase): create → list → edit → delete → summary refresh
