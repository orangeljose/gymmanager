# Verification Report

**Change**: machines-maintenance
**Version**: N/A (delta specs, unversioned)
**Mode**: Standard (Strict TDD disabled — no frontend test runner; backend has pytest without coverage tooling)
**Branch**: `feature/machines` (from `main`) — reviewed, NOT merged
**Date**: 2026-10-13

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 31 |
| Tasks complete | 29 |
| Tasks incomplete | 2 (ops-only: 7.1 console index creation, 7.3 live E2E) |

Incomplete tasks are non-code operational steps, not core implementation tasks.

## Build & Tests Execution

**Build (frontend type-check)**: ✅ Passed
```text
npx tsc --noEmit   (cwd: frontend/)
EXIT CODE: 0
```

**Tests (machine suite)**: ✅ 37 passed / ❌ 0 failed / ⚠️ 0 skipped
```text
pytest tests/routes/test_machines.py -v   (cwd: backend/)
collected 37 items
======================== 37 passed, 37 warnings in 1.72s ========================
```

**Tests (full suite, baseline comparison)**: ✅ No new failures
```text
backend, branch main         : 18 failed, 289 passed in 3.56s
backend, branch feature/machines: 18 failed, 326 passed in 5.19s
Delta: +37 passed (all new machine tests), +0 new failures.
```
The 18 failures are pre-existing and unrelated to this change
(`tests/models/test_client.py`, `tests/routes/test_plans.py`, `tests/routes/test_users.py`,
`tests/unit/test_dashboard.py`). Matches the expected baseline of 18 exactly.

**Coverage**: ➖ Not available (no coverage tooling configured).

## Spec Compliance Matrix

### machine-inventory (7 requirements, 13 scenarios)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Machines Data Model | Document shape on create | `test_machines.py > TestCreateMachine::test_create_valid_201_with_defaults` | ✅ COMPLIANT |
| List Machines | List with filters | `TestListMachines::test_list_filters_and_meta` | ✅ COMPLIANT |
| List Machines | Legacy document treated as active | `TestListMachines::test_list_legacy_active_included_and_deleted_excluded` | ✅ COMPLIANT |
| List Machines | Deleted machine excluded | `TestListMachines::test_list_legacy_active_included_and_deleted_excluded` | ✅ COMPLIANT |
| Create Machine | Successful create | `TestCreateMachine::test_create_valid_201_with_defaults` | ✅ COMPLIANT |
| Create Machine | Invalid input | `TestCreateMachine::test_create_empty_name_400` + `test_create_invalid_category_400` | ✅ COMPLIANT |
| Create Machine | Cross-branch create denied | `TestCreateMachine::test_create_cross_branch_403` | ✅ COMPLIANT |
| Update Machine | Update status | `TestUpdateAndDeleteMachine::test_update_status_200` | ✅ COMPLIANT |
| Update Machine | Missing or deleted machine | `TestUpdateAndDeleteMachine::test_update_missing_404` (missing only) | ⚠️ PARTIAL |
| Soft Delete Machine | Soft delete preserves document | `TestUpdateAndDeleteMachine::test_soft_delete_preserves_document` | ✅ COMPLIANT |
| Permissions | Trainer cannot write | `TestCreateMachine::test_trainer_cannot_create_403` (+`test_cashier_cannot_delete_403`, `test_unauth_returns_401`) | ✅ COMPLIANT |
| Permissions | Cashier can read | `TestPermissions::test_cashier_can_read_200` | ✅ COMPLIANT |
| Composite Index | Missing index | (none found) | ❌ UNTESTED |

