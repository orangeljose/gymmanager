# Machine Maintenance Specification

## Purpose

Log maintenance and repair events for machines, transition machine lifecycle status on completion, and expose a quota-conscious summary so admins act before equipment breaks down.

## Requirements

### Requirement: Maintenance Data Model

Each record SHALL be a document in `machine_maintenance` with fields: `id`, `machineId`, `machineName` (denormalized), `type` (`preventive|repair`), `description`, `date` (YYYY-MM-DD), `costCents` (integer), `technician`, `status` (`scheduled|in_progress|completed`), `resolvedStatus` (`operational|out_of_service`), `businessId`, `branchId`, `registeredBy`, `registeredByName`, `createdAt`.

#### Scenario: Document shape on create

- GIVEN an authorized admin and an existing machine
- WHEN a maintenance record is added
- THEN the document MUST contain every model field
- AND `machineName` MUST equal the machine's current name

### Requirement: List Machine Maintenance

`GET /api/machines/:id/maintenance` SHALL return the maintenance history for one machine, ordered by `date` DESC, paginated (`page`, `limit`), scoped to the machine's business/branch. It MUST use a single scoped Firestore query (no N+1).

#### Scenario: Ordered paginated history

- GIVEN an authorized user and a machine with records
- WHEN GET `/api/machines/m1/maintenance?page=1&limit=20`
- THEN respond 200 with records ordered by `date` DESC
- AND `meta {total,page,limit,pages}`

#### Scenario: Cross-tenant machine

- GIVEN a machine in another business
- WHEN GET `/api/machines/m1/maintenance`
- THEN respond 403 or 404
- AND no records are returned

### Requirement: Add Maintenance Record

`POST /api/machines/:id/maintenance` SHALL add a record (admin+). The machine MUST exist and MUST NOT be soft-deleted, and MUST be in the caller's scope (`branchId` within scope). `type` SHALL be one of `preventive|repair`. It SHALL respond 201.

#### Scenario: Add record

- GIVEN an authorized admin and an existing non-deleted machine
- WHEN POST with valid `type`, `description`, `date`
- THEN respond 201 with the created record

#### Scenario: Unknown or deleted machine

- GIVEN an unknown or `isActive:false` machine id
- WHEN POST `/api/machines/m1/maintenance`
- THEN respond 404
- AND no record is created

#### Scenario: Invalid type

- GIVEN an authorized admin
- WHEN POST with `type:"inspection"`
- THEN respond 400 with an error message

### Requirement: Repair Completion Updates Machine Status

When a `repair` record is created or completed with `status:"completed"`, the system SHALL set the machine's `status` to the record's `resolvedStatus` (`operational` or `out_of_service`). A `repair` without a `resolvedStatus` MUST be rejected or left uninfluential.

#### Scenario: Completed repair sets status

- GIVEN a machine in `maintenance` and a repair with `resolvedStatus:"operational"`
- WHEN the repair is saved as `completed`
- THEN the machine's `status` SHALL become `operational`

#### Scenario: Repair keeps machine out of service

- GIVEN a machine with a repair `resolvedStatus:"out_of_service"`
- WHEN the repair is saved as `completed`
- THEN the machine's `status` SHALL become `out_of_service`

### Requirement: Preventive Maintenance Schedules Next Date

When a `preventive` record is created, the system SHALL set the machine's `nextMaintenanceDate` to the record `date` plus the maintenance interval (default 90 days, configurable). An explicit `nextMaintenanceDate` on the request MAY override the computed value. The `nextMaintenanceDate` MUST be stored as a date-only YYYY-MM-DD string.

#### Scenario: Preventive sets next date

- GIVEN a machine and a preventive record dated 2026-10-13
- WHEN the record is created
- THEN the machine's `nextMaintenanceDate` SHALL be 2027-01-11 (date + 90 days)

#### Scenario: Explicit override

- GIVEN a preventive record supplying `nextMaintenanceDate:"2026-11-01"`
- WHEN the record is created
- THEN the machine's `nextMaintenanceDate` SHALL be `2026-11-01`

### Requirement: Maintenance Summary

`GET /api/machines/summary` SHALL return: total machines, count by status (`operational`/`maintenance`/`out_of_service`), upcoming maintenance (machines with `nextMaintenanceDate` within the next 7 days), and the last 5 recent repairs. Machine counts SHALL be computed in memory from a single scoped `machines` query; recent repairs SHALL use a scoped, limited `machine_maintenance` query. Summary SHALL be readable by all roles.

#### Scenario: Summary counts

- GIVEN an admin with machines across statuses
- WHEN GET `/api/machines/summary`
- THEN respond 200 with `total`, `byStatus`, `upcomingMaintenance`, `recentRepairs`
- AND `recentRepairs` contains at most 5 records ordered by `date` DESC

#### Scenario: Cashier reads summary

- GIVEN an authenticated cashier
- WHEN GET `/api/machines/summary`
- THEN respond 200

#### Scenario: No upcoming maintenance

- GIVEN no machine has `nextMaintenanceDate` within 7 days
- WHEN GET `/api/machines/summary`
- THEN `upcomingMaintenance` SHALL be empty

### Requirement: Permissions

`POST /api/machines/:id/maintenance` SHALL be restricted to `super_admin`, `admin`, `branch_admin`. `GET /api/machines/:id/maintenance` and `GET /api/machines/summary` SHALL allow every role. Unauthorized MUST return 403; unauthenticated MUST return 401.

#### Scenario: Trainer cannot log maintenance

- GIVEN an authenticated trainer
- WHEN POST `/api/machines/m1/maintenance`
- THEN respond 403

#### Scenario: Trainer can read history

- GIVEN an authenticated trainer
- WHEN GET `/api/machines/m1/maintenance`
- THEN respond 200

### Requirement: Composite Index

Deployment SHALL require a manual Firebase-console composite index: `machine_maintenance (businessId ASC, machineId ASC)`. If a query raises an index error, the API SHOULD surface an actionable message.

#### Scenario: Missing index

- GIVEN the composite index has not been created
- WHEN a machine's history is queried
- THEN the API SHOULD respond 500 with a message referencing the missing index
