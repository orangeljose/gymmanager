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
