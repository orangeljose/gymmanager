# expiry-notifications Specification

## Purpose

Visual expiry indicators on client-facing views so staff can proactively identify clients needing membership renewal within 7 days.

## Requirements

### Requirement: Expiry Badge on Dashboard

The Dashboard MUST display a badge or highlight on clients whose membership expires within 7 days of the current date.

#### Scenario: Client expiring in 3 days

- GIVEN a client's membership expires in 3 days
- WHEN the dashboard renders the clients list
- THEN that client row SHALL display a warning badge (e.g., "Expires in 3 days")

#### Scenario: Client expiring today

- GIVEN a client's membership expires today
- WHEN the dashboard renders the clients list
- THEN that client row SHALL display an urgent badge (e.g., "Expires today")

#### Scenario: Client not expiring soon

- GIVEN a client's membership expires in 15 days
- WHEN the dashboard renders the clients list
- THEN no expiry badge SHALL be shown

### Requirement: Expiry Badge on ClientsPage

The ClientsPage MUST display the same expiry badge as the Dashboard, ensuring consistency across views.

#### Scenario: ClientsPage shows expiry indicators

- GIVEN the clients list page is loaded
- WHEN there are clients expiring within 7 days
- THEN those client rows SHALL display the same expiry badge as the Dashboard

#### Scenario: Real-time badge after payment

- GIVEN a client with an expiring membership makes a payment that extends membership
- WHEN the clients list reloads
- THEN the expiry badge SHALL be removed for that client

### Requirement: Data Source

Expiry data SHALL be computed on the client side using the `membershipEnd` date from each client record. A reusable helper `getDaysRemaining(date)` calculates the difference between today and the expiry date.

#### Scenario: Client-side expiry computation

- GIVEN a client with membership expiring on July 18 (7 days from July 11)
- WHEN the frontend renders expiry badges on DashboardPage, ClientsPage, or ClientDetailPage
- THEN each page SHALL compute `daysRemaining` via `getDaysRemaining(membershipEnd)` and display a badge when `daysRemaining >= 0 && daysRemaining <= 7`
