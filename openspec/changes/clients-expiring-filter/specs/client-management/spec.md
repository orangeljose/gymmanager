# Delta for client-management

## ADDED Requirements

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

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Solvency Report Feature

(Reason: dead code — the page is unreachable from the menu, no action in the app produces its input, and it consumes Firestore reads. Removed end-to-end: `SolvencyReportPage`, the `/reports/solvency` route, the ReportsPage nav link, `getSolvencyReport` in `api.ts`, the `SolvencyReport`/`ReportFilters` types, `GET /api/reports/solvency` in `reports.py`, and its tests. The system MUST NOT expose any user-facing link or route to `/reports/solvency`.)