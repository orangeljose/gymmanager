# Delta for dashboard-analytics

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Fix Overdue Clients Count

The `overdueClients` counter on the Dashboard MUST report the actual count of clients with expired memberships, computed only from clients that are not soft-deleted.
(Previously: counted clients with expired memberships without considering soft-deleted status.)

#### Scenario: Overdue clients displayed correctly

- GIVEN 5 clients have memberships expired before today
- WHEN the dashboard loads
- THEN the overdue count SHALL display "5"

#### Scenario: Deleted client excluded from overdue count

- GIVEN 5 clients have memberships expired before today, 1 of which is soft-deleted
- WHEN the dashboard loads
- THEN the overdue count SHALL display "4"