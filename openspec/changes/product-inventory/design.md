# Design: Phase 2 — Products, Stock & Movements

## Technical Approach

Mirror `routes/expenses.py`: one `products_bp` over two collections (`products` + `product_movements`), business/branch scope from `g.current_user` via `_scope_ids()`, an equality filter on `businessId` only in Firestore, and all category/lowStock/search filtering plus summary aggregation in Python (10–50 docs/business). Soft delete (`isActive:false`) + audit and `_index_error_response` follow the expenses blueprint. Movements are append-only; purchases never touch `expenses`.

## Architecture Decisions

| # | Decision | Choice | Rationale / Alternatives |
|---|----------|--------|--------------------------|
| 1 | Blueprint & registration | New `routes/products.py` (`products_bp`, prefix `/api/products`); export in `routes/__init__.py` AND import+register in `app.py` | Matches machines/expenses (both sites). |
| 2 | Scope resolution | Reuse `_scope_ids()`: super_admin reads `businessId`/`branchId` query params; others from `g.current_user` | Single source of scope truth. |
| 3 | Query filtering | Firestore applies `businessId` equality only; `branchId`, `category`, `lowStock`, `search` filtered in Python | Low volume; avoids composite indexes on `products`. |
| 4 | Soft delete | `isActive:false` + `deletedBy`/`deletedAt` (NOT `isDeleted`) | Proposal flag; products use `isActive`. Helpers `_is_active_product`. |
| 5 | Movement role split | `POST .../movement` uses `@require_auth` only; role checked **in-body** by `type` (`sale`→SALE_ROLES incl. cashier; `purchase`→ADMIN_ROLES) | `@require_role` is static; a param-dependent role cannot be a decorator. Rejected: two endpoints (breaks the single-movement contract). |
| 6 | Stock update | read product → validate scope/active → (sale) guard `qty ≤ stockQty` → `create_document(movement)` → `update_document(products, id, {stockQty})` | Read-modify-write. **Non-atomic** (accepted): concurrent sales may oversell; transactions deferred. |
| 7 | Initial stock | On create with `stockQty>0`: `create_document(products)` then `create_document(product_movements, purchase)` — 2 writes | Auditable money-out trail; non-atomic (accepted). |
| 8 | Purchase cost update | `updateCostPrice:true` sets `product.costPriceCents` to movement `unitPriceCents` | Explicit opt-in; avoids accidental last-cost overwrite. |
| 9 | Purchases ≠ expenses | Movement endpoints never import/write `expenses` | Anti-double-count (spec requirement). |
| 10 | Summary | ONE scoped `products` query → Python compute `totalStockValue`, `lowStockCount`, `outOfStockCount` | No counters; single query. |
| 11 | Nav group | Restructure Layout into a **"Caja"** submenu group (Egresos + Productos), icon `Wallet` | DB/cash direction for Phase 3; alternative "Finanzas" rejected as less concrete. |
| 12 | Index | Document `product_movements (businessId ASC, date ASC)`; `products (businessId)` automatic | Manual creation on Spark; surfaces via `_index_error_response`. |

## Data Flow

    ProductsPage ─getProducts(filters)─► GET /api/products ──where(businessId)==──► Firestore products
         │                                                                              │
         └─getProductsSummary()─► GET /api/products/summary ◄── python aggregates ───────┘
    ProductForm ─createProduct/updateProduct─► POST/PUT /api/products[/:id]
                        └─(stockQty>0)─► create purchase movement (2nd write)
    MovementModal ─registerMovement(id,type,qty)─► POST /api/products/:id/movement
                        ├─ sale: guard qty≤stockQty → create movement → stockQty -= qty
                        └─ purchase: create movement → stockQty += qty (+cost update)
    ProductDetailPage ─getProductMovements(id)─► GET /api/products/:id/movements (date DESC)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/routes/products.py` | Create | Blueprint, products CRUD + movements + summary |
| `backend/routes/__init__.py` | Modify | Export `products_bp` |
| `backend/app.py` | Modify | Import + `register_blueprint(products_bp)` |
| `backend/tests/routes/test_products.py` | Create | CRUD, movements, stock guard, perms, initial stock, summary (isolation-safe `prime_app_modules`) |
| `frontend/src/pages/ProductsPage.tsx` | Create | List, stock badges, filters, stat cards |
| `frontend/src/pages/ProductDetailPage.tsx` | Create | Product info + movement history |
| `frontend/src/components/ProductForm.tsx` | Create | Create/edit modal (name, category, cost, sale, initial stock, threshold) |
| `frontend/src/components/ProductMovementModal.tsx` | Create | Sale (cashier+) / purchase (admin+) modal |
| `frontend/src/services/api.ts` | Modify | 8 product methods |
| `frontend/src/types/index.ts` | Modify | Product/movement types |
| `frontend/src/App.tsx` | Modify | `/products`, `/products/:id` routes |
| `frontend/src/components/Layout.tsx` | Modify | "Caja" nav group (Egresos + Productos) |

## Interfaces / Contracts

Endpoints: `GET /api/products`, `GET /api/products/summary`, `POST /api/products`, `PUT /api/products/:id`, `DELETE /api/products/:id`, `GET /api/products/:id/movements`, `POST /api/products/:id/movement`. `Routing order`: declare `/summary` before `/<product_id>` to avoid capture.

```ts
export type ProductCategory = 'supplement'|'drink'|'apparel'|'accessory'|'other';
export type MovementType = 'sale'|'purchase';

export interface Product {
  id: string; name: string; category: ProductCategory;
  costPriceCents: number; salePriceCents: number; stockQty: number;
  lowStockThreshold: number; businessId: string; branchId?: string|null;
  isActive: boolean; createdAt: string; registeredBy: string;
  deletedBy?: string; deletedAt?: string;
}
export interface ProductMovement {
  id: string; productId: string; type: MovementType; qty: number;
  unitPriceCents: number; totalCents: number; date: string;
  businessId: string; branchId?: string|null; registeredBy: string;
  registeredByName: string; createdAt: string; note?: string|null;
}
export interface ProductSummary {
  totalProducts: number; totalStockValue: number; lowStockCount: number; outOfStockCount: number;
}
```

Movement POST body: `{type:'sale'|'purchase', qty:number, unitPriceCents?:number, updateCostPrice?:boolean, date?:string, note?:string}`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Route unit | Product CRUD, validation, soft-delete audit, scope, initial-stock movement, summary, movement immutability | pytest `test_products.py` with `prime_app_modules` autouse fixture (super_admin prime + patch call-sites `services.firebase_service`, `routes.products`, `middleware.auth_middleware`) |
| Permission | cashier sale 201 / purchase 403; trainer admin-writes 403; all-roles list 200 | Role matrix param tests |
| Stock guard | `qty > stockQty` → 400 "Stock insuficiente", stock unchanged, no movement | Mock `get_document` with stock |
| Integration | list filters + pagination over scoped mock data; movements date DESC | `make_client` factory per test |
| E2E | create w/ stock → sell → purchase → detail history → summary refresh | Manual smoke |

## Migration / Rollout

Additive only. `products`/`product_movements` start empty; no existing collection mutates. Manual Firestore index `product_movements (businessId, date)` is the only operational step. Rollback: remove `products.py`, unregister blueprint, revert FE pages/api/nav/routes.

## Open Questions

- [ ] Concurrency oversell under simultaneous sales — accepted for Phase 2; revisit with Firestore transactions if volume grows.
- [ ] Whether Phase 3 cash report reads `product_movements` directly — deferred to Phase 3 design.
