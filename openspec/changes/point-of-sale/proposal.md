# Proposal: Point of Sale (Cart Checkout) + Inventory Relocation

## Intent

Product sales are recorded per-product via `product_movements` (`type:'sale'`), so a multi-item checkout writes N movements and income/outflow share one ledger. Add cart-based checkout (`sales`) and split concerns: `sales` = income; `product_movements` = purchases only. Relocate inventory to Administración ("Mercancía"); Caja gets a dedicated POS.

## Scope

### In Scope
- New `sales` collection: cart checkout, `V-YYYYMMDD-XXX` receipt, optional client
- `POST /api/sales`, `GET /api/sales`, `GET /api/sales/:id` (cashier+); stock validate + decrement
- `product_movements` → purchase-only; `POST /api/products/:id/movement` = "Reponer" (admin+)
- Update `GET /api/products/report`: income from `sales`, outflow from `product_movements`
- FE: `PointOfSalePage` (`/pos`); `ProductsPage` → "Mercancía" (`/products`) with Reponer + low-stock; nav swap

### Out of Scope
- Sale edit/refund/void; Firestore transaction atomicity; supplier/P.O.; offline POS queue

## Capabilities

### New Capabilities
- `point-of-sale`: cart checkout, `sales` docs, V- receipt numbering, sale list/detail, income report

### Modified Capabilities
- `product-inventory`: movement endpoint purchase-only; permissions table (sale moves to `point-of-sale`); report reads `sales`

## Approach

Mirror `products.py` + `PaymentService`: `sales_bp` (`/api/sales`) reuses `_scope_ids()`, `count_firestore('sales', businessId)+1` → `V-YYYYMMDD-XXX` (fallback `V-YYYYMMDD-HHMMSSfff`), `PaymentModel.VALID_METHODS`, `paymentAccountId`. Create sale: read all products once → any insufficient stock → 400 with product name (no write) → else write sale + decrement each `stockQty` (non-atomic, documented). Report: two scoped queries (`sales` + `product_movements`), Python aggregation by date.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/routes/sales.py` (+`__init__.py`, `app.py`) | New | sales endpoints + receipt |
| `backend/routes/products.py` | Modified | movement purchase-only; report reads `sales` |
| `backend/tests/routes/test_sales.py` | New | checkout, stock guard, perms, receipt |
| `backend/tests/routes/test_products.py` | Modified | drop sale-movement cases |
| `frontend/src/pages/PointOfSalePage.tsx` | New | grid + cart + checkout + receipt |
| `frontend/src/pages/ProductsPage.tsx` | Modified | "Mercancía": CRUD + Reponer + low-stock |
| `frontend/src/App.tsx`, `Layout.tsx`, `services/api.ts`, `types` | Modified | `/pos` route; nav swap; API + types |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Non-atomic multi-item stock decrement | Med | Validate all first; document; transactions later |
| Receipt `V-` collision | Low | `count()+1` + timestamp fallback (mirror payments) |
| Breaking report/tests on `type:'sale'` removal | Med | Update tests; no prod data (code-only) |
| Missing `sales (businessId, date)` index | High | Document; `_index_error_response` |

## Rollback Plan

Additive + reversible: remove `sales.py`/`sales_bp`, revert `products.py` movement/report and FE nav/routes. `sales` collection dormant; `product_movements` (purchase-only) still valid. Restore sale-movement logic from git.

## Dependencies

- Manual index `sales (businessId ASC, date ASC)`; `sales (businessId)` automatic.
- Base: `feature/product-inventory`. `product-inventory` change still active (spec in `changes/product-inventory/specs/`, not merged to `openspec/specs/`) — order archive/merge accordingly.

## Success Criteria

- [ ] Cashier completes multi-item sale → `V-` receipt, stock decremented per item
- [ ] Oversell any item → 400 with product name; whole sale rejected, no partial write
- [ ] Cashier `POST .../movement` (purchase) → 403
- [ ] Report: income from `sales`, outflow from purchases; net correct
- [ ] Nav: Caja→"Productos"=`/pos`; Administración→"Mercancía"=`/products`
