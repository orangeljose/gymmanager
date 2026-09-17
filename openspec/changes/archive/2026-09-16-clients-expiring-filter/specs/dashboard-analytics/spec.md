# Delta for dashboard-analytics

## ADDED Requirements

### Requirement: Dashboard Counters Independent of Solvency Report

The Dashboard's `overdueClients` and `expiringThisWeek` counters MUST be computed from `GET /api/reports/dashboard` and MUST NOT depend on `GET /api/reports/solvency`. Removing the solvency endpoint MUST NOT alter dashboard behavior or payload.

#### Scenario: Vencidos count after solvency removal

- GIVEN 5 clients with memberships expired before today and the solvency endpoint removed
- WHEN the dashboard loads
- THEN the Vencidos counter SHALL display "5"

#### Scenario: Expiring count unaffected

- GIVEN 3 clients expiring this week
- WHEN the dashboard loads after solvency removal
- THEN `expiringThisWeek` SHALL display "3"

## MODIFIED Requirements

### Requirement: ClientsPage Single Fetch

ClientsPage MUST fetch the clients list at most once per data change. The hook-level initial fetch and the page-level debounce effect MUST NOT both issue a request for the same state change. The "Próximos 7 días" dropdown option SHALL count as a filter change subject to the same rule.
(Previously: covered status and branch filter changes only.)

#### Scenario: One fetch on mount

- GIVEN ClientsPage mounts with a businessId and no filters
- WHEN the page loads
- THEN exactly one GET /api/clients request SHALL be issued

#### Scenario: One fetch per filter change

- GIVEN the page is loaded with results
- WHEN the status, branch, or expiringSoon filter changes
- THEN exactly one GET /api/clients request SHALL be issued with the new filter

#### Scenario: One fetch per Próximos 7 días selection

- GIVEN the page is loaded with results
- WHEN the user selects "Próximos 7 días"
- THEN exactly one GET /api/clients request SHALL be issued with `expiringSoon=true`

#### Scenario: Search still debounced

- GIVEN the user types a search term
- WHEN the debounce window elapses
- THEN exactly one search request SHALL be issued