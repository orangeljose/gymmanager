# payment-flow Specification

## Purpose

Standalone payment registration flow enabling cashiers and admins to register payments without navigating to a client's detail page.

## Requirements

### Requirement: Standalone Payment Page

The system MUST provide a page at `/payments/new` accessible to `cashier`, `branch_admin`, and `super_admin` roles.

#### Scenario: Cashier accesses payment page

- GIVEN a user with cashier role is authenticated
- WHEN navigating to `/payments/new`
- THEN the payment registration form SHALL render with client search and empty payment fields

#### Scenario: Unauthorized role is redirected

- GIVEN a trainer role user is authenticated
- WHEN navigating to `/payments/new`
- THEN the system SHALL redirect to the dashboard with an access-denied message

### Requirement: Client Search and Summary

The system MUST allow searching and selecting an existing client, then display a summary with current plan name and membership status.

#### Scenario: Client found and displayed

- GIVEN the payment page is loaded
- WHEN a cashier searches for a client by name and selects one
- THEN the system SHALL display client name, current plan name, membership expiry date, and active/inactive status

#### Scenario: Client not found

- GIVEN the payment page is loaded
- WHEN a cashier searches for a nonexistent client
- THEN the system SHALL display "No clients found" without error

### Requirement: Payment Methods

The PaymentForm component MUST support: `cash`, `card`, `transfer`, `zelle`, `pago_movil`, and `other`.

#### Scenario: Cashier selects payment method

- GIVEN a client is selected
- WHEN the cashier chooses "transfer" from the method dropdown
- THEN amount input and reference field SHALL be enabled; the submit button SHALL be gated on valid amount

### Requirement: Amount Validation

The system MUST enforce that the payment amount matches the selected plan's price. The payment amount is auto-filled from the selected plan and is NOT editable by the user. Plan prices are validated when creating or editing plans (must be greater than $0).

#### Scenario: Amount auto-filled from plan

- GIVEN a client is selected
- WHEN the cashier selects a membership plan from the dropdown
- THEN the amount field SHALL auto-fill with the plan's price and SHALL be readonly

#### Scenario: Backend rejects mismatched amount

- GIVEN a payment request where the amount does NOT match the selected plan's price
- WHEN the backend processes the payment
- THEN the server SHALL respond with a 400 error and a descriptive message indicating the amount does not match the plan price

#### Scenario: Plan price must be positive

- GIVEN a user is creating or editing a plan
- WHEN the price is $0 or negative
- THEN the form SHALL display a validation error and block submission

### Requirement: Membership Auto-Extension

On successful payment registration, the system MUST extend the client's membership expiry by the plan's duration period.

#### Scenario: Monthly plan renewed

- GIVEN a client has a monthly plan expiring on July 15
- WHEN a full-plan payment is registered on July 10
- THEN the membership expiry SHALL update to August 15

### Requirement: Receipt Number Generation

Every payment MUST receive a unique sequential receipt number.

#### Scenario: Receipt number assigned

- GIVEN a valid payment is submitted
- WHEN the payment is saved
- THEN a receipt number SHALL be generated and displayed in the success confirmation

### Requirement: Dashboard Link Fix

The Dashboard dead link to `/payments/new` MUST be corrected.

#### Scenario: Dashboard "Register Payment" button works

- GIVEN the dashboard is loaded for a cashier user
- WHEN the "Register Payment" button is clicked
- THEN the user SHALL navigate to `/payments/new` without a 404 error

### Requirement: Shared PaymentForm Component

A `PaymentForm` component MUST be extracted from the existing ClientDetailPage modal implementation and reused in `/payments/new`.

#### Scenario: Existing modal still works

- GIVEN a client detail page is open
- WHEN "Register Payment" is clicked in the detail page modal
- THEN the payment modal SHALL function identically to before the extraction