### machine-maintenance (8 requirements, 16 scenarios)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Maintenance Data Model | Document shape on create | `TestMaintenanceTransitions::test_record_contains_all_model_fields` | ✅ COMPLIANT |
| List Machine Maintenance | Ordered paginated history | `TestMaintenanceHistory::test_history_order_and_pagination` | ✅ COMPLIANT |
| List Machine Maintenance | Cross-tenant machine | `TestMaintenanceHistory::test_history_cross_business_403` | ✅ COMPLIANT |
| Add Maintenance Record | Add record | `TestMaintenanceTransitions::test_repair_completed_sets_resolved_status` + `test_record_contains_all_model_fields` | ✅ COMPLIANT |
| Add Maintenance Record | Unknown or deleted machine | `TestMaintenanceTransitions::test_unknown_machine_404` (unknown only) | ⚠️ PARTIAL |
| Add Maintenance Record | Invalid type | `TestMaintenanceTransitions::test_invalid_type_400` | ✅ COMPLIANT |
| Repair Completion Updates Machine Status | Completed repair sets status | `TestMaintenanceTransitions::test_repair_completed_sets_resolved_status` | ✅ COMPLIANT |
| Repair Completion Updates Machine Status | Repair keeps machine out of service | `TestMaintenanceTransitions::test_repair_completed_sets_resolved_status` | ✅ COMPLIANT |
| Preventive Maintenance Schedules Next Date | Preventive sets next date | `TestMaintenanceTransitions::test_preventive_completed_sets_plus_90_days` | ✅ COMPLIANT |
| Preventive Maintenance Schedules Next Date | Explicit override | `TestMaintenanceTransitions::test_preventive_explicit_override` | ✅ COMPLIANT |
| Maintenance Summary | Summary counts | `TestMachinesSummary::test_summary_counts_window_and_recent` | ✅ COMPLIANT |
| Maintenance Summary | Cashier reads summary | `TestMachinesSummary::test_summary_no_upcoming_empty` | ✅ COMPLIANT |
| Maintenance Summary | No upcoming maintenance | `TestMachinesSummary::test_summary_no_upcoming_empty` | ✅ COMPLIANT |
| Permissions | Trainer cannot log maintenance | `TestMaintenanceTransitions::test_trainer_cannot_log_403` | ✅ COMPLIANT |
| Permissions | Trainer can read history | `TestMaintenanceHistory::test_history_order_and_pagination` | ✅ COMPLIANT |
| Composite Index | Missing index | (none found) | ❌ UNTESTED |

**Compliance summary**: 25/29 scenarios COMPLIANT, 2 PARTIAL, 2 UNTESTED.
(The orchestrator's prompt said 15 + 19 scenarios; the spec files contain 13 + 16 = 29
actual scenarios. The matrix maps every scenario present in the spec files.)

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Scoped queries (businessId equality only) | ✅ Implemented | List/summary filter only `businessId` in Firestore; category/status/branchId/search resolved in Python. Single-field auto index suffices. |
| No N+1 | ✅ Implemented | Summary = 1 `machines` query + 1 bounded `machine_maintenance` query; asserted by `test_summary_counts_window_and_recent`. History = 1 query. List = 1 query. |
| Repair completion → `machine.status = resolvedStatus` | ✅ Implemented | Inline transition; completed repair without `resolvedStatus` rejected 400. |
| Preventive completed → `nextMaintenanceDate = date + 90d` (+ override) | ✅ Implemented | `PREVENTIVE_INTERVAL_DAYS = 90`; explicit override honored; does NOT resurrect `out_of_service`. |
| scheduled/in_progress → `machine.status = 'maintenance'` | ✅ Implemented | Both statuses covered (parametrized test). |
| Soft delete with audit fields | ✅ Implemented | `{isActive:false, deletedBy, deletedAt}`; `delete_document` never called. |
| 404 on missing/deleted machine | ✅ Implemented | Shared `_fetch_active_machine` guards GET/PUT/DELETE/maintenance. |
| Denormalized `machineName` | ✅ Implemented | Set from machine at record creation. |
| Actionable index-error 500 | ✅ Implemented (untested) | `_index_error_response` returns guidance referencing both `machine_maintenance` indexes. |
| Isolation-safe tests | ✅ Implemented | `prime_app_modules` + per-request call-site patching (ported from `test_attendance.py`). Full-suite delta confirms isolation. |

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| 1. Blueprint registered in both `__init__.py` and `app.py` | ✅ Yes | Both sites confirmed in diff. |
| 2. Transition logic inline (no service class) | ✅ Yes | Inline in `add_machine_maintenance`. |
| 3. Machine status from completed repair `resolvedStatus` | ✅ Yes | |
| 4. Preventive +90d, flip to operational only if currently `maintenance` | ✅ Yes | `test_preventive_does_not_resurrect_out_of_service`. |
| 5. scheduled/in_progress → `maintenance` | ✅ Yes | |
| 6. Summary counts in memory from 1 scoped query | ✅ Yes | |
| 7. Recent repairs: 1 bounded query `date DESC` limit 5 | ✅ Yes | ⚠️ branch filter applied post-limit — see WARNING 2. |
| 8. Soft delete with audit | ✅ Yes | |
| 9. Shared `MachineForm.tsx`, NO `/machines/new` route | ✅ Yes | App.tsx has only `machines` and `machines/:id`. |
| 10. Nav "Máquinas" (`Dumbbell`) after Clientes, roles = all | ✅ Yes | Placed after Clientes (no "Asistencia" item exists on this branch). No `roles` restriction. |
| Routes `/machines`, `/machines/:id` for all roles | ✅ Yes | Nested under authenticated `Layout`; no `requiredRoles`. |

