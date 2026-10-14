# Verification Report

**Change**: product-inventory (Phase 2 — Products, Stock & Movements)
**Version**: N/A (delta spec, no version field)
**Mode**: Standard (strict_tdd not configured; no STRICT TDD instruction passed)
**Re-verification**: after fix commit `1e149ab` (CRITICAL-01 + WARNING-02)

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 24 |
| Tasks complete | 23 |
| Tasks incomplete | 1 |

Incomplete: `6.3` manual smoke (create w/ stock → sell → purchase → detail history → summary) — explicitly deferred to a human with a live Firebase project + running UI.

## Build & Tests Execution

**Build (type-check)**: ✅ Passed
```text
frontend> npx tsc --noEmit
(exit 0, no diagnostics)
```

**Tests (feature)**: ✅ 64 passed / ❌ 0 failed / ⚠️ 0 skipped
```text
backend> python -m pytest backend/tests/routes/test_products.py -v
64 passed, 64 warnings in 2.96s
```
Delta vs previous verify: 54 → 64 tests (+10) from `TestGetProduct` (5 cases incl. 5-role
param = 9) and the added `GET /api/products/p1` unauthenticated case.

**Tests (full suite, regression check)**: ✅ No new failures
```text
backend> python -m pytest backend/tests -q
18 failed, 489 passed, 323 warnings in 10.68s
```
The 18 failures are exactly the known baseline set, all in unrelated modules
(`tests/routes/test_plans.py`, `tests/routes/test_users.py`, `tests/unit/test_dashboard.py`,
`tests/models/test_client.py`). `test_products.py` never fails. Passing count moved 479 → 489,
matching the +10 new product tests. No regression.

**Coverage**: ➖ Not available (no coverage tooling configured/run).

## Fix Verification

