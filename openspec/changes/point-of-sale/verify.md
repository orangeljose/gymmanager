# Verification Report — point-of-sale

**Change**: point-of-sale
**Version**: N/A
**Mode**: Standard
**Date**: 2026-10-15
**Branch**: feature/product-inventory (clean working tree, 4 commits ahead of origin)

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 13 |
| Tasks complete | 13 |
| Tasks incomplete | 0 |

All tasks in `tasks.md` (1.1 → 5.1) are marked `[x]`. No incomplete core or cleanup tasks.

## Build & Tests Execution

**Build (frontend type-check)**: ✅ Passed
```text
$ npx tsc --noEmit
EXITCODE=0
```

**Tests (change scope)**: ✅ 98 passed / 0 failed / 0 skipped
```text
$ python -m pytest tests/routes/test_sales.py tests/routes/test_products.py -v
============================== 98 passed, 98 warnings in 4.62s ==============================
```

**Tests (full suite)**: ✅ 540 passed / ❌ 18 failed (all pre-existing baseline, none in this change)
```text
$ python -m pytest -q
18 failed, 540 passed, 374 warnings in 14.97s
```
The 18 failures are confined to `test_client.py`, `test_plans.py`, `test_users.py`, `test_dashboard.py` — files NOT touched by this change (verified via `git diff origin/feature/product-inventory...HEAD`). They match the stated baseline (~18). No new failures introduced by point-of-sale.

**Coverage**: ➖ Not available (no coverage run requested)

---

## Spec Compliance Matrix

### point-of-sale/spec.md

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Sale Data Model | Document shape (totalCents = Σ subtotals) | `test_sales.py > test_multi_item_checkout_201_and_decrements_stock` | ⚠️ PARTIAL — invariant fully asserted; not every model field asserted |
| Create Sale | Multi-item checkout 201 + per-item decrement | `test_sales.py > test_multi_item_checkout_201_and_decrements_stock` | ✅ COMPLIANT |
| Create Sale | Oversell rejects whole sale (400, no writes) | `test_sales.py > test_oversell_rejects_whole_sale_400_no_writes` | ✅ COMPLIANT |
| Create Sale | Forbidden role (trainer POST → 403) | `test_sales.py > test_trainer_cannot_create_sale_403` | ✅ COMPLIANT |
| List Sales | List with date range + meta | `test_sales.py > test_list_filters_by_date_range_and_client` | ✅ COMPLIANT |
| Sale Detail | Receipt detail 200 (404 missing / 403 out-of-scope) | `test_sales.py > test_get_sale_200` (+`_404`, `_403`) | ✅ COMPLIANT |
| Receipt Number | Sequential (count=4 → `-005`) | `test_sales.py > test_receipt_sequential_count_plus_one` | ✅ COMPLIANT |
| Optional Client | Walk-in sale (null client) | `test_sales.py > test_walk_in_sale_null_client` | ✅ COMPLIANT |
| Stock Never Negative | Guard on boundary (stockQty:2, qty:2 → 0) | `test_sales.py > test_boundary_stock_never_negative` | ✅ COMPLIANT |
| Point of Sale Permissions | GET 200 all roles / POST 403 trainer | `test_sales.py > test_all_roles_can_list_and_detail_200[*]` + `test_trainer_cannot_create_sale_403` | ✅ COMPLIANT |
| Composite Index | Index documented | `openspec/changes/point-of-sale/firestore-indexes.md` (static) | ✅ COMPLIANT (static) |

### product-inventory/spec.md

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Register Movement | Purchase increases stock + updates cost | `test_products.py > test_purchase_increases_stock_and_updates_cost` | ✅ COMPLIANT |
| Register Movement | Cashier cannot replenish (403) | `test_products.py > test_cashier_cannot_purchase_403` | ✅ COMPLIANT |
| Register Movement | Sale type rejected (400) | `test_products.py > test_sale_type_rejected_400` | ✅ COMPLIANT |
| Product Permissions | Trainer POST/DELETE → 403 | `test_products.py > test_non_admin_catalog_writes_403[*]` | ✅ COMPLIANT |
| Product Report | Reads sales (income) + purchases (outflow), net | `test_products.py > test_report_reads_sales_and_purchases_two_queries` | ✅ COMPLIANT |
| Sales Do Not Create Movements | Sale not a movement | `test_sales.py > test_multi_item_checkout_201_and_decrements_stock` (asserts no `product_movements` write) | ✅ COMPLIANT |

**Compliance summary**: 16/17 scenarios compliant · 1 partial (document-shape field exhaustiveness; core invariant covered).

