# Proposal: Phase 2 — Products, Stock & Sales/Purchases

## Intent

Gyms resell proteins/merch with no stock ledger, so product income is invisible. Adds `products` + `product_movements`: cashiers register sales (IN), admins purchases (OUT); feeds the Phase 3 cash report.

## Scope

### In Scope
- `products` CRUD (admin+ write; all read stock)
- `product_movements`: immutable purchase/sale records with stock effect
- Sale (cashier+) / purchase (admin+) + stock guard
- `ProductsPage` (stat cards, stock badges, filters), forms, movement modal, detail
- Nav "Caja" (Egresos + Productos); index `product_movements (businessId, date)`

### Out of Scope
- Cash report + `cash_daily` (Phase 3); suppliers, purchase orders, currency conversion

## Capabilities

### New Capabilities
- `product-inventory`: products with cost/sale price + stock; immutable movements; low-stock summary

### Modified Capabilities
- None

## Approach

Mirror `expenses.py`: `products_bp` (`/api/products`), `_scope_ids()`, businessId-only equality, Python filtering, `_index_error_response`, soft-delete + audit. Movement = read stock → check → write movement → update `stockQty`.

### Confirmed decisions
1. Stock can't go negative → 400 "Stock insuficiente".
2. Movements immutable (no edit/delete).
3. Sale uses `salePriceCents` (optional override); purchase writes last `costPriceCents`.
4. No counters now; category enum `supplement|drink|apparel|accessory|other`; `lowStockThreshold` default 5.

### Flags — resolve in design
- **Purchases ≠ expenses**: a money-OUT purchase MUST NOT write an `expenses` doc (double-count).
- **Initial stock**: `stockQty>0` auto-creates an initial `purchase` movement, OR force `stockQty=0`.
- **Product delete** = soft delete (`isActive:false`).
- **Negative-stock guard is only as strong as atomicity** — concurrent sales can oversell.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/routes/products.py` + registration (`__init__.py`, `app.py`) | New | CRUD, movements, summary |
| `backend/tests/routes/test_products.py` | New | CRUD, stock guard, perms, scope |
| `frontend/src/pages/ProductsPage.tsx`, `ProductDetailPage.tsx` | New | List + detail/history |
| `frontend/src/components/ProductForm.tsx`, `ProductMovementModal.tsx` | New | Create/edit + movement |
| `services/api.ts`, `types/index.ts`, `Layout.tsx`, `App.tsx` | Modified | API + types + nav + routes |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Missing composite index | High | Document; `_index_error_response` |
| Oversell under concurrency | Med | Document; transaction later |
| Purchase double-counted | Med | Purchases only in movements |
| Cashier over-permission | Low | `require_role` split + tests |

## Rollback Plan

Additive only. Remove `products.py`, unregister blueprint, revert FE pieces. Collections dormant; nothing else mutated.

## Dependencies

- Manual index `product_movements (businessId, date)`; `products (businessId)` automatic.
- Base: `feature/cash-expenses` (Phase 1).

## Success Criteria

- [ ] Product CRUD + movements scoped, no full scan
- [ ] Cashier sells; purchase by cashier → 403 (tests); `qty > stockQty` → 400 "Stock insuficiente"
- [ ] Each movement updates `stockQty`; summary value + low-stock from one query
