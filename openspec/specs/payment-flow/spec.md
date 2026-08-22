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

The system MUST allow searching and selecting an existing, non-deleted client, then display a summary with current plan name and membership status. Soft-deleted clients MUST NOT appear in client search results.

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

### Requirement: Payment Deletion Endpoint

The system MUST provide `DELETE /api/payments/:paymentId` that soft-deletes the payment and returns the client's recalculated membership.

#### Scenario: Successful deletion

- GIVEN an authorized user and an existing non-deleted payment
- WHEN the user sends DELETE `/api/payments/:paymentId`
- THEN the system SHALL mark the payment `isDeleted: true`, recalculate the client's membership, and return 200 with the recalculated membership data

#### Scenario: Payment not found

- GIVEN a `paymentId` that does not exist or is already soft-deleted
- WHEN the user sends DELETE `/api/payments/:paymentId`
- THEN the system SHALL return 404

### Requirement: Payment Deletion Authorization

Deletion MUST be restricted by role and branch. `super_admin` and `admin` MAY delete any payment; `branch_admin` MAY delete only payments in their own branch; `cashier` and `trainer` MUST NOT delete payments.

| Role | Own-branch payment | Cross-branch payment |
|------|--------------------|----------------------|
| super_admin | 200 | 200 |
| admin | 200 | 200 |
| branch_admin | 200 | 403 |
| cashier | 403 | 403 |
| trainer | 403 | 403 |

#### Scenario: branch_admin cross-branch

- GIVEN a `branch_admin` whose `branchId` differs from the payment's `branchId`
- WHEN they send DELETE `/api/payments/:paymentId`
- THEN the system SHALL return 403 without modifying the payment

#### Scenario: cashier denied

- GIVEN a cashier-authenticated request
- WHEN they send DELETE `/api/payments/:paymentId`
- THEN the system SHALL return 403

### Requirement: Soft Delete Behavior

Deletion MUST be a soft delete: the payment document MUST set `isDeleted: true` and MUST NOT be hard-deleted. Audit fields (`receiptNumber`, `registeredBy`, `registeredByName`, `paymentDate`, `amount`) MUST be preserved.

#### Scenario: Audit trail preserved

- GIVEN a payment with `receiptNumber` and `registeredBy`
- WHEN the payment is deleted
- THEN the document SHALL remain with `isDeleted: true` and all audit fields intact

### Requirement: Membership Recalculation After Deletion

The system MUST rebuild the client's membership from their remaining non-deleted payments, iterating in ascending `paymentDate` order and applying the same cumulative rule as `extend_membership`: the running end starts at the earliest payment's date and each payment advances it by `plan.durationDays × monthsPaid`, restarting from that payment's date if the running end has already passed. `membershipStart` SHALL equal the earliest remaining payment's date. If no payments remain, the client MUST be set to `isActive: false`, `status: 'expired'`.

#### Scenario: Delete only payment

- GIVEN a client with exactly one non-deleted payment
- WHEN that payment is deleted
- THEN the client SHALL become `isActive: false` and `status: 'expired'`

#### Scenario: Delete oldest payment

- GIVEN a client with multiple payments
- WHEN the earliest-dated payment is deleted
- THEN `membershipStart` SHALL move to the next remaining payment's date and `membershipEnd` SHALL be recomputed from scratch

#### Scenario: Delete most recent payment

- GIVEN a client with multiple payments
- WHEN the latest-dated payment is deleted
- THEN `membershipStart` SHALL remain unchanged and `membershipEnd` SHALL shorten by that payment's duration

#### Scenario: Multiple remaining payments

- GIVEN a client with three or more payments and one middle payment is deleted
- THEN `membershipEnd` SHALL be determined by summing the remaining payments' durations in chronological order

### Requirement: Soft-Deleted Payment Filtering

All payment queries — client history, reports, and receipts — MUST exclude payments where `isDeleted` is truthy. A payment WITHOUT an `isDeleted` field MUST be treated as not deleted, using defensive in-Python filtering (Firestore equality filters omit documents missing the field).

#### Scenario: History excludes deleted

- GIVEN a client with one active and one soft-deleted payment
- WHEN payment history is fetched
- THEN the deleted payment SHALL be excluded

#### Scenario: Missing field treated as active

- GIVEN a legacy payment lacking an `isDeleted` field
- WHEN history, report, or receipts are queried
- THEN the payment SHALL be included

### Requirement: Payment Deletion UI

`ClientDetailPage` payment history MUST show a delete action on each payment row, visible only to `super_admin`, `admin`, and `branch_admin`. Deleting MUST require a confirmation modal, and on success MUST refresh payment history and client data.

#### Scenario: Authorized delete flow

- GIVEN an authorized user viewing a client's payment history
- WHEN they click delete and confirm the modal
- THEN the payment SHALL be deleted server-side and both payment history and client membership SHALL refresh

#### Scenario: Cashier sees no delete button

- GIVEN a cashier viewing a client's payment history
- WHEN the history renders
- THEN no delete action SHALL be visible
