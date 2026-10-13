# Proposal: Cash Management (Income/Expenses + Product Stock)

## Intent

Gyms record membership income in `payments` but cannot register expenses (payroll, rent, services, repairs) or resell products (proteins, merch) with stock. Real profit is invisible. This adds expenses, product inventory, and a consolidated cash view that CONSOLIDATES with — never duplicates — the existing payments income.

## Scope

### In Scope
- `expenses` CRUD — simple income/expense without stock
- `products` + stock + `product_movements` (purchase increases stock, sale decreases)
- Consolidated cash summary/report: sales + membership payments − expenses = net
- `cash_daily` counters from day 1 (quota)
- Cashier registers sales; expenses/payroll restricted to admin+

### Out of Scope
- Multimoneda conversion and cash-register arqueo (currency field stored for future only)
- Offline sale sync, product category admin UI, supplier entities

## Capabilities

### New Capabilities
- `cash-expenses`: register/list/update/soft-delete expenses by category, scoped by business+branch
- `product-inventory`: products with cost/sale price and stock; purchase/sale movements
- `cash-reporting`: consolidated income (payments + sales) vs expenses, net, period breakdown

### Modified Capabilities
- None — `payments` is consumed read-only for income; no spec-level behavior changes

## Approach

Mirror `machines.py`: one blueprint per concern, `_scope_ids()` scoping, in-Python filtering over equality-scoped Firestore queries, `_index_error_response` helper, soft-delete + audit (`registeredBy/Name`). Reuse the `attendance.py` `*_daily` counter pattern (read-modify-write on doc id `{businessId}_{date}`) for `cash_daily`. Reuse `reports.py` income logic (businessId + `createdAt` range) for the payments leg of the cash report.

### Data Model

| Collection | Key fields |
|---|---|
| `expenses` | id, category(`payroll\|supplies\|services\|rent\|maintenance\|other`), amountCents, currency, description, date(YYYY-MM-DD), businessId, branchId, registeredBy/Name, createdAt, isDeleted |
| `products` | id, name, category, costPriceCents, salePriceCents, stockQty, currency, businessId, branchId, isActive, createdAt |
| `product_movements` | id, productId, productName(denorm), type(`purchase\|sale`), qty, unitPriceCents, totalAmountCents, currency, date, businessId, branchId, registeredBy/Name, createdAt |
| `cash_daily` | id=`{businessId}_{date}`, businessId, date, salesTotalCents, expensesTotalCents |

### Endpoints

| Endpoint | Roles |
|---|---|
| GET/POST/PUT/DELETE `/api/expenses` | GET/POST/PUT/DELETE admin+ (cashier denied) |
| GET `/api/products`, `/api/products/:id` | all roles (view stock) |
| POST/PUT/DELETE `/api/products` | admin+ |
| POST `/api/products/:id/movement` | sale: cashier+; purchase: admin+ |
| GET `/api/products/:id/movements` | all roles |
| GET `/api/cash/summary`, `/api/cash/report` | admin+ (cashier: summary MAY be allowed) |

### Phasing (recommended)

| Phase | Deliverable | Why first |
|---|---|---|
| 1 | Expenses module | Simplest, standalone, immediate value; no stock math |
| 2 | Products + stock + sales/purchases | Depends on movement pattern; larger surface |
| 3 | Consolidated cash report/summary | Depends on phases 1+2 + payments |

Ship Phase 1 alone if time-boxed; each phase is independently verifiable.

## Affected Areas

| Area | Impact |
|---|---|
| `backend/routes/expenses.py`, `products.py`, `cash.py` | New blueprints |
| `backend/routes/__init__.py`, `backend/app.py` | Register blueprints |
| `backend/tests/routes/test_*.py` | New route tests |
| `frontend/src/pages/ExpensesPage.tsx`, `ProductsPage.tsx`, `CashReportPage.tsx` | New pages |
| `frontend/src/services/api.ts`, `types/`, nav | New methods + nav entries |
| `openspec/specs/{cash-expenses,product-inventory,cash-reporting}/spec.md` | New specs |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Quota blowout from scans | Med | `cash_daily` counters day 1; scoped queries + composite indexes; no N+1 |
| Sales/purchases race on `stockQty` | Med | Accept read-modify-write (per attended counter tradeoff); document; optional transaction later |
| Income double-counted | Med | Sales read only `product_movements type=sale`; payments read `payments`; distinct sources, documented in report |
| Cashier over-permission | Low | Role table enforced in route decorators + tests |

## Rollback Plan

New collections and blueprints are additive. Revert = remove blueprint registration lines in `app.py`/`__init__.py` and delete new route files; FE pages/nav removed. No existing collection is mutated, so `payments`/`clients` remain untouched. Soft-deleted docs (`isDeleted`) preserve audit if partial rollback is needed.

## Dependencies

- Firestore composite indexes (manual console): `expenses (businessId, date)`, `product_movements (businessId, date)` + `(businessId, productId)`, `products (businessId)`.
- Existing `payments` collection as read-only income source.

## Success Criteria

- [ ] Expense/sale/purchase CRUD works scoped by business+branch with soft-delete + audit
- [ ] Cashier can sell; cannot create expenses/payroll (403 verified by tests)
- [ ] `cash_daily` updated on each sale/expense with 1 read + 1 write
- [ ] Cash report: total income = payments(period) + sales(period); net = income − expenses
- [ ] No full-collection scans; composite indexes documented
