# Verification Report

**Change**: cash-refinements (4 refinements to GymManager cash module)
**Version**: N/A (delta refinements, no version field)
**Mode**: Standard (strict_tdd disabled per testing-capabilities; no STRICT TDD instruction passed)
**Branch**: feature/product-inventory (ahead of origin by 6 commits, working tree clean)

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 6 |
| Tasks complete | 6 |
| Tasks incomplete | 0 |

Task list recovered from `sdd/cash-refinements/apply-progress` (Engram #121) — R1 backend, R1 frontend,
R2 (rename + chart removal), R3 (Suscripciones nav), R4 backend, R4 frontend. All marked complete.

> **Artifact note**: no separate `proposal.md` / `specs/` / `design.md` / `tasks.md` exist under
> `openspec/changes/cash-refinements/`. This is a refinement delta layered on top of the
> `cash-expenses` and `product-inventory` changes (which do carry full SDD artifacts). Verification
> therefore maps the launch checklist against the apply-progress report + source + tests.

## Build & Tests Execution

**Build (type-check)**: ✅ Passed
```text
frontend> npx tsc --noEmit
(exit 0, no diagnostics)
```

**Tests (feature)**: ✅ 120 passed / ❌ 0 failed / ⚠️ 0 skipped
```text
backend> python -m pytest backend/tests/routes/test_expenses.py backend/tests/routes/test_products.py -v
120 passed, 120 warnings in 6.84s
```

**Tests (full suite, regression check)**: ✅ No new failures
```text
backend> python -m pytest backend/tests -q
18 failed, 502 passed, 336 warnings in 11.22s
```
The 18 failures are exactly the known baseline set, all in unrelated modules
(`tests/models/test_client.py`, `tests/routes/test_plans.py`, `tests/routes/test_users.py`,
`tests/unit/test_dashboard.py`). `test_expenses.py` and `test_products.py` never fail. Passing count
502 matches the apply-progress claim; no regression.

**Coverage**: ➖ Not available (no coverage tooling configured/run).

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| R1 — expenses method | method + paymentAccountId stored on create | `test_expenses.py > TestCreateExpense::test_create_with_method_and_payment_account` | ✅ COMPLIANT |
| R1 — expenses method | default method = cash | `TestCreateExpense::test_create_default_method_cash` | ✅ COMPLIANT |
| R1 — expenses method | invalid method → 400 (create) | `TestCreateExpense::test_create_invalid_method_400` | ✅ COMPLIANT |
| R1 — expenses method | method + paymentAccountId on update | `TestUpdateAndDeleteExpense::test_update_method_and_payment_account` | ✅ COMPLIANT |
| R1 — movement method | sale method + paymentAccountId | `test_products.py > TestMovements::test_sale_with_method_and_payment_account` | ✅ COMPLIANT |
| R1 — movement method | purchase method + paymentAccountId | `TestMovements::test_purchase_with_method_and_payment_account` | ✅ COMPLIANT |
| R1 — movement method | default method = cash | `TestMovements::test_sale_default_method_cash` | ✅ COMPLIANT |
| R1 — movement method | invalid method → 400 | `TestMovements::test_invalid_method_400` | ✅ COMPLIANT |
| R4 — product report | splits sales/purchases, computes net + daily | `TestProductsReport::test_report_splits_sales_vs_purchases_and_daily` | ✅ COMPLIANT |
| R4 — product report | empty → zeroes | `TestProductsReport::test_report_empty_returns_zeroes` | ✅ COMPLIANT |
| R4 — product report | invalid date → 400 | `TestProductsReport::test_report_invalid_date_400` | ✅ COMPLIANT |
| R4 — product report | branch scoping | `TestProductsReport::test_report_branch_scoped_user_filters_own_branch` | ✅ COMPLIANT |
| R4 — product report | all READ_ROLES 200 / unauth 401 | `TestPermissions::test_all_roles_can_list_and_summary_200` + `test_unauth_returns_401` | ✅ COMPLIANT |

**Compliance summary**: 13/13 scenarios compliant (0 PARTIAL, 0 FAILING, 0 UNTESTED).

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| R1 expenses — method + paymentAccountId | ✅ Implemented | `expenses.py` create (L339-345, L369-370) and update (L443-451); reuses `PaymentModel.VALID_METHODS` (L43) |
| R1 expenses — invalid method 400 | ✅ Implemented | `create_expense` L340-341, `update_expense` L445-446 |
| R1 movements — method + paymentAccountId | ✅ Implemented | `products.py` `register_movement` L810-816, L860-861; initial-stock purchase writes `method:'cash'` (L544) |
| R1 movements — invalid method 400 | ✅ Implemented | `products.py` L811-812 |
| R2 — "Servicios" rename | ✅ Implemented | `Layout.tsx` L60 (`Servicios`); `ExpensesPage.tsx` title/subtitle/button/empty-states/toasts (L117-123, L196, L96, L127); `ExpenseForm.tsx` labels |
| R2 — chart removed | ✅ Implemented | `ExpensesPage.tsx` has no `recharts` import; L185 comment "By-category chart removed"; 3 stat cards retained (L105-109) |
| R3 — "Suscripciones" nav | ✅ Implemented | `Layout.tsx` L59: first Caja submenu item, `/payments/new`, roles `[super_admin, admin, branch_admin, cashier]`; route in `App.tsx` L139-145 with matching roles |
| R4 — GET /api/products/report | ✅ Implemented | `products.py` L318-412, declared before `/<product_id>` (L421); splits by type, `net = sales - purchases`, `daily` map sorted by date; READ_ROLES |
| R4 — ProductsPage "Reportes" tab | ✅ Implemented | `ProductsPage.tsx` tabs (L186-207), date range (L405-426), 3 cards ventas/compras/neto (L156-160, L429-441), recharts BarChart (L463-479) |
| Types | ✅ Implemented | `types/index.ts`: `Expense.method/paymentAccountId`, `ProductMovement.method/paymentAccountId`, `ProductReport` (sales/purchases/net/daily) |
| API client | ✅ Implemented | `api.ts` `getProductsReport` (L701-709) hits `/products/report` |

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Reuse `PaymentModel.VALID_METHODS` as single source of truth | ✅ Yes | Both `expenses.py` and `products.py` import it |
| Default method = `cash` on both expenses and movements | ✅ Yes | Backend + tests |
| `paymentAccountId` optional/nullable | ✅ Yes | Coerced to `str | None` in both routes |
| Method selector filtered to account-backed methods (zelle/pago_movil/binance) | ✅ Yes | `ExpenseForm` + `ProductMovementModal` via `usePaymentAccounts` |
| Report route declared before `/<product_id>` | ✅ Yes | `products.py` L318 vs L421; runtime tests prove `/report` resolves 200 (not 404) |
| Rename preserves collection/endpoint name `expenses` | ✅ Yes | No data migration; only labels changed |

## Issues Found

**CRITICAL**
- None.

**WARNING**
- **WARNING-01 — `cash-refinements` SDD artifacts (proposal/spec/design/tasks) not persisted to openspec.**
  Only `sdd/cash-refinements/apply-progress` exists in Engram. The launch checklist + apply-progress were
  used as the verification contract. Downstream `archive` may have nothing to sync. Not a code defect.

**SUGGESTION**
- **SUGGESTION-01 — `PUT /api/expenses/<id>` invalid method has no negative test.** The code validates it
  (`expenses.py` L443-447) and the positive path is covered (`test_update_method_and_payment_account`),
  but there is no `test_update_invalid_method_400` mirroring the create/movement negative tests.
- **SUGGESTION-02 — `api.getProductsReport` signature extended with a 4th optional `businessId`.**
  The instruction listed `(startDate, endDate, branchId)`. Adding `businessId` mirrors
  `getIncomeDailyReport` and correctly scopes super_admin reports; harmless but a documented deviation.
- **SUGGESTION-03 — initial-stock purchase movement hardcodes `method:'cash'`.** Intentional field
  consistency for `create_product`; noted as a deviation from the sale/purchase-only instruction.

## Verdict

**PASS WITH WARNINGS**

All six verification targets are satisfied with runtime proof: method + paymentAccountId are stored and
invalid methods return 400 on expenses and product movements; "Servicios" rename is complete with the
by-category chart removed from ExpensesPage (no recharts import); "Suscripciones" points to `/payments/new`
with the correct roles; `GET /api/products/report` splits sales/purchases, computes net + daily, and is
declared before `/<product_id>`; and the ProductsPage "Reportes" tab renders date range, 3 cards, and a
bar chart. 120 feature tests pass, `tsc --noEmit` is clean, and the full suite shows only the pre-existing
18 baseline failures. The only warning is a process gap (missing cash-refinements SDD artifacts); the
suggestions are non-blocking coverage/docs niceties.
