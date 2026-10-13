# Verification Report

**Change**: cash-expenses (Phase 1 — Egresos)
**Version**: N/A (delta spec, no version)
**Mode**: Standard (Strict TDD disabled per `sdd/gymmanager/testing-capabilities`)
**Branch**: `feature/cash-expenses` (review branch, NOT merged)
**Date**: 2026-10-13

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 23 |
| Tasks complete | 22 |
| Tasks incomplete | 1 |

Incomplete task: `6.2 Manual smoke (live Firebase)` — ops/verification task, not a code
deliverable (requires live credentials + the manual composite index).

## Build & Tests Execution

**Type check**: ✅ Passed
```text
cd frontend && npx tsc --noEmit  → exit 0 (no output)
```

**Expenses tests**: ✅ 43 passed / ❌ 0 failed / ⚠️ 0 skipped
```text
cd backend && venv\Scripts\python.exe -m pytest tests/routes/test_expenses.py -v
→ 43 passed, 43 warnings in 10.95s
```

**Full suite (branch)**: 18 failed, 425 passed
```text
cd backend && venv\Scripts\python.exe -m pytest tests/ -q
→ 18 failed, 425 passed in 16.97s
```

**Full suite (baseline `main`)**: 18 failed, 382 passed
```text
git checkout main && pytest tests/ -q
→ 18 failed, 382 passed in 13.61s
```

Baseline comparison: the SAME 18 pre-existing failures (`test_client`, `test_plans`,
`test_users`, `test_dashboard`) occur on `main`. 382 (main) + 43 (new expense tests)
= 425 (branch). **No new failures introduced.**

**Coverage**: ➖ Not available (pytest-cov / coverage not installed).

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Expense Data Model | Document shape on create | `test_expenses.py > TestCreateExpense::test_create_valid_201` | ✅ COMPLIANT |
| List Expenses | List with filters | `test_list_filters_category_and_range_and_meta` | ✅ COMPLIANT |
| List Expenses | Deleted expense excluded | `test_list_excludes_deleted_and_sorts_date_desc` | ✅ COMPLIANT |
| Create Expense | Successful create | `test_create_valid_201` | ✅ COMPLIANT |
| Create Expense | Invalid input | `test_create_invalid_amount_cents_400[0/-100/500/12.5/True]`, `test_create_invalid_category_400`, `test_create_invalid_date_400` | ✅ COMPLIANT |
| Update Expense | Successful update | `test_update_fields_200` | ✅ COMPLIANT |
| Update Expense | Missing or deleted | `test_update_missing_404`, `test_update_deleted_404` | ✅ COMPLIANT |
| Soft Delete Expense | Soft delete preserves audit | `test_soft_delete_audit_preserved`, `test_deleted_expense_excluded_from_list_and_summary` | ✅ COMPLIANT |
| Expense Summary | Summary windows | `test_summary_windows_and_by_category_one_query` | ✅ COMPLIANT |
| Expense Permissions | Cashier forbidden | `test_non_admin_roles_forbidden_403[cashier|trainer × 5 endpoints]` (+ `test_unauth_returns_401`) | ✅ COMPLIANT |
| No Income In Phase 1 | Income not modeled here | (none — review-type scenario) | ⚠️ PARTIAL (static) |
| Composite Index | Index documented | (none — doc artifact) | ⚠️ PARTIAL (static) |

**Compliance summary**: 10/12 scenarios runtime-compliant; 12/12 satisfied (2 via static inspection).

The two ⚠️ scenarios are non-behavioral by nature (a review statement and a documentation
requirement), so no runtime test can cover them. Static evidence below confirms both.

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Expenses CRUD scoped | ✅ Implemented | `_scope_ids()` + `_expense_scope_denied()`; Firestore equality on `businessId` only, branch/category/date/search filtered in Python |
| Soft delete + audit | ✅ Implemented | `DELETE` sets `isDeleted:true`, `deletedBy`, `deletedAt`; `_is_active()` excludes from list/summary; PUT/DELETE on deleted → 404 |
| Validation | ✅ Implemented | category ∈ `EXPENSE_CATEGORIES`; `_valid_amount` (int, not bool, >0); `validate_date_format` regex `^\d{4}-\d{2}-\d{2}$` |
| Summary | ✅ Implemented | One scoped query, Python group: today / rolling 7d / rolling 30d + `byCategory` |
| Permissions | ✅ Implemented | `@require_auth` + `@require_role(ADMIN_ROLES)` on all 5 endpoints; `ADMIN_ROLES=[super_admin,admin,branch_admin]` |
| Composite index documented | ✅ Implemented | `openspec/changes/cash-expenses/indexes.md` documents `expenses (businessId ASC, date ASC)`; `_index_error_response` returns actionable 500 |
| Frontend wired | ✅ Implemented | `ExpensesPage.tsx`, `ExpenseForm.tsx`, `/expenses` route (admin+ `ProtectedRoute`), nav "Egresos" (`TrendingDown`) after "Equipamiento", 5 `apiService` methods, types |
| $ ↔ cents conversion | ✅ Implemented | Form: `Math.round(dollars*100)`; edit prefill: `(amountCents/100).toFixed(2)`; `formatDollars` = `cents/100`; chart tooltip consistent |
| No income in Phase 1 | ✅ Implemented | No income/earning field or endpoint in `expenses.py`; only a doc comment noting income stays in `payments` |
| Blueprint registration | ✅ Implemented | Exported in `routes/__init__.py` AND imported/registered in `app.py` (both sites, mirrors machines) |

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| 1. New `routes/expenses.py` blueprint, both registration sites | ✅ Yes | |
| 2. `_scope_ids()` shape (super_admin query params; others from user) | ✅ Yes | |
| 3. Firestore equality on `businessId` only; rest in Python | ✅ Yes | Test asserts exactly one filter |
| 4. Summary = one scoped query, Python grouping, no counters | ✅ Yes | Test asserts single query call |
| 5. Soft delete + audit; list/summary exclude; PUT → 404 | ✅ Yes | |
| 6. `require_role(ADMIN_ROLES)` on all 5 endpoints | ✅ Yes | |
| 7. `ExpensesPage.tsx` + `ExpenseForm.tsx` modal, no `/expenses/new` | ✅ Yes | |
| 8. Nav "Egresos" (`TrendingDown`) after "Equipamiento" | ✅ Yes | |
| 9. Document `expenses (businessId, date)` composite index | ✅ Yes | `indexes.md` |

## Issues Found

**CRITICAL**: None.

**WARNING**:
1. Task **6.2 (manual live-Firebase smoke)** is not executed. Create→list→edit→delete→summary
   has never been exercised against a real Firestore, and the manual composite index has not
   been built in any environment. Automated tests mock Firestore, so real query behavior
   (index requirement, serialization) is unproven. Cleanup/ops task → WARNING, not CRITICAL.

**SUGGESTION**:
1. Composite index may be unnecessary as written. The code issues only a single-field
   equality query (`businessId ==`) and sorts/ranges in Python, so Firestore would not
   require `(businessId, date)`. The spec explicitly requires the index be *documented*
   (satisfied), but the `_index_error_response`/`indexes.md` narrative ("query ... and
   sort/range on date") overstates what the query does. Consider aligning the wording, or
   pushing date order into Firestore if volume grows.
2. `summary.byCategory` aggregates **all-time** non-deleted expenses while `today/week/month`
   are windowed. This matches the spec/design (no window defined for `byCategory`), but the
   UI chart is rendered next to 30-day stat cards, which can read as if it were also 30-day.
   A one-line label clarification would remove the ambiguity.
3. `validate_date_format` only checks the `YYYY-MM-DD` shape, not calendar validity
   (`2026-13-45` passes). Pre-existing shared helper — consistent with the rest of the
   codebase, so not a regression, but worth a future hardening pass.

## Verdict

**PASS WITH WARNINGS**

All 43 expense tests pass, frontend type-checks clean, and the full suite shows no new
failures beyond the 18 pre-existing baseline failures. Every behavioral spec scenario is
covered by a passing test; the two remaining scenarios are non-behavioral and verified
statically. The only open item is the unexecuted live-Firebase manual smoke (and the
related manual index build).
