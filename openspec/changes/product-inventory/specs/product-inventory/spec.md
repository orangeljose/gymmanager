# Product Inventory Specification

## Purpose

Manage sellable gym products (supplements, drinks, merch) with cost/sale price and stock, plus an immutable purchase/sale movement ledger that adjusts stock. Feeds the Phase 3 cash report. Stock data is readable by all roles; writes are role-gated.

## Requirements

### Requirement: Product Data Model

Each product SHALL be a document in `products` with: `id`, `name` (non-empty), `category`, `costPriceCents` (integer ≥ 0), `salePriceCents` (integer > 0), `stockQty` (integer ≥ 0), `lowStockThreshold` (integer, default 5), `businessId`, `branchId`, `isActive` (default `true`), `createdAt`, `registeredBy`. `category` MUST be one of `supplement | drink | apparel | accessory | other`.

#### Scenario: Document shape on create

- GIVEN an authorized admin in scope
- WHEN a product is created
- THEN the document MUST contain every model field
- AND `isActive` MUST default to `true` and `lowStockThreshold` to 5

#### Scenario: Invalid category rejected

- GIVEN an admin
- WHEN a product is created with `category:"food"`
- THEN respond 400 and no document is created

### Requirement: List Products

`GET /api/products` SHALL list products scoped by `businessId` (and `branchId` when the caller is branch-scoped), excluding `isActive:false`. It MUST accept optional `category`, `lowStock` (boolean), `search` (name) and `page`/`limit`, and MUST use one scoped Firestore query with in-memory filtering — no full scan. It SHALL be readable by all authenticated roles.

#### Scenario: List with filters

- GIVEN an admin in business B
- WHEN GET `/api/products?category=drink&lowStock=true&page=1&limit=20`
- THEN respond 200 with `data[]` and `meta {total,page,limit,pages}`
- AND only active, in-scope, in-stock-low drink products are returned

#### Scenario: Soft-deleted excluded

- GIVEN a product with `isActive:false`
- WHEN the list is queried
- THEN it SHALL NOT appear in the results

### Requirement: Create Product

`POST /api/products` SHALL create a product (admin+). It MUST validate `name`, `category`, `costPriceCents ≥ 0` and `salePriceCents > 0`, and SHALL accept an optional `stockQty ≥ 0`. It SHALL respond 201.

#### Scenario: Successful create

- GIVEN an admin in scope
- WHEN POST with valid fields
- THEN respond 201 with `{success:true, data:{...}}`

#### Scenario: Invalid input

- GIVEN an admin
- WHEN POST missing `name`, or with `salePriceCents:0`, or `costPriceCents:-1`
- THEN respond 400 and no document is created

### Requirement: Initial Stock Movement

When product creation receives `stockQty > 0`, the system MUST auto-create an initial `purchase` movement (`qty=stockQty`, `unitPriceCents=costPriceCents`, `date`=creation date, same `businessId`/`branchId`, `registeredBy`=creator). When `stockQty` is 0 or absent, it MUST NOT create a movement.

#### Scenario: Initial stock creates purchase

- GIVEN an admin creating a product with `stockQty:10`, `costPriceCents:1500`
- WHEN the product is created
- THEN one `purchase` movement with `qty:10` and `unitPriceCents:1500` MUST exist

#### Scenario: No stock, no movement

- GIVEN an admin creating a product with `stockQty:0`
- WHEN the product is created
- THEN no movement SHALL be created

### Requirement: Update Product

`PUT /api/products/:id` SHALL update a product (admin+). It MUST respond 404 if the product does not exist or is soft-deleted, and 403 outside scope.

#### Scenario: Successful update

- GIVEN an existing product
- WHEN PUT with valid fields
- THEN respond 200 with the updated fields

#### Scenario: Missing or deleted

- GIVEN an unknown or soft-deleted id
- WHEN PUT `/api/products/:id`
- THEN respond 404

### Requirement: Soft Delete Product

`DELETE /api/products/:id` SHALL soft-delete by setting `isActive:false`, `deletedBy`, `deletedAt` (admin+). It SHALL respond 200.

#### Scenario: Soft delete preserves audit

