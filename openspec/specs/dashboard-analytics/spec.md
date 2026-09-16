# dashboard-analytics Specification

## Purpose

Enhanced Dashboard with income visualization, client engagement metrics, and bug fixes for overdue count and currency display.

## Requirements

### Requirement: 30-Day Income Chart

The Dashboard MUST render a bar chart of daily income for the last 30 days using Recharts.

#### Scenario: Dashboard loads with income data

- GIVEN payment data exists for the last 30 days
- WHEN the dashboard page loads
- THEN a bar chart SHALL display with each bar representing daily sum of payments; no-data days SHALL show zero

#### Scenario: No payment data

- GIVEN no payments exist in the last 30 days
- WHEN the dashboard loads
- THEN the chart SHALL render empty with a "No hay datos registrados bajo este periodo" message

### Requirement: Top 5 Clients Widget

The Dashboard MUST display the top 5 clients ranked by payment count.

#### Scenario: Clients ranked by payments

- GIVEN payment records exist across multiple clients
- WHEN the dashboard loads
- THEN a list SHALL display the 5 clients with highest payment counts in descending order

#### Scenario: Fewer than 5 clients

- GIVEN only 3 clients have payment records
- WHEN the dashboard loads
- THEN the widget SHALL show all 3 clients without empty rows

### Requirement: Client Retention Metric

The Dashboard SHALL display the percentage of clients who renewed their membership at least once.

#### Scenario: Retention calculated

- GIVEN 100 clients, 60 have renewed at least once
- WHEN the dashboard loads
- THEN retention SHALL display "60%"

#### Scenario: No clients with renewals

- GIVEN no client has renewed
- WHEN the dashboard loads
- THEN retention SHALL display "0%"

### Requirement: Fix Overdue Clients Count

The `overdueClients` counter on the Dashboard MUST report the actual count of clients with expired memberships, computed only from clients that are not soft-deleted.

#### Scenario: Overdue clients displayed correctly

- GIVEN 5 clients have memberships expired before today
- WHEN the dashboard loads
- THEN the overdue count SHALL display "5"

#### Scenario: Deleted client excluded from overdue count

- GIVEN 5 clients have memberships expired before today, 1 of which is soft-deleted
- WHEN the dashboard loads
- THEN the overdue count SHALL display "4"

### Requirement: Fix Currency Display

All monetary values on the Dashboard MUST display using the correct business currency configured per branch.

#### Scenario: Currency shown correctly

- GIVEN a branch is configured with currency "USD"
- WHEN the dashboard displays any monetary value
- THEN the value SHALL be prefixed with "$" (USD symbol)

### Requirement: Client-Derived Metrics Exclude Deleted Clients

The dashboard client-derived metrics `activeClients` and `expiringThisWeek` MUST be computed only from clients that are not soft-deleted. A client with `isDeleted: true` MUST NOT contribute to either count. A client WITHOUT an `isDeleted` field MUST be treated as not deleted. The `retentionRate` SHALL derive from the same non-deleted client base.

#### Scenario: Deleted client excluded from active count

- GIVEN 5 active clients of which 1 is soft-deleted
- WHEN the dashboard loads
- THEN `activeClients` SHALL display 4

#### Scenario: Deleted client excluded from expiring count

- GIVEN 3 clients expiring this week, 1 of which is soft-deleted
- WHEN the dashboard loads
- THEN `expiringThisWeek` SHALL display 2

#### Scenario: Legacy client without field counted

- GIVEN a client lacking an `isDeleted` field with an active membership
- WHEN the dashboard loads
- THEN the client SHALL count toward `activeClients`

### Requirement: Top Paying Clients Keep Deleted Clients

The `topPayingClients` widget MUST include payments from soft-deleted clients as historical record (payment-derived metric).

#### Scenario: Deleted client still ranked

- GIVEN a soft-deleted client with 5 payments in the last 30 days
- WHEN the dashboard loads
- THEN the widget SHALL rank that client by their payment count

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