| Item | Evidence | Result |
|------|----------|--------|
| CRITICAL-01 — `GET /api/products/:id` exists | `products.py` `get_product` @ line 316, `@require_auth` + `@require_role(READ_ROLES)`; returns `{success, data}` | ✅ Resolved |
| — 200 for all roles | `TestGetProduct::test_get_product_200`, `test_all_roles_can_get_detail_200[super_admin/admin/branch_admin/cashier/trainer]` | ✅ Passing |
| — 404 missing | `test_get_product_missing_404` | ✅ Passing |
| — 404 soft-deleted | `test_get_product_soft_deleted_404` | ✅ Passing |
| — 403 out of scope | `test_get_product_out_of_scope_403` | ✅ Passing |
| — FE contract match | `api.ts getProduct(id)` → baseURL `http://localhost:5000/api` + `/products/${id}` = `/api/products/<id>`, matches backend rule | ✅ Aligned |
| WARNING-02 — movements meta assertion | `test_movements_history_date_desc` now asserts `body['meta'] == {'total':2,'page':1,'limit':20,'pages':1}` | ✅ Resolved |
| `/summary` route still resolves | `TestProductsSummary::test_summary_counters_one_query`, `test_summary_empty_returns_zeroes` pass; `/summary` declared line 249 before `/<product_id>` line 316; static rule wins over dynamic | ✅ Confirmed |
| No regressions | Full suite = baseline 18 failures only; tsc exit 0 | ✅ Confirmed |

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Product Data Model | Document shape on create | `test_products.py > TestCreateProduct::test_create_valid_201` | ✅ COMPLIANT |
| Product Data Model | Invalid category rejected | `TestCreateProduct::test_create_invalid_category_400` | ✅ COMPLIANT |
| List Products | List with filters | `TestListProducts::test_list_filters_category_and_lowstock_and_meta` | ✅ COMPLIANT |
| List Products | Soft-deleted excluded | `TestListProducts::test_list_excludes_deleted_and_sorts_by_name` | ✅ COMPLIANT |
| Create Product | Successful create | `TestCreateProduct::test_create_valid_201` | ✅ COMPLIANT |
| Create Product | Invalid input | `TestCreateProduct::test_create_invalid_input_400` (4 params) | ✅ COMPLIANT |
| Initial Stock Movement | Initial stock creates purchase | `TestCreateProduct::test_create_with_initial_stock_creates_purchase_movement` | ✅ COMPLIANT |
| Initial Stock Movement | No stock, no movement | `TestCreateProduct::test_create_without_stock_no_movement` | ✅ COMPLIANT |
| Update Product | Successful update | `TestUpdateAndDeleteProduct::test_update_fields_200` | ✅ COMPLIANT |
| Update Product | Missing or deleted | `test_update_missing_404`, `test_update_deleted_404` | ✅ COMPLIANT |
| Soft Delete Product | Soft delete preserves audit | `test_soft_delete_audit_preserved` + `test_deleted_product_excluded_from_list_and_summary` | ✅ COMPLIANT |
| List Movements | History ordered | `TestMovements::test_movements_history_date_desc` (200 + date DESC + `meta` asserted) | ✅ COMPLIANT |
| Register Movement | Sale decreases stock | `TestMovements::test_sale_decreases_stock_and_defaults_unit_price` | ✅ COMPLIANT |
| Register Movement | Oversell rejected | `TestMovements::test_oversell_rejected_400_stock_unchanged` | ✅ COMPLIANT |
| Register Movement | Purchase increases stock | `TestMovements::test_purchase_increases_stock_and_updates_cost` | ✅ COMPLIANT |
| Register Movement | Cashier cannot purchase | `TestMovements::test_cashier_cannot_purchase_403` | ✅ COMPLIANT |
| Movements Immutable | No mutation endpoint | `TestMovements::test_movements_are_immutable_405` | ✅ COMPLIANT |
| Product Summary | Summary computed | `TestProductsSummary::test_summary_counters_one_query` | ✅ COMPLIANT |
| Purchases Do Not Create Expenses | Purchase stays in movements | `TestMovements::test_purchase_does_not_write_expenses` | ✅ COMPLIANT |
| Product Permissions | Forbidden role | `TestPermissions::test_non_admin_catalog_writes_403` (trainer/cashier POST/PUT/DELETE) | ✅ COMPLIANT |
| Composite Index | Index documented | (documentation) `openspec/changes/product-inventory/firestore-indexes.md` | ✅ COMPLIANT (static) |
| Product Detail (FE integration) | GET /api/products/:id (task 4.2 `getProduct`) | `TestGetProduct::test_get_product_200/404/403` + `test_all_roles_can_get_detail_200` | ✅ COMPLIANT |

