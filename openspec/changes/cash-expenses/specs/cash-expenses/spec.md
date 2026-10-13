# Cash Expenses Specification

## Purpose

Register, list, update and soft-delete gym expenses by category, scoped by business/branch, with period and by-category summaries. Phase 1 is expenses-only: income remains in `payments` (memberships) and future Phase 2 sales.

## Requirements

### Requirement: Expense Data Model

Each expense SHALL be a document in the `expenses` collection with fields: `id`, `category` (`payroll|supplies|services|rent|maintenance|other`), `amountCents` (integer > 0), `description`, `date` (YYYY-MM-DD), `businessId`, `branchId`, `registeredBy`, `registeredByName`, `createdAt`, `isDeleted`.

#### Scenario: Document shape on create

- GIVEN an authorized admin in scope
- WHEN an expense is created
- THEN the document MUST contain every model field
- AND `isDeleted` MUST default to `false`

### Requirement: List Expenses

`GET /api/expenses` SHALL list expenses scoped by `businessId` (and `branchId` when the caller is branch-scoped), excluding `isDeleted:true`. It SHALL accept optional `startDate`/`endDate` (YYYY-MM-DD), `category` and pagination (`page`, `limit`). It MUST use one scoped Firestore query with in-memory filtering — no full scan.

#### Scenario: List with filters

- GIVEN an admin in business B
- WHEN GET `/api/expenses?category=rent&startDate=2026-01-01&endDate=2026-01-31&page=1&limit=20`
- THEN respond 200 with a data array and `meta {total,page,limit,pages}`
- AND only non-deleted business B expenses inside the range are returned

#### Scenario: Deleted expense excluded

- GIVEN an expense with `isDeleted:true`
- WHEN the list is queried
- THEN it SHALL NOT appear in the results

### Requirement: Create Expense

`POST /api/expenses` SHALL create an expense. `category` MUST be one of the allowed values, `amountCents` MUST be an integer > 0, and `date` MUST be YYYY-MM-DD. `description` is optional. It SHALL respond 201.

#### Scenario: Successful create

- GIVEN an admin in scope
- WHEN POST `/api/expenses` with valid `category`, `amountCents`, `date`
- THEN respond 201 with `{success:true, data:{...}}`

#### Scenario: Invalid input

- GIVEN an admin
- WHEN POST with `amountCents:0`, or `category:"travel"`, or `date:"01-2026"`
- THEN respond 400 with an error message
- AND no document is created

### Requirement: Update Expense

`PUT /api/expenses/:id` SHALL update an expense. It MUST respond 404 if the expense does not exist or is soft-deleted.

#### Scenario: Successful update

- GIVEN an existing expense
- WHEN PUT `/api/expenses/:id` with valid fields
- THEN respond 200 with the updated fields

#### Scenario: Missing or deleted

- GIVEN an unknown or soft-deleted id
- WHEN PUT `/api/expenses/:id`
- THEN respond 404

### Requirement: Soft Delete Expense

`DELETE /api/expenses/:id` SHALL soft-delete the expense by setting `isDeleted:true`, `deletedBy`, `deletedAt`. It SHALL respond 200.

#### Scenario: Soft delete preserves audit

- GIVEN an existing expense
- WHEN DELETE `/api/expenses/:id`
- THEN the document MUST keep its data with `isDeleted:true` and audit fields
- AND subsequent list and summary calls MUST exclude it

### Requirement: Expense Summary

`GET /api/expenses/summary` SHALL return totals for today, rolling 7 days and rolling 30 days, plus a by-category breakdown. It MUST derive them from a single scoped query grouped in Python — no daily counters.

#### Scenario: Summary windows

- GIVEN expenses spread across 30 days in business B
- WHEN GET `/api/expenses/summary`
- THEN respond 200 with `{today, week, month, byCategory}`
- AND each total only counts non-deleted in-scope expenses

### Requirement: Expense Permissions

All expense endpoints MUST require `super_admin`, `admin` or `branch_admin`. `cashier` and `trainer` MUST receive 403.

#### Scenario: Cashier forbidden

- GIVEN a cashier
- WHEN calling any `/api/expenses` endpoint
- THEN respond 403
- AND no expense data is returned

### Requirement: No Income In Phase 1

The `expenses` capability SHALL NOT record income. Income MUST remain in `payments` (memberships) and future Phase 2 sales.

#### Scenario: Income not modeled here

- GIVEN the cash-expenses change
- WHEN reviewing its endpoints and model
- THEN none SHALL accept an income or earning concept

### Requirement: Composite Index

A Firestore composite index `expenses (businessId ASC, date ASC)` MUST be documented for manual creation.

#### Scenario: Index documented

- GIVEN a new environment
- WHEN the change is deployed
- THEN the required `expenses (businessId, date)` index MUST be documented
