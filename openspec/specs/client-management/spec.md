# client-management Specification

## Purpose

Client lifecycle management including soft deletion of clients with payments preserved (Option A). Deleted clients disappear from operational views (list, detail, dashboard, quick-pay) while their payments remain in income reports and historical records for financial accuracy.

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

All operational client queries MUST exclude soft-deleted clients: `GET /api/clients` (list) and `GET /api/clients/:id` (detail). A client WITHOUT an `isDeleted` field MUST be treated as not deleted.
(Previously: also covered `GET /api/reports/solvency`, which is removed by this change.)

#### Scenario: List excludes deleted

- GIVEN 10 clients of which 2 are soft-deleted
- WHEN `GET /api/clients` is requested
- THEN the response SHALL contain only the 8 non-deleted clients

#### Scenario: Detail returns 404 for deleted

- GIVEN a soft-deleted client
- WHEN `GET /api/clients/:id` is requested for it
- THEN the system SHALL return 404

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

### Requirement: Clients List expiringSoon Filter

`GET /api/clients` MUST accept `expiringSoon=true` and filter clients by `membershipEnd` within the inclusive range [now, now + 7 days], applied in the Firestore query (not in Python). The query MUST respect business scope and, when a branch scope applies, `branchId` equality. The filter MUST exclude soft-deleted clients and MUST include legacy clients lacking an `isDeleted` field.

`expiringSoon` MUST accept only `true` or `false`; any other value SHALL return 400. When `expiringSoon=true` is present, it takes PRECEDENCE over `status` (status is ignored, no 400) — the frontend dropdown is single-select and never sends both, and rejecting combined params would add complexity without user benefit. The `status` param MUST accept only `active` and `expired`; `suspended` SHALL return 400.

The filtered query requires a composite index on `clients`, created manually in the Firebase console (the index-error message provides the direct link):

| Index | Fields (order) | Supports |
|-------|----------------|----------|
| 1 | `businessId ASC, membershipEnd ASC` | businessId == + membershipEnd range |
| 2 | `businessId ASC, branchId ASC, membershipEnd ASC` | businessId == + branchId == + membershipEnd range |

#### Scenario: Returns only expiring clients

- GIVEN clients with membershipEnd in the past, in 3 days, and in 30 days
- WHEN `GET /api/clients?expiringSoon=true` is requested
- THEN the response SHALL contain only the client expiring in 3 days

#### Scenario: Inclusive window boundaries

- GIVEN clients with membershipEnd exactly at now and exactly at now + 7 days
- WHEN the expiringSoon query runs
- THEN both clients SHALL be included

#### Scenario: Branch scope respected

- GIVEN a branch_admin of branch Y with expiring clients in branches Y and Z
- WHEN they request `GET /api/clients?expiringSoon=true`
- THEN only branch Y clients SHALL be returned

#### Scenario: Pagination totals correct

- GIVEN 25 clients expiring within 7 days
- WHEN `GET /api/clients?expiringSoon=true&page=2&limit=10` is requested
- THEN `meta.total` SHALL be 25 and the response SHALL contain 10 clients

#### Scenario: Missing composite index

- GIVEN the composite index does not exist
- WHEN the expiringSoon query runs
- THEN the request SHALL fail with Firestore's index-error message and other client endpoints SHALL remain unaffected

#### Scenario: Rejected parameter values

- GIVEN `expiringSoon=yes` or `status=suspended`
- WHEN such a request is made
- THEN the system SHALL return 400

#### Scenario: expiringSoon precedence over status

- GIVEN a request with both `expiringSoon=true` and `status=active`
- WHEN the request is processed
- THEN the system SHALL apply the expiringSoon filter and SHALL NOT return 400 (status ignored)

### Requirement: Clients Status Filter Dropdown

The ClientsPage status dropdown MUST offer exactly: Todos (no filter), Activos (`status=active`), Vencidos (`status=expired`), and Próximos 7 días (`expiringSoon=true`). It MUST NOT offer "Suspendidos". The dropdown SHALL send at most one of `status` or `expiringSoon` per selection, passed through `useClients`/`fetchClients`.

#### Scenario: New option replaces Suspendidos

- GIVEN ClientsPage renders
- WHEN the status dropdown is opened
- THEN "Próximos 7 días" SHALL be present and "Suspendidos" SHALL NOT be present

#### Scenario: Selecting Próximos 7 días

- GIVEN a user on ClientsPage
- WHEN they select "Próximos 7 días"
- THEN a single `GET /api/clients` request SHALL be issued with `expiringSoon=true`

#### Scenario: Existing status filters unchanged

- GIVEN the user selects "Activos" or "Vencidos"
- WHEN the dropdown changes
- THEN the request SHALL carry `status=active` or `status=expired` respectively