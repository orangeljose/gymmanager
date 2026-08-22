# client-management Specification

## Purpose

Client lifecycle management including soft deletion of clients with payments preserved (Option A). Deleted clients disappear from operational views (list, detail, solvency, dashboard, quick-pay) while their payments remain in income reports and historical records for financial accuracy.

## Requirements

### Requirement: Delete Client Endpoint

The system MUST provide `DELETE /api/clients/:clientId` that soft-deletes the client by setting `isDeleted: true`. The endpoint MUST NOT hard-delete the document and MUST NOT modify any of the client's payment documents.

#### Scenario: Successful soft delete

- GIVEN an authorized user and an existing non-deleted client
- WHEN they send DELETE `/api/clients/:clientId`
- THEN the client SHALL be marked `isDeleted: true` and the endpoint SHALL return 200

#### Scenario: Client not found

- GIVEN a `clientId` that does not exist or is already soft-deleted
- WHEN DELETE `/api/clients/:clientId` is sent
- THEN the system SHALL return 404 without modifying anything

### Requirement: Client Deletion Authorization

Deletion MUST be restricted by role and branch. `super_admin` and `admin` MAY delete any client; `branch_admin` MAY delete only clients in their own branch; `cashier` and `trainer` MUST NOT delete clients.

| Role | Own-branch client | Cross-branch client |
|------|-------------------|---------------------|
| super_admin | 200 | 200 |
| admin | 200 | 200 |
| branch_admin | 200 | 403 |
| cashier | 403 | 403 |
| trainer | 403 | 403 |

#### Scenario: branch_admin cross-branch denied

- GIVEN a `branch_admin` whose `branchId` differs from the client's `branchId`
- WHEN they send DELETE `/api/clients/:clientId`
- THEN the system SHALL return 403 and SHALL NOT modify the client

#### Scenario: cashier denied

- GIVEN a cashier-authenticated request
- WHEN they send DELETE `/api/clients/:clientId`
- THEN the system SHALL return 403

### Requirement: Soft Delete Preserves Payments

Client deletion MUST be a soft delete: the client document SHALL set `isDeleted: true` and ALL payment documents of that client SHALL remain unmodified. Income reports, receipts, and dashboard `topPayingClients` MUST continue to include the deleted client's payments.

#### Scenario: Payments untouched

- GIVEN a client with 5 payments
- WHEN the client is soft-deleted
- THEN all 5 payment documents SHALL remain unchanged with their original fields intact

### Requirement: Deleted Client Exclusion from Client Queries

All operational client queries MUST exclude soft-deleted clients: `GET /api/clients` (list), `GET /api/clients/:id` (detail), and `GET /api/reports/solvency`. A client WITHOUT an `isDeleted` field MUST be treated as not deleted.

#### Scenario: List excludes deleted

- GIVEN 10 clients of which 2 are soft-deleted
- WHEN `GET /api/clients` is requested
- THEN the response SHALL contain only the 8 non-deleted clients

#### Scenario: Detail returns 404 for deleted

- GIVEN a soft-deleted client
- WHEN `GET /api/clients/:id` is requested for it
- THEN the system SHALL return 404

#### Scenario: Solvency excludes deleted

- GIVEN a soft-deleted client with an expired membership
- WHEN `GET /api/reports/solvency` is requested
- THEN the deleted client SHALL NOT appear in the response

#### Scenario: Legacy client without field

- GIVEN a legacy client lacking an `isDeleted` field
- WHEN any operational client query runs
- THEN the client SHALL be included

### Requirement: Backfill isDeleted

The system SHOULD backfill `isDeleted: false` on existing client documents lacking the field. The backfill MUST be idempotent.

#### Scenario: Backfill is idempotent

- GIVEN legacy clients without an `isDeleted` field
- WHEN the backfill runs
- THEN each legacy client SHALL gain `isDeleted: false` and a second run SHALL change nothing

### Requirement: Client Deletion UI

`ClientDetailPage` MUST show a delete action visible only to `super_admin`, `admin`, and `branch_admin`. Deletion MUST require a confirmation modal; on success the UI MUST navigate away from the deleted client or refresh. `ClientsPage` MAY show a delete row action with the same confirmation flow.

#### Scenario: Authorized delete flow

- GIVEN an authorized user viewing a client detail page
- WHEN they click delete and confirm the modal
- THEN the client SHALL be deleted server-side and the UI SHALL navigate away or refresh

#### Scenario: Cashier sees no delete button

- GIVEN a cashier viewing a client detail page
- WHEN the page renders
- THEN no delete action SHALL be visible

#### Scenario: Cancel keeps client

- GIVEN the confirmation modal is open
- WHEN the user cancels
- THEN the client SHALL remain unchanged and no delete request SHALL be sent