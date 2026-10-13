# Delta for equipment-items

Capability `equipment-items` (quantity-based equipment, `kind='item'`) plus deltas on
`machine-inventory` and `machine-maintenance`. All behavior is additive; existing machine
behavior MUST remain unchanged.

## ADDED Requirements

### Requirement: Equipment Kind Field

Every `machines` document SHALL carry `kind` (`machine` | `item`). Documents lacking it MUST be
treated as `machine`. Item documents SHALL carry `quantity` (int ≥ 1, default 1) and `weightKg`
(number ≥ 0 or null). Legacy documents MUST NOT be reinterpreted.

#### Scenario: Legacy document defaults to machine

- GIVEN a document without `kind`
- WHEN it is read by list, summary, detail or maintenance
- THEN it MUST be treated as `machine`

#### Scenario: Item document shape

- GIVEN an admin
- WHEN POST `{kind:'item', name:'Mancuerna 10kg', category:'free_weights', quantity:8, weightKg:10}`
- THEN the stored document MUST contain `kind:'item'`, `quantity:8`, `weightKg:10`

### Requirement: Conditional Create Validation

`POST /api/machines` SHALL validate by `kind`. For `kind='machine'` it SHALL keep the existing
rules (non-empty `name`, `category` in the machine set, valid `status` and dates). For
`kind='item'` it MUST require a non-empty `name`, SHALL require `quantity` an integer ≥ 1
(default 1), SHALL accept optional `weightKg` a number ≥ 0, SHALL require `category` in the item
set (`free_weights` | `accessory` | `other`), and MUST NOT require `status` or maintenance
dates. An unknown `kind` MUST return 400. It SHALL respond 201.

#### Scenario: Item created with quantity

- GIVEN an admin
- WHEN POST a valid item payload
- THEN respond 201 AND the document stores `quantity` and `weightKg`

#### Scenario: Item quantity defaults to 1

- GIVEN an admin
- WHEN POST an item without `quantity`
- THEN the stored `quantity` MUST be 1

#### Scenario: Invalid item quantity

- GIVEN an admin
- WHEN POST `{kind:'item', quantity:0}` or `quantity:'x'`
- THEN respond 400 AND no document is created

#### Scenario: Invalid weightKg

- GIVEN an admin
- WHEN POST `{kind:'item', weightKg:-1}`
- THEN respond 400

#### Scenario: Unknown kind

- GIVEN an admin
- WHEN POST `{kind:'gadget'}`
- THEN respond 400

#### Scenario: Machine path unchanged

- GIVEN an admin
- WHEN POST a valid machine payload (no `kind` or `kind:'machine'`)
- THEN respond 201 with the existing machine defaults

### Requirement: Kind Filter on List

`GET /api/machines` SHALL accept an optional `kind` query param. When present it SHALL return only
documents whose `_kind` matches; when absent it SHALL return all kinds. Filtering MUST be in
Python from the single `businessId`-scoped query (no new index).

#### Scenario: Filter items

- GIVEN documents of both kinds
- WHEN GET `/api/machines?kind=item`
- THEN only `item` documents are returned

#### Scenario: Filter machines includes legacy

- GIVEN an item and a legacy document without `kind`
- WHEN GET `/api/machines?kind=machine`
- THEN the legacy document is returned and the item is not

#### Scenario: No filter returns all

- GIVEN no `kind` param
- WHEN GET `/api/machines`
- THEN both kinds are returned

### Requirement: Update Item Fields

`PUT /api/machines/:id` SHALL allow editing `quantity` and `weightKg` for `kind='item'` documents.
When provided, `quantity` MUST be an integer ≥ 1 and `weightKg` a number ≥ 0 or null; otherwise
respond 400. Existing machine update behavior MUST be unchanged.

#### Scenario: Edit item quantity

- GIVEN an existing item
- WHEN PUT `{quantity:12}`
- THEN respond 200 AND the document is updated

#### Scenario: Invalid quantity rejected

