# Point of Sale Specification

## Purpose

Cart-based product checkout: multi-item sales into a `sales` ledger (income), with `V-YYYYMMDD-XXX` receipts, optional client, and per-item stock decrement. Sales are readable by all authenticated roles; creation is cashier+.

## Requirements

### Requirement: Sale Data Model

Each sale SHALL be a document in `sales` with: `id`, `receiptNumber` (`V-YYYYMMDD-XXX`), `date` (YYYY-MM-DD), `totalCents`, `method`, `paymentAccountId` (nullable), `clientId` (nullable), `clientName` (nullable), `items[]` of `{productId, productName, qty, unitPriceCents, subtotalCents}`, `businessId`, `branchId`, `registeredBy`, `registeredByName`, `createdAt`. `totalCents` MUST equal the sum of item `subtotalCents`.

#### Scenario: Document shape

- GIVEN an authorized cashier
- WHEN a sale is created
- THEN the document MUST contain every model field
- AND `totalCents` equals Σ item subtotals

### Requirement: Create Sale

`POST /api/sales` SHALL create a sale (cashier+). It MUST validate every item references an existing, active, in-scope product with integer `qty > 0`. If ANY item has insufficient stock, it SHALL respond 400 naming the product and write nothing. On success it MUST decrement each product `stockQty` by its item qty and respond 201.

#### Scenario: Multi-item checkout

- GIVEN products with sufficient stock
- WHEN POST a sale with several items
- THEN respond 201 with the sale
- AND each product `stockQty` is decremented by its qty

#### Scenario: Oversell rejects whole sale

- GIVEN one item with insufficient stock
- WHEN POST a sale including that item
- THEN respond 400 naming the product
- AND no sale is created and no stock changes

#### Scenario: Forbidden role

- GIVEN a trainer
- WHEN POST `/api/sales`
- THEN respond 403

### Requirement: List Sales

`GET /api/sales` SHALL list sales scoped by `businessId` (and `branchId` for branch-scoped callers), with optional `startDate`, `endDate`, `clientName` search, `page`/`limit`. It SHALL respond 200 with `data[]` and `meta`.

#### Scenario: List with date range

- GIVEN sales in scope
- WHEN GET `/api/sales?startDate=...&endDate=...`
- THEN respond 200 with matching sales and pagination meta

### Requirement: Sale Detail

`GET /api/sales/:id` SHALL return one sale (receipt). It MUST respond 404 if missing and 403 if out of scope.

#### Scenario: Receipt detail

- GIVEN an existing sale in scope
- WHEN GET `/api/sales/:id`
- THEN respond 200 with the full sale including items

### Requirement: Receipt Number

Each sale MUST receive a unique `receiptNumber` `V-YYYYMMDD-XXX` (sequence = business sale count + 1), falling back to `V-YYYYMMDD-HHMMSSffffff` when the count fails or reaches the ceiling.

#### Scenario: Sequential receipt

- GIVEN an existing sale count of 4 for the business
- WHEN a sale is created
- THEN `receiptNumber` is `V-YYYYMMDD-005`

### Requirement: Optional Client

A sale MAY be registered without a client (walk-in). `clientId` and `clientName` MUST be nullable.

#### Scenario: Walk-in sale

- GIVEN a cashier
- WHEN POST a sale without client
- THEN respond 201 with `clientId` and `clientName` null

### Requirement: Stock Never Negative

A sale MUST NOT leave any product `stockQty` below 0; oversell is rejected before any write.

#### Scenario: Guard on boundary

- GIVEN a product with `stockQty: 2`
- WHEN POST a sale of qty 2 for that product
- THEN `stockQty` becomes 0 (never negative)

### Requirement: Point of Sale Permissions

| Capability | Allowed roles |
|---|---|
| View / list / detail sales | every authenticated role |
| Create sale | `super_admin, admin, branch_admin, cashier` |

#### Scenario: Forbidden role

- GIVEN a trainer
- WHEN GET or POST `/api/sales`
- THEN GET responds 200 and POST responds 403

### Requirement: Composite Index

A Firestore composite index `sales (businessId ASC, date ASC)` MUST be documented for manual creation; `sales (businessId)` uses the automatic single-field index.

#### Scenario: Index documented

- GIVEN a new environment
- WHEN the change is deployed
- THEN the `sales (businessId, date)` index MUST be documented
