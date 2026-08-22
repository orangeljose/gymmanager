# Delta for payment-flow

## MODIFIED Requirements

### Requirement: Client Search and Summary

The system MUST allow searching and selecting an existing, non-deleted client, then display a summary with current plan name and membership status. Soft-deleted clients MUST NOT appear in client search results.
(Previously: search returned any existing client without considering soft-deleted status.)

#### Scenario: Client found and displayed

- GIVEN the payment page is loaded
- WHEN a cashier searches for a client by name and selects one
- THEN the system SHALL display client name, current plan name, membership expiry date, and active/inactive status

#### Scenario: Client not found

- GIVEN the payment page is loaded
- WHEN a cashier searches for a nonexistent client
- THEN the system SHALL display "No clients found" without error

#### Scenario: Deleted client excluded from search

- GIVEN a soft-deleted client whose name matches the search term
- WHEN a cashier searches for that name
- THEN the deleted client SHALL NOT appear in the results