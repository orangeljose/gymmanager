# Delta for Product Inventory

## MODIFIED Requirements

### Requirement: Register Movement

`POST /api/products/:id/movement` SHALL register a `purchase` movement ONLY (admin+). It MUST require integer `qty > 0` and `unitPriceCents` (cost); it MUST increase `stockQty`; when `updateCostPrice:true` it MUST set `product.costPriceCents` to `unitPriceCents`. Sales are NOT movements: they are recorded via `POST /api/sales`.

(Previously: accepted `type ∈ {sale, purchase}`; `sale` decreased stock for cashier+, `purchase` increased stock for admin+.)

#### Scenario: Purchase increases stock

- GIVEN an admin and a product with `stockQty: 0`
- WHEN POST `{type:"purchase", qty:10, unitPriceCents:1500, updateCostPrice:true}`
- THEN respond 201, `stockQty` becomes 10
- AND `product.costPriceCents` becomes 1500

#### Scenario: Cashier cannot replenish

- GIVEN a cashier
- WHEN POST `{type:"purchase", qty:1, unitPriceCents:100}`
- THEN respond 403

#### Scenario: Sale type rejected

- GIVEN an authorized cashier
- WHEN POST `{type:"sale", qty:1}`
- THEN respond 400 (sales use `POST /api/sales`)

### Requirement: Product Permissions

| Capability | Allowed roles |
|---|---|
| View products, summary, movements | every authenticated role |
| Create / update / delete product | `super_admin, admin, branch_admin` |
| Register `purchase` movement ("Reponer") | `super_admin, admin, branch_admin` |
| Sell products (POS) | `super_admin, admin, branch_admin, cashier` (see `point-of-sale`) |

(Previously: had a "Register `sale` movement" row for cashier+; sales now belong to `point-of-sale`.)

#### Scenario: Forbidden role

- GIVEN a trainer
- WHEN POST `/api/products` or DELETE `/api/products/:id`
- THEN respond 403

## ADDED Requirements

### Requirement: Product Report (Sales vs Purchases)

`GET /api/products/report` SHALL compute income from the `sales` collection and outflow from `product_movements` (purchases only). It SHALL return `{sales:{count,totalCents}, purchases:{count,totalCents}, net, daily:[{date,salesCents,purchasesCents}]}`.

#### Scenario: Report reads sales and purchases

- GIVEN sales and purchase movements in scope
- WHEN GET `/api/products/report`
- THEN `sales.totalCents` comes from `sales`, `purchases.totalCents` from purchase movements
- AND `net = sales - purchases`

### Requirement: Sales Do Not Create Movements

A sale MUST write a `sales` document and decrement stock directly; it MUST NOT create a `product_movements` document.

#### Scenario: Sale not a movement

- GIVEN a cashier completing a sale
- WHEN POST `/api/sales`
- THEN no `product_movements` document is created
