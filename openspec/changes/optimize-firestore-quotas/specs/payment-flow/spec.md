# Delta for payment-flow

## MODIFIED Requirements

### Requirement: Receipt Number Generation

Every payment MUST receive a unique sequential receipt number.

The receipt number MUST follow the format `P-YYYYMMDD-XXX` (generation date + sequence). The sequence value MUST be derived WITHOUT enumerating the payment history: the system SHALL use a constant-cost mechanism — the Firestore `count()` aggregation over the business's payments, or an equivalent non-enumerating counter — so reads do NOT grow with the total payment count P. The sequence MAY contain gaps but MUST NOT repeat. Soft-deleted payments SHALL count toward the sequence (preserving current len+1 semantics); the count MUST NOT apply isDeleted filtering. When the aggregation is unavailable or the payment count exceeds the aggregation ceiling, the system SHALL fall back to a unique timestamp-based number (`P-YYYYMMDD-HHMMSSfff`) and MUST NOT block payment registration.

(Previously: sequence computed by scanning ALL payments of the business (`query_firestore('payments', businessId ==)` + `len() + 1`), costing O(P) reads per payment write.)

#### Scenario: Receipt number assigned

- GIVEN a valid payment is submitted
- WHEN the payment is saved
- THEN a receipt number SHALL be generated and displayed in the success confirmation

#### Scenario: Quota-efficient generation

- GIVEN a business with P payments, P large
- WHEN a new payment is registered
- THEN receipt generation SHALL read a small constant number of documents independent of P, and SHALL NOT enumerate the payments collection

#### Scenario: Uniqueness and format preserved

- GIVEN two payments registered on the same day
- WHEN both are saved
- THEN both receipt numbers SHALL be unique and match the format P-YYYYMMDD-XXX

#### Scenario: Gaps tolerated

- GIVEN a payment is soft-deleted after receiving a receipt number
- WHEN a later payment is registered
- THEN the later sequence SHALL NOT reuse the deleted payment's number; contiguity is NOT required

#### Scenario: Aggregation failure fallback

- GIVEN the count aggregation fails or the payment count exceeds the aggregation ceiling
- WHEN a payment is registered
- THEN the system SHALL generate a unique timestamp-based number and SHALL complete the registration successfully