# Tasks: Point of Sale (Cart Checkout) + Inventory Relocation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1600–2000 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | `sales_bp` backend + tests (sales.py, __init__, app.py, test_sales.py) | PR 1 | base `feature/product-inventory`; additive, autonomous, pytest-green |
| 2 | products.py purchase-only + report reads sales + test_products.py | PR 2 | base PR 1; breaking (removes `type:'sale'`) |
| 3 | PointOfSalePage + api.ts + types + `/pos` route | PR 3 | base PR 1; FE POS deliverable, `npm run build` green |
| 4 | "Mercancía" relabel + Reponer + nav swap + movement modal | PR 4 | base PR 2; FE relabel, build green |

## Phase 1: Backend — Sales API

- [x] 1.1 Create `backend/routes/sales.py`: `sales_bp` (`/api/sales`) mirroring `products.py`; helpers `_scope_ids`, `_error`, `_index_error_response` (message → `sales (businessId ASC, date ASC)` index); receipt gen via `count_firestore('sales', businessId)+1` → `V-YYYYMMDD-XXX` (fallback `V-YYYYMMDD-HHMMSSffffff`), reusing `PaymentModel.VALID_METHODS`.
- [x] 1.2 Implement `POST /api/sales` (`@require_role(['super_admin','admin','branch_admin','cashier'])`): validate items (existing/active/in-scope product, int qty>0), read all products once, any `qty > stockQty` → 400 naming product with NO write; else create sale (totalCents = Σ subtotals) + decrement each `stockQty` (non-atomic).
- [x] 1.3 Implement `GET /api/sales` (list, `startDate`/`endDate`/`clientName`/`branchId`/`page`/`limit`, `{data,meta}`) and `GET /api/sales/:id` (404 missing / 403 out-of-scope).
- [x] 1.4 Register `sales_bp` in `backend/routes/__init__.py` (`import`+`__all__`) and `backend/app.py` (`import`+`register_blueprint`).

## Phase 2: Backend — Narrow products + report

- [x] 2.1 `backend/routes/products.py`: `register_movement` → `@require_role(ADMIN_ROLES)`, remove `'sale'` from `MOVEMENT_TYPES` and drop `SALE_ROLES`; `type` fixed to `purchase`; delete sale branch/oversell; purchase-only stock increase.
- [x] 2.2 `products.py` `/report`: income from `sales` query, outflow from `product_movements` (purchases only); two scoped queries + Python daily aggregation → `{sales,purchases,net,daily}`.

## Phase 3: Backend tests

- [x] 3.1 Create `backend/tests/routes/test_sales.py` (mock pattern from `test_products.py`): multi-item checkout 201 + per-item decrement; oversell 400 no write; receipt `V-\d{8}-\d{3}` + sequential (`count=4` → `-005`); list/detail + scope + perms (`prime_app_modules`+`make_client`); walk-in null client; boundary `stockQty:2`/qty:2 → 0.
- [x] 3.2 Update `backend/tests/routes/test_products.py`: remove `sale` movement cases; report asserts 2 queries (`sales` + `product_movements`) and correct net; add `type:'sale'` → 400 case; cashier purchase → 403 stays.

## Phase 4: Frontend — POS + nav

- [x] 4.1 `frontend/src/types/index.ts`: `MovementType` → `'purchase'`; add `Sale`, `SaleItem`, `SaleFilters`. `frontend/src/services/api.ts`: add `createSale`, `getSales`, `getSale`.
- [x] 4.2 Create `frontend/src/pages/PointOfSalePage.tsx`: product grid + search, cart (qty/edit/remove), optional client, payment method + account, checkout → receipt summary (reuse `PAYMENT_METHODS`/`formatDollars`).
- [x] 4.3 `frontend/src/App.tsx`: add `/pos` route (cashier+). `frontend/src/components/Layout.tsx`: Caja "Productos" → `/pos`; Administración "Mercancía" → `/products`.
- [x] 4.4 `ProductsPage.tsx`: relabel "Mercancía" + "Reponer" button (admin+, opens movement modal). `ProductMovementModal.tsx`: purchase-only ("Reponer", drop sale/`canSell`). `ProductReportPage.tsx`: label tweaks.

## Phase 5: Cleanup / Docs

- [x] 5.1 Document manual Firestore composite index `sales (businessId ASC, date ASC)` (proposal/design note or index doc).
