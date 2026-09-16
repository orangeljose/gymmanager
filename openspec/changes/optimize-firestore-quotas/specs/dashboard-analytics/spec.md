# Delta for dashboard-analytics

## ADDED Requirements

### Requirement: Income Reports Filtered in Firestore

The income endpoints (`/api/reports/income/daily`, `/api/reports/income/by-method`) MUST push filters into the Firestore query instead of reading all payments: `businessId == X` (user's businessId; the request's businessId for super_admin), `createdAt >= start`, `createdAt <= end`, and `branchId == Y` when a branch filter applies. The endpoints MUST keep the defensive Python filtering: payments with `isDeleted: true` MUST be excluded, and payments whose client is soft-deleted MUST be excluded. The Python-side date check MAY remain as a final in-memory filter.

The queries require composite indexes on `payments`, created manually in the Firebase console (the index-error message provides the direct link):

| Index | Fields (order) | Supports |
|-------|----------------|----------|
| 1 | `businessId ASC, createdAt ASC` | businessId == + createdAt range |
| 2 | `businessId ASC, branchId ASC, createdAt ASC` | businessId == + branchId == + createdAt range |

#### Scenario: Report reads only matching documents

- GIVEN a business with 2,300 payments and a report request for one week
- WHEN the income report endpoint is called with startDate/endDate
- THEN Firestore SHALL return only payments matching businessId and the date range, and the endpoint SHALL NOT enumerate the full payments collection

#### Scenario: Branch filter pushed to Firestore

- GIVEN a request with a branchId
- WHEN the income report endpoint is called
- THEN the Firestore query SHALL include the branchId equality clause

#### Scenario: Deleted payments still excluded

- GIVEN a payment matching the query with `isDeleted: true`
- WHEN the report endpoint processes the result
- THEN the payment SHALL be excluded by the defensive Python filter

#### Scenario: Missing composite index

- GIVEN the required composite index does not exist
- WHEN the filtered query runs
- THEN the query SHALL fail with Firestore's index-error message and other endpoints SHALL remain unaffected

### Requirement: Dashboard Payment Query Filtered

The dashboard payment query MUST filter in Firestore by `businessId == X` and, when a branch scope applies, `branchId == Y`; it SHOULD also bound the window via `createdAt >= (now - 30 days)` so reads do not grow with history. The dashboard MUST keep the defensive Python exclusions (`isDeleted`, soft-deleted clients). This requires composite index 2 (and index 1 when no branch scope applies).

#### Scenario: Business-scoped query

- GIVEN a branch_admin loads the dashboard
- WHEN the dashboard endpoint runs
- THEN the payment query SHALL include businessId and branchId equality clauses in Firestore

#### Scenario: Bounded window

- GIVEN payments older than 30 days exist
- WHEN the dashboard endpoint runs
- THEN the Firestore query SHALL NOT return payments outside the 30-day window

#### Scenario: Deleted payments excluded

- GIVEN a payment with `isDeleted: true` inside the window
- WHEN the dashboard endpoint runs
- THEN the payment SHALL NOT contribute to any dashboard metric

### Requirement: Recent Clients Data Contract

`GET /api/reports/dashboard` response data MUST include a `recentClients` array: the most recent non-deleted clients of the business (branch-scoped), each with at least `id`, `name`, and `email`, up to 5 entries. DashboardPage MUST render the widget from `recentClients` and MUST NOT call `GET /api/clients` for it.

#### Scenario: Widget data from dashboard payload

- GIVEN a dashboard payload containing recentClients
- WHEN DashboardPage loads
- THEN the "Clientes Recientes" widget SHALL render from the payload without a separate clients fetch

#### Scenario: No recent clients

- GIVEN a business with no clients
- WHEN the dashboard loads
- THEN recentClients SHALL be an empty array and the widget SHALL show the empty-state message

#### Scenario: Deleted clients excluded

- GIVEN a soft-deleted client registered recently
- WHEN the dashboard loads
- THEN that client SHALL NOT appear in recentClients

### Requirement: ClientsPage Single Fetch

ClientsPage MUST fetch the clients list at most once per data change. The hook-level initial fetch and the page-level debounce effect MUST NOT both issue a request for the same state change.

#### Scenario: One fetch on mount

- GIVEN ClientsPage mounts with a businessId and no filters
- WHEN the page loads
- THEN exactly one GET /api/clients request SHALL be issued

#### Scenario: One fetch per filter change

- GIVEN the page is loaded with results
- WHEN the status or branch filter changes
- THEN exactly one GET /api/clients request SHALL be issued with the new filter

#### Scenario: Search still debounced

- GIVEN the user types a search term
- WHEN the debounce window elapses
- THEN exactly one search request SHALL be issued