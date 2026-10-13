# Machine Inventory Specification

## Purpose

Register gym equipment per business/branch, expose its lifecycle status, and support scoped CRUD so staff can tell what machines exist and whether each is operational.

## Requirements

### Requirement: Machines Data Model

Each machine SHALL be a document in the `machines` collection with fields: `id`, `name`, `brand`, `model`, `category` (`cardio|strength|functional|other`), `purchaseDate` (YYYY-MM-DD), `warrantyUntil` (YYYY-MM-DD), `businessId`, `branchId`, `status` (`operational|maintenance|out_of_service`), `nextMaintenanceDate` (YYYY-MM-DD), `isActive`.

#### Scenario: Document shape on create

- GIVEN an authorized admin
- WHEN a machine is created
- THEN the document MUST contain every model field
- AND `status` MUST default to `operational` and `isActive` to `true`

### Requirement: List Machines

`GET /api/machines` SHALL list machines scoped by `businessId` and, when the caller is branch-scoped, by `branchId`. It SHALL accept optional filters `category`, `status`, `branchId`, `businessId` and pagination (`page`, `limit`). It MUST use a single scoped Firestore query with in-memory grouping/filtering (no N+1). Soft-deleted machines (`isActive:false`) MUST be excluded; documents without an `isActive` field MUST be treated as active via defensive in-Python filtering.

#### Scenario: List with filters

- GIVEN an admin in business B
- WHEN GET `/api/machines?category=cardio&status=operational&page=1&limit=20`
- THEN respond 200 with a data array and `meta {total,page,limit,pages}`
- AND only business B machines matching the filters are returned

#### Scenario: Legacy document treated as active

- GIVEN a machine lacking an `isActive` field
- WHEN the list is queried
- THEN that machine SHALL be included

#### Scenario: Deleted machine excluded

- GIVEN a machine with `isActive:false`
- WHEN the list is queried
- THEN it SHALL NOT appear in the results

### Requirement: Create Machine

`POST /api/machines` SHALL create a machine. `name` MUST be non-empty and `category` MUST be one of the allowed values. `branchId` MUST be within the caller's scope. It SHALL respond 201.

#### Scenario: Successful create

- GIVEN an admin in scope
- WHEN POST `/api/machines` with valid `name`, `category`, `branchId`
- THEN respond 201 with `{success:true, data:{...}}`

#### Scenario: Invalid input

- GIVEN an admin
- WHEN POST with an empty `name` or `category:"cardio2"`
- THEN respond 400 with an error message
- AND no document is created

#### Scenario: Cross-branch create denied

- GIVEN a branch_admin of branch A
- WHEN POST with `branchId:"B"`
- THEN respond 403
- AND no document is created

### Requirement: Update Machine

`PUT /api/machines/:id` SHALL update a machine's fields, including `status`. The machine MUST exist, MUST NOT be soft-deleted, and MUST be in the caller's scope; otherwise respond 404.

#### Scenario: Update status

- GIVEN an admin and an existing machine
- WHEN PUT `/api/machines/m1` `{status:"maintenance"}`
- THEN respond 200 with the updated machine

#### Scenario: Missing or deleted machine

- GIVEN an unknown or `isActive:false` machine id
- WHEN PUT `/api/machines/m1`
- THEN respond 404
- AND no document is modified

### Requirement: Soft Delete Machine

`DELETE /api/machines/:id` SHALL soft-delete the machine by setting `isActive:false`. It MUST NOT physically remove the document, and audit fields MUST be preserved.

#### Scenario: Soft delete preserves document

- GIVEN an admin and an existing machine
- WHEN DELETE `/api/machines/m1`
- THEN respond 200 and the document remains with `isActive:false`
- AND the document is not physically deleted

### Requirement: Permissions

`POST`, `PUT`, and `DELETE` SHALL be restricted to `super_admin`, `admin`, `branch_admin`. `GET` SHALL allow every role, including `cashier` and `trainer`. Unauthorized MUST return 403; unauthenticated MUST return 401.

| Endpoint | super_admin | admin | branch_admin | cashier | trainer |
|----------|-------------|-------|--------------|---------|---------|
| GET | 200 | 200 | 200 | 200 | 200 |
| POST/PUT/DELETE | 200 | 200 | 200 | 403 | 403 |

#### Scenario: Trainer cannot write

- GIVEN an authenticated trainer
- WHEN POST `/api/machines`
- THEN respond 403

#### Scenario: Cashier can read

- GIVEN an authenticated cashier
- WHEN GET `/api/machines`
- THEN respond 200

### Requirement: Composite Index

Deployment SHALL require manual Firebase-console composite indexes: `machines (businessId ASC, category ASC)` and `machines (businessId ASC, status ASC)`. If a query raises an index error, the API SHOULD surface an actionable message.

#### Scenario: Missing index

- GIVEN the composite index has not been created
- WHEN a filtered query runs
- THEN the API SHOULD respond 500 with a message referencing the missing index