## Issues Found

**CRITICAL**: None.
All executed test commands exit 0, all 37 new tests pass, and the full-suite baseline is preserved.

**WARNING**:
1. **Spec ↔ design drift on `machines` composite indexes.** `machine-inventory` spec REQ *Composite Index* mandates `machines (businessId, category)` and `(businessId, status)`. Design decision #6, `indexes.md`, and the implementation deliberately do NOT create or require them: only `businessId` equality reaches Firestore (category/status filtered in Python), so the automatic single-field index suffices. Behavior is correct and more quota-friendly, but the spec text is stale and must be reconciled at archive.
2. **Branch-scoped `recentRepairs` can be incomplete/misleading.** `machines_summary` fetches the business-wide `limit=5` maintenance records and *then* filters by `branchId` in Python (`routes/machines.py` lines ~302-305). For a branch-scoped user whose own branch records are not in the business-wide top-5, `recentRepairs` returns fewer than 5 or empty. The existing test only uses same-branch records, so it does not expose this. Fix: push `branchId` equality into the query (needs `(businessId, branchId, date DESC)` index) or use a larger pre-limit.
3. **`_index_error_response` path untested.** Both *Composite Index → Missing index* scenarios have no covering test; the actionable-500 helper is implemented but never exercised. SHOULD-level requirement, but per the verify skill an uncovered scenario is reported as UNTESTED.
4. **Two ops tasks remain open.** Task 7.1 (create the two `machine_maintenance` composite indexes in the Firebase console) and 7.3 (manual end-to-end API verification against live Firebase) are unchecked. Docs are recorded in `indexes.md`; console creation + live E2E pending. Blocks a fully "done" claim, not a code defect.

**SUGGESTION**:
1. **Category enum drift.** Spec *Machines Data Model* lists `category` (`cardio|strength|functional|other`); implementation/design/types add `free_weights`. Implementation is a superset — update the spec for consistency.
2. **`upcomingMaintenance` includes overdue dates.** Filter is `nextMaintenanceDate <= today+7d` with no lower bound, so past-due machines appear as "upcoming". Possibly intentional ("due/overdue"), but spec wording says "within the next 7 days". Consider documenting the intent or renaming, and add an overdue test.
3. **`recentRepairs` returns any maintenance type.** The field/query is not filtered to `type=='repair'`, so preventive records can appear under "recent repairs". Semantics vs. spec prose ("last 5 recent repairs") should be clarified.
4. **super_admin without `businessId` runs unbounded queries.** `list`/`summary` execute with an empty filter set (full-collection scan) when a super_admin passes no `businessId`. Acceptable at 10–50 docs/business; consider a guard or explicit "all businesses" mode.
5. **`MachinesPage` fetches `limit: 100` with no pagination UI.** Fine at current volume; the API already supports `page`/`limit` if the inventory grows.

## Verdict

**PASS WITH WARNINGS**

All test commands pass with real runtime evidence (37/37 machine tests, `tsc` clean, full-suite baseline of 18 failures preserved — no new failures), and 25/29 spec scenarios are test-covered and green. Two scenarios are PARTIAL, the two index-error scenarios are UNTESTED, and there is one spec↔design drift plus a branch-scoped summary edge case — none of which block release.
