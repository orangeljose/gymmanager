# Attendance Specification

## Purpose

Record, query, and aggregate gym client check-ins with business/branch scoping, and expose a stable POST contract that a future QR/biometric scanner can call unchanged.

## Requirements

### Requirement: Attendance Data Model

Each check-in SHALL be a document in the `attendance` collection with fields: `id`, `clientId`, `clientName` (denormalized), `businessId`, `branchId`, `date` (YYYY-MM-DD string), `checkInAt` (ISO datetime), `method` (`manual|qr|biometric`), `registeredBy` (uid), `registeredByName`, `createdAt`.

#### Scenario: Document shape on check-in

- GIVEN a valid client and an authorized user
- WHEN a check-in is registered
- THEN the created document MUST contain every model field
- AND `clientName` MUST equal the client's current name

### Requirement: Register Check-In

`POST /api/attendance` SHALL accept `{clientId, method?, branchId?}`. The client MUST exist and belong to the caller's business (and branch when the user is branch-scoped). `method` SHALL default to `manual` and MUST be one of `manual|qr|biometric`. The system SHALL respond 201 for a new record.

#### Scenario: Successful manual check-in

- GIVEN a cashier in branch A and an active client in branch A
- WHEN POST /api/attendance `{clientId, method:"manual"}`
- THEN respond 201 with `{success:true, data:{...}}`
- AND a document is created with `date` = today

#### Scenario: Invalid method

- GIVEN an authorized user
- WHEN POST with `method:"nfc"`
- THEN respond 400 with an error code and message

#### Scenario: Unknown or cross-tenant client

- GIVEN an authorized user
- WHEN POST with a non-existent or other-business `clientId`
- THEN respond 404 (not found) or 403 (cross-business)
- AND no document is created

### Requirement: Idempotent Same-Day Check-In

The system SHALL allow at most one check-in per client per calendar day. If a check-in already exists for today, POST MUST NOT create a duplicate and SHALL return the existing record with HTTP 200 and `alreadyCheckedIn: true`.

#### Scenario: Second scan same day

- GIVEN a client already checked in today
- WHEN POST /api/attendance `{clientId}` is called again
- THEN respond 200 with the existing record
- AND `alreadyCheckedIn` equals true
- AND no new document is created

### Requirement: List Check-Ins

`GET /api/attendance` SHALL list check-ins filtered by `businessId` + `date`, with optional `branchId` and `clientId`, plus pagination (`page`, `limit`). It MUST use a single scoped Firestore query (no N+1) and SHALL return records plus a daily summary.

#### Scenario: List by date and branch

- GIVEN an admin in business B
- WHEN GET `/api/attendance?date=2026-10-05&branchId=A&page=1&limit=20`
- THEN respond 200 with a data array and `meta {total,page,limit,pages}`
- AND include a daily summary (total check-ins)
- AND only records for business B are returned

### Requirement: Client Attendance History

`GET /api/attendance/client/:clientId` SHALL return the client's history plus stats: total check-ins and current-month count. Access SHALL be scoped to the client's business/branch.

#### Scenario: Client history

- GIVEN a trainer in the client's branch
- WHEN GET `/api/attendance/client/c1`
- THEN respond 200 with history and stats `{total, thisMonth}`
- AND a cross-business client returns 403 or 404

### Requirement: Attendance Stats

`GET /api/attendance/stats` SHALL return today's count, this week, this month, top attendees, and a 7-day daily series. Aggregation SHALL be computed in memory from a single scoped query (no per-day queries).

#### Scenario: Stats for a branch

- GIVEN a branch_admin
- WHEN GET `/api/attendance/stats`
- THEN respond 200 with today/week/month counts, `topAttendees`, `last7Days`
- AND at most one scoped Firestore query is issued

### Requirement: Permissions

POST SHALL be restricted to `super_admin`, `admin`, `branch_admin`, `cashier`. All GET endpoints SHALL allow every role including `trainer`. Unauthorized access MUST return 403; unauthenticated MUST return 401.

#### Scenario: Trainer cannot register

- GIVEN an authenticated trainer
- WHEN POST `/api/attendance`
- THEN respond 403

#### Scenario: Trainer can read

- GIVEN an authenticated trainer
- WHEN GET `/api/attendance/stats`
- THEN respond 200

### Requirement: Composite Index

The deployment SHALL require a composite Firestore index on `attendance (businessId ASC, date ASC)`, created manually in the Firebase console. If a query raises an index error, the API SHOULD surface an actionable message.

#### Scenario: Missing index

- GIVEN the composite index has not been created
- WHEN a filtered query runs
- THEN the API SHOULD respond 500 with a message referencing the missing index

### Requirement: Scanner Contract (QR/Biometric)

The POST contract SHALL accept `clientId` and `method` ∈ `{qr, biometric}` unchanged, so a future scanner can call it without auth-flow or contract changes.

#### Scenario: QR scan

- GIVEN a QR resolves to a clientId
- WHEN POST `/api/attendance` `{clientId, method:"qr"}`
- THEN the record is created with `method:"qr"`
- AND no additional endpoint is required