---

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| `sales_bp` blueprint registered | ✅ Implemented | `routes/__init__.py` import+`__all__`; `app.py` import + `register_blueprint(sales_bp)` |
| POST /api/sales cashier+ with stock guard | ✅ Implemented | validate-all-first; insufficient stock → 400 naming product, no writes; non-atomic decrement documented |
| V- receipt numbering (count+1, timestamp fallback) | ✅ Implemented | `_generate_receipt_number` mirrors PaymentService |
| GET /api/sales list + detail | ✅ Implemented | date range + clientName + branch scope + pagination; 404/403 on detail |
| `register_movement` purchase-only (admin+) | ✅ Implemented | `MOVEMENT_TYPES = ['purchase']`; `@require_role(ADMIN_ROLES)`; `type:'sale'` → 400 |
| products report reads sales + purchases | ✅ Implemented | two scoped queries + Python aggregation; `net = sales - purchases` |
| FE PointOfSalePage (grid+search+cart+checkout+receipt) | ✅ Implemented | `/pos` route cashier+; optional client; account-required methods |
| Mercancía relabel + Reponer | ✅ Implemented | ProductsPage "Mercancía", Reponer button admin+; ProductMovementModal purchase-only "Reponer" |
| ProductReportPage updated | ✅ Implemented | "Reporte de Mercancía", sales vs purchases chart |
| Nav swap (Caja "Productos"→/pos; Admin "Mercancía"→/products) | ✅ Implemented | Layout.tsx updated |
| Composite index documented | ✅ Implemented | `firestore-indexes.md` + `_index_error_response` in sales.py |
| `MovementType` narrowed to `'purchase'` (FE) | ✅ Implemented | `types/index.ts` line 642 |

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| New `sales` collection + `sales_bp` | ✅ Yes | mirrors products.py/PaymentService |
| Receipt `count_firestore('sales', businessId)+1`, timestamp fallback | ✅ Yes | ceiling/timestamp fallback present |
| validate-all-first + non-atomic decrement | ✅ Yes | documented in code + design |
| Report = two scoped queries + Python aggregation | ✅ Yes | exactly two queries (sales + product_movements) |
| Movement endpoint `@require_role(ADMIN_ROLES)`, type fixed to `purchase` | ✅ Yes | `MOVEMENT_TYPES=['purchase']` |
| Nav: Caja "Productos"→/pos; Administración "Mercancía"→/products | ✅ Yes | implemented, but see WARNING-1 (branch_admin nav gap) |

---

## Issues Found

**CRITICAL**: None

**WARNING**
1. **branch_admin loses nav access to Mercancía management.** The spec authorizes `branch_admin` to create/update/delete products and Reponer (product-inventory spec "Product Permissions"), but "Mercancía" now lives under the "Administración" nav group, which is gated `roles: ['super_admin', 'admin']` (Layout.tsx line 80). `branch_admin` therefore has no nav path to `/products` (the route itself remains directly reachable and API read-all still works). This is a real UX gap for an authorized role — the design's own Open Question ("keep /products readable by all vs admin+") was resolved to read-all-API but the nav placement under a super_admin/admin-only parent was not reconciled with `branch_admin` write permissions. Recommend either adding "Mercancía" to a branch_admin-visible nav section or relaxing the Administración gate (at least for the Mercancía entry).

**SUGGESTION**
1. **Receipt fallback branch untested.** `_generate_receipt_number`'s timestamp fallback (`V-YYYYMMDD-HHMMSSffffff`) has no covering test — no test forces `count_firestore` to raise. Only the primary `V-\d{8}-\d{3}` format is asserted.
2. **Spec scenario wording drift.** product-inventory spec "Sale type rejected" says `GIVEN an authorized cashier`, but the movement endpoint is now admin+ only (cashier → 403 before type validation). The test correctly uses `admin`. The `GIVEN` clause should read "an authorized admin".
3. **Timezone inconsistency in receipt fallback.** `_generate_receipt_number` uses `datetime.now(timezone.utc)` for the count path but naive `datetime.now()` in the fallback path.
4. **Unlisted file change.** `frontend/src/pages/ProductDetailPage.tsx` was modified (Reponer relabel + movement-type handling) but is not listed in design.md "File Changes". Minor design-doc drift.

---

## Verdict

**PASS WITH WARNINGS**

Backend and frontend implementation match the specs, design, and tasks; all 98 change-scope tests pass, type-check is clean, and the 18 full-suite failures are confirmed pre-existing baseline (unrelated files). One authorized-role nav gap (branch_admin → Mercancía) and minor spec/doc/test polish remain, none of which are CRITICAL.