- GIVEN an existing item
- WHEN PUT `{quantity:-3}`
- THEN respond 400 AND no document is modified

## MODIFIED Requirements

### Requirement: Machines Data Model (machine-inventory)

Each document SHALL be in the `machines` collection with fields: `id`, `name`, `brand`, `model`,
`category` (`cardio|strength|functional|free_weights|accessory|other`), `purchaseDate`,
`warrantyUntil`, `businessId`, `branchId`, `status`, `nextMaintenanceDate`, `isActive`, PLUS
`kind` (`machine|item`, default `machine`), `quantity` (int, default 1) and `weightKg`
(number|null). (Previously: no `kind`/`quantity`/`weightKg`, category had no `accessory`.)

#### Scenario: Machine document shape on create

- GIVEN an authorized admin
- WHEN a machine is created
- THEN the document MUST contain every original model field
- AND `status` MUST default to `operational` and `isActive` to `true`

#### Scenario: Item document shape on create

- GIVEN an authorized admin
- WHEN an item is created
- THEN the document MUST contain `kind:'item'`, `quantity`, `weightKg`, `name`, `category`, `businessId`

### Requirement: List Machines (machine-inventory)

`GET /api/machines` SHALL list documents scoped by `businessId` and, when branch-scoped, by
`branchId`, accepting optional filters `category`, `status`, `kind`, `branchId`, `businessId` and
pagination. It MUST use a single scoped Firestore query with in-Python filtering (no N+1).
Soft-deleted documents (`isActive:false`) MUST be excluded; documents without `isActive` MUST be
treated as active. (Previously: no `kind` filter.)

#### Scenario: List with filters

- GIVEN an admin in business B
- WHEN GET `/api/machines?category=cardio&status=operational&page=1&limit=20`
- THEN respond 200 with a data array and `meta {total,page,limit,pages}`

#### Scenario: Kind filter restricts results

- GIVEN documents of both kinds
- WHEN GET `/api/machines?kind=item`
- THEN only items are returned

#### Scenario: Legacy document treated as active

- GIVEN a document lacking `isActive`
- WHEN the list is queried
- THEN that document SHALL be included

### Requirement: Maintenance Summary (machine-maintenance)

`GET /api/machines/summary` SHALL compute machine stats over `kind='machine'` documents only —
`total`, `byStatus`, `upcomingMaintenance`, `recentRepairs` — AND an additive `items` block:
`{ itemTypes: <count of item docs>, totalUnits: <sum of quantity> }`. Machine keys and their
types MUST stay stable. All counts MUST come from the single scoped `machines` query, split by
kind in Python. (Previously: `total` counted all active documents; no `items` block.)

#### Scenario: Summary split

- GIVEN 2 machines and 3 items with quantities 5, 2, 1
- WHEN GET `/api/machines/summary`
- THEN `total` is 2 and `byStatus` counts machines only
- AND `items` is `{itemTypes:3, totalUnits:8}`

#### Scenario: Item excluded from machine stats

- GIVEN an item with `nextMaintenanceDate` set
- WHEN GET `/api/machines/summary`
- THEN it MUST NOT appear in `upcomingMaintenance` nor in `byStatus`

#### Scenario: Items-only business

- GIVEN only items
- WHEN GET `/api/machines/summary`
- THEN `total` is 0, `byStatus` is all zero, and `items` is populated

### Requirement: Add Maintenance Record (machine-maintenance)

`POST /api/machines/:id/maintenance` SHALL reject a `kind='item'` target with 400 and the message
"Los accesorios no tienen mantenimiento". For `kind='machine'` targets the existing validation and
status transition MUST be unchanged. (Previously: no kind guard.)

#### Scenario: Maintenance rejected on item

- GIVEN an existing item
- WHEN POST `/api/machines/i1/maintenance`
- THEN respond 400 with a message mentioning "accesorios"
- AND no maintenance record is created

#### Scenario: Machine record still works

- GIVEN an existing machine
- WHEN POST valid maintenance
- THEN respond 201 and the status transition applies