**Compliance summary**: 22/22 scenarios compliant (0 PARTIAL, 0 FAILING, 0 UNTESTED; one doc scenario verified statically).

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Product Data Model | ✅ Implemented | `create_product` builds full record; `isActive:true`; `lowStockThreshold` default 5; category enum enforced |
| Validation | ✅ Implemented | `name` non-empty, `category` enum, `costPriceCents >= 0`, `salePriceCents > 0`, `stockQty >= 0` via `_valid_int` |
| List Products | ✅ Implemented | Single `businessId` equality query; Python filtering; excludes `isActive:false`; paginated `meta` |
| Initial Stock | ✅ Implemented | `stockQty>0` → 2nd write to `product_movements` (`type:purchase`) |
| Soft Delete | ✅ Implemented | `isActive:false` + `deletedBy`/`deletedAt`; no hard delete |
| List Movements | ✅ Implemented | `date` DESC (tiebreak `createdAt` DESC), 404 if missing/inactive, `meta` pagination |
| Register Movement | ✅ Implemented | In-body role check by `type`; oversell → 400 "Stock insuficiente"; sale default price; purchase requires `unitPriceCents`; `updateCostPrice` opt-in |
| Movements Immutable | ✅ Implemented | No PUT/DELETE route → 405 |
| Product Summary | ✅ Implemented | ONE scoped query; Python compute of the four counters |
| Purchases ≠ Expenses | ✅ Implemented | `products.py` never imports/writes `expenses` |
| Permissions | ✅ Implemented | `ADMIN_ROLES` catalog writes; `SALE_ROLES` sale; `ADMIN_ROLES` purchase; `READ_ROLES` list/summary/movements/detail |
| Product Detail | ✅ Implemented | `get_product` @ READ_ROLES: 404 missing/soft-deleted (`_fetch_active_product`), 403 out of scope (`_product_scope_denied`), 200 `{success, data}` |
| Composite Index | ✅ Documented | `firestore-indexes.md` |
| Route order | ✅ Verified | `/summary` (line 249) before `/<product_id>` (line 316); static rule precedence + declaration order both hold |
| Frontend wiring | ✅ Complete | `ProductDetailPage` → `getProduct(id)` → `/api/products/:id` now resolves 200 |

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| 1. New `routes/products.py`, exported + registered (both sites) | ✅ Yes | |
| 2. Reuse `_scope_ids()` | ✅ Yes | |
| 3. Firestore `businessId` equality only + Python filtering | ✅ Yes | |
| 4. Soft delete `isActive` + audit (not `isDeleted`) | ✅ Yes | |
| 5. Movement role split in-body by `type` | ✅ Yes | |
| 6. Read-modify-write, non-atomic (accepted) | ✅ Yes | |
| 7. Initial stock = 2nd write | ✅ Yes | |
| 8. `updateCostPrice` opt-in | ✅ Yes | |
| 9. Purchases never touch `expenses` | ✅ Yes | |
| 10. Summary = one scoped query, Python compute | ✅ Yes | |
| 11. "Caja" nav group (`Wallet`) | ✅ Yes | |
| 12. Document composite index | ✅ Yes | |
| Design endpoint contract (7 endpoints, no `GET /:id`) | ⚠️ Stale | Code now exposes an 8th endpoint (`GET /api/products/:id`); design.md Interfaces/Contracts still lists 7. Code is correct per task 4.2/FE; the design doc should be updated (see WARNING-03). |

## Issues Found

**CRITICAL**
- None. CRITICAL-01 is resolved: `GET /api/products/<product_id>` exists (all READ_ROLES),
  returns 200/404/403 as required, and matches the frontend `getProduct` call path.

**WARNING**
- **WARNING-01 — Task 6.3 (manual E2E smoke) not executed.** Requires a live Firebase project + UI.
  Backend behavior is covered by route tests, but the create→sell→purchase→detail→summary flow has
  no real end-to-end run. Deferred cleanup task → WARNING.
- **WARNING-03 — Design doc stale (endpoint count).** `design.md` Interfaces/Contracts still lists
  7 endpoints and omits `GET /api/products/:id`, which now exists and is required by task 4.2/FE.
  Not a spec break, but the design should be updated so contract docs match shipped code
  (the commit that fixed CRITICAL-01 updated `products.py` and tests only).

**SUGGESTION**
- **SUGGESTION-01 — Concurrent oversell.** `POST /movement` is a documented non-atomic
  read-modify-write (design decision 6). Two simultaneous sales can oversell. Accepted for Phase 2;
  revisit with Firestore transactions if volume grows.
- **SUGGESTION-02 — Sale `unitPriceCents` permits 0.** Spec only requires an integer; a zero-priced
  sale is allowed. Confirm intended (e.g., giveaways) or require `> 0`.

## Verdict

**PASS WITH WARNINGS**
CRITICAL-01 and WARNING-02 are both resolved and proven by runtime tests: `GET /api/products/:id`
returns 200 (all roles) / 404 (missing or soft-deleted) / 403 (out of scope), the movements test now
asserts `meta`, `/summary` still resolves, the frontend call path aligns with the backend rule, 64/64
product tests pass, `tsc --noEmit` is clean, and the full suite shows only the pre-existing 18 baseline
failures. Remaining warnings are non-blocking: deferred manual smoke (6.3) and a stale design endpoint
contract (cosmetic doc drift).
