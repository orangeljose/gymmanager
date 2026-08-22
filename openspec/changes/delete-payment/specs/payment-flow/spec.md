# Delta for payment-flow

## ADDED Requirements

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
