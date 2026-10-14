# Tasks: Phase 2 — Products, Stock & Movements

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,900–2,300 (backend ~950, frontend ~1,100) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend) → PR 2 (FE foundation) → PR 3 (FE pages) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

```text
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High
```

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend routes + registration + tests | PR 1 | base = `feature/product-inventory`; tests ship with code |
| 2 | FE types + api + routes + nav | PR 2 | base = PR 1 branch (feature-branch-chain) |
| 3 | FE pages + modals | PR 3 | base = PR 2 branch; needs PR 2 types |

## Phase 1: Backend Foundation

- [x] 1.1 Create `backend/routes/products.py` with `products_bp` (`/api/products`), constants `PRODUCTS_COLLECTION`, `MOVEMENTS_COLLECTION`, `PRODUCT_CATEGORIES`, `ADMIN_ROLES`, `SALE_ROLES`.
- [x] 1.2 Port helpers from `expenses.py`: `_index_error_response`, `_error`, `_scope_ids`, `_is_active_product`, `_fetch_active_product`, `_product_scope_denied`.
- [x] 1.3 Export `products_bp` in `routes/__init__.py`; import + `register_blueprint` in `app.py`.

## Phase 2: Backend Endpoints

- [x] 2.1 `GET /api/products` (all roles): eq filter `businessId`; Python filter `category`/`lowStock`/`search`/`branchId`; exclude `isActive:false`; paginate + `meta`.
- [x] 2.2 `GET /api/products/summary` (all roles): ONE query; `totalProducts`, `totalStockValue=Σ stockQty×costPriceCents`, `lowStockCount`, `outOfStockCount`. Declare BEFORE `/<product_id>`.
- [x] 2.3 `POST /api/products` (`ADMIN_ROLES`): validate name/category/`costPriceCents≥0`/`salePriceCents>0`; threshold default 5; if `stockQty>0` write initial `purchase` movement (2nd write); 201.
- [x] 2.4 `PUT /api/products/<id>` (`ADMIN_ROLES`): 404 missing/inactive, 403 out of scope, validate changed fields, 200.
- [x] 2.5 `DELETE /api/products/<id>` (`ADMIN_ROLES`): soft delete `isActive:false` + `deletedBy`/`deletedAt`.
- [x] 2.6 `GET /api/products/<id>/movements` (all roles): 404 missing/inactive; `date` DESC, paginated.
- [x] 2.7 `POST /api/products/<id>/movement` (`@require_auth` only): in-body role check by `type`; sale→`SALE_ROLES`, `qty>0`, guard `qty≤stockQty` else 400 "Stock insuficiente", `unitPrice` defaults `salePriceCents`; purchase→`ADMIN_ROLES`, `unitPrice` required, `updateCostPrice` opt-in. Never touch `expenses`.

## Phase 3: Backend Tests

- [x] 3.1 Create `backend/tests/routes/test_products.py` with `reset_singleton`, `prime_app_modules` (super_admin prime), `make_client` patching `services.firebase_service`, `routes.products`, `middleware.auth_middleware`.
- [x] 3.2 Tests: CRUD validation, soft-delete audit, business/branch scope, list filters + `meta`, summary counters.
- [x] 3.3 Tests: sale 201 decreases stock / oversell 400 unchanged / purchase increases + cost / initial-stock movement / cashier purchase 403 / trainer write 403 / all-roles list 200 / missing movement endpoint 404–405.

## Phase 4: Frontend Foundation

- [x] 4.1 Add `Product`/`ProductMovement`/`ProductSummary` + filters/form types to `types/index.ts`.
- [x] 4.2 Add 8 methods to `services/api.ts` (getProducts, getProduct, getProductsSummary, getProductMovements, create/update/deleteProduct, registerMovement).
- [x] 4.3 Add `/products` + `/products/:id` routes in `App.tsx` (super_admin/admin/branch_admin/cashier/trainer).
- [x] 4.4 Refactor `Layout.tsx`: group Egresos + Productos under "Caja" (`Wallet` icon); register icon in `iconMap`.

## Phase 5: Frontend Pages

- [x] 5.1 `ProductsPage.tsx`: stat cards from summary, list + stock badges, category/lowStock/search filters, create/edit modal.
- [x] 5.2 `ProductDetailPage.tsx`: product info + movement history (date DESC).
- [x] 5.3 `ProductForm.tsx`: create/edit modal (name, category, cost, sale, initial stock, threshold).
- [x] 5.4 `ProductMovementModal.tsx`: sale (cashier+) / purchase (admin+) with role-gated type selector.

## Phase 6: Verification

- [x] 6.1 Run `pytest backend/tests/routes/test_products.py`; run FE `npm run build`.
- [x] 6.2 Document manual Firestore index `product_movements (businessId ASC, date ASC)`.
- [ ] 6.3 Manual smoke: create w/ stock → sell → purchase → detail history → summary refresh. (Requires a live Firebase project + running UI — deferred to verify by the human.)