- GIVEN an existing product
- WHEN DELETE `/api/products/:id`
- THEN the document MUST keep its data with `isActive:false` and audit fields
- AND subsequent list and summary calls MUST exclude it

### Requirement: List Movements

`GET /api/products/:id/movements` SHALL list a product's movements (all roles), ordered by `date` DESC, paginated. It MUST respond 404 if the product is missing/soft-deleted.

#### Scenario: History ordered

- GIVEN a product with dated movements
- WHEN GET `/api/products/:id/movements`
- THEN respond 200 with movements newest-first and `meta {total,page,limit,pages}`

### Requirement: Register Movement

`POST /api/products/:id/movement` SHALL register `type ∈ {sale, purchase}` with integer `qty > 0`.

For `type:"sale"` (cashier+): it MUST decrease `stockQty`; `unitPriceCents` defaults to `product.salePriceCents` (override allowed).
For `type:"purchase"` (admin+ ONLY): it MUST increase `stockQty`; `unitPriceCents` (cost) is required; when `updateCostPrice:true` it MUST set `product.costPriceCents` to this `unitPriceCents`.

#### Scenario: Sale decreases stock

- GIVEN a cashier and a product with `stockQty:10`
- WHEN POST `{type:"sale", qty:3}` (no unitPriceCents)
- THEN respond 201, `stockQty` becomes 7
- AND the movement `unitPriceCents` equals `product.salePriceCents`

#### Scenario: Oversell rejected

- GIVEN a product with `stockQty:2`
- WHEN POST `{type:"sale", qty:5}`
- THEN respond 400 with message "Stock insuficiente"
- AND no movement is created and `stockQty` is unchanged

#### Scenario: Purchase increases stock

- GIVEN an admin and a product with `stockQty:0`
- WHEN POST `{type:"purchase", qty:10, unitPriceCents:1500, updateCostPrice:true}`
- THEN respond 201, `stockQty` becomes 10
- AND `product.costPriceCents` becomes 1500

#### Scenario: Cashier cannot purchase

- GIVEN a cashier
- WHEN POST `{type:"purchase", qty:1, unitPriceCents:100}`
- THEN respond 403

### Requirement: Movements Immutable

Movements MUST be immutable. No update or delete endpoint SHALL exist for `product_movements`.

#### Scenario: No mutation endpoint

- GIVEN a registered movement
- WHEN PUT or DELETE `/api/products/:id/movement`
- THEN respond 404/405 — the movement is never altered

### Requirement: Product Summary

`GET /api/products/summary` SHALL return `{totalProducts, totalStockValue, lowStockCount, outOfStockCount}` derived from one scoped products query computed in Python, where `totalStockValue = Σ stockQty × costPriceCents`. It SHALL be readable by all authenticated roles.

#### Scenario: Summary computed

- GIVEN active products in scope with varying stock
- WHEN GET `/api/products/summary`
- THEN respond 200 with the four counters
- AND `lowStockCount` counts `stockQty > 0 AND stockQty ≤ lowStockThreshold`, `outOfStockCount` counts `stockQty = 0`

### Requirement: Purchases Do Not Create Expenses

A `purchase` movement is money OUT but MUST NOT create or mutate any `expenses` document. Purchases and expenses are separate sources to avoid double-counting.

#### Scenario: Purchase stays in movements

- GIVEN an admin registering a purchase
- WHEN the movement is created
- THEN no `expenses` document MUST be created or modified

### Requirement: Product Permissions

| Capability | Allowed roles |
|---|---|
| View products, summary, movements | every authenticated role |
| Create / update / delete product | `super_admin, admin, branch_admin` |
| Register `sale` movement | `super_admin, admin, branch_admin, cashier` |
| Register `purchase` movement | `super_admin, admin, branch_admin` |

#### Scenario: Forbidden role

- GIVEN a trainer
- WHEN POST `/api/products` or DELETE `/api/products/:id`
- THEN respond 403

### Requirement: Composite Index

A Firestore composite index `product_movements (businessId ASC, date ASC)` MUST be documented for manual creation; `products (businessId)` uses the automatic single-field index.

#### Scenario: Index documented

- GIVEN a new environment
- WHEN the change is deployed
- THEN the `product_movements (businessId, date)` index MUST be documented
