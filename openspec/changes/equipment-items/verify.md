# Verification Report

**Change**: equipment-items
**Version**: N/A (delta spec)
**Mode**: Standard
**Branch**: `feature/machines` (review branch, NOT merged)
**Verified commit**: `da7a506` (HEAD)

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 19 |
| Tasks complete | 18 |
| Tasks incomplete | 1 (`5.2` — live-Firebase E2E, infra-dependent) |

## Build & Tests Execution

**Build**: ✅ Passed
```text
$ npx tsc --noEmit   (frontend/)
EXIT: 0  (no diagnostics)
```

**Tests (target)**: ✅ 63 passed / ❌ 0 failed / ⚠️ 0 skipped
```text
$ python -m pytest backend/tests/routes/test_machines.py -v
63 passed, 63 warnings in 9.81s
```
Covers all 26 new item cases (create/filter/summary/maintenance/PUT) plus the 37 pre-existing machine cases.

**Tests (full suite)**: ✅ No new failures
```text
feature/machines : 18 failed, 352 passed
base dd2f82e     : 18 failed, 326 passed   (verified in throwaway worktree with .env + serviceAccountKey.json)
```
The SAME 18 tests fail on both refs (`test_plans`, `test_users`, `test_dashboard`, `test_client`). Those files are untouched by this change and the failures are pre-existing/environmental. Net delta = **+26 passing, +0 failing**.

**Coverage**: ➖ Not available (no coverage runner configured for this repo).

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Equipment Kind Field | Legacy document defaults to machine | `test_machines.py > TestListMachines::test_list_legacy_active_included_and_deleted_excluded`, `TestListKindFilter::test_filter_machine_includes_legacy`, `TestMaintenanceOnItem::test_legacy_doc_maintenance_still_201` | ✅ COMPLIANT |
| Equipment Kind Field | Item document shape | `TestCreateItem::test_item_create_201_stores_fields` | ✅ COMPLIANT |
| Conditional Create Validation | Item created with quantity | `TestCreateItem::test_item_create_201_stores_fields` | ✅ COMPLIANT |
| Conditional Create Validation | Item quantity defaults to 1 | `TestCreateItem::test_item_quantity_defaults_to_one` | ✅ COMPLIANT |
| Conditional Create Validation | Invalid item quantity | `TestCreateItem::test_item_invalid_quantity_400[0/-1/x/2.5/True]` | ✅ COMPLIANT |
| Conditional Create Validation | Invalid weightKg | `TestCreateItem::test_item_invalid_weight_400` | ✅ COMPLIANT |
| Conditional Create Validation | Unknown kind | `TestCreateItem::test_unknown_kind_400` | ✅ COMPLIANT |
| Conditional Create Validation | Machine path unchanged | `TestCreateMachine::test_create_valid_201_with_defaults`, `TestCreateItem::test_machine_kind_explicit_stored` | ✅ COMPLIANT |
| Kind Filter on List | Filter items | `TestListKindFilter::test_filter_item_only` | ✅ COMPLIANT |
| Kind Filter on List | Filter machines includes legacy | `TestListKindFilter::test_filter_machine_includes_legacy` | ✅ COMPLIANT |
| Kind Filter on List | No filter returns all | `TestListKindFilter::test_no_filter_returns_all` | ✅ COMPLIANT |
| Update Item Fields | Edit item quantity | `TestUpdateItem::test_update_item_quantity_200` | ✅ COMPLIANT |
| Update Item Fields | Invalid quantity rejected | `TestUpdateItem::test_update_item_invalid_quantity_400[-3/0/x]` | ✅ COMPLIANT |
| Machines Data Model (modified) | Machine document shape on create | `TestCreateMachine::test_create_valid_201_with_defaults` | ✅ COMPLIANT |
| Machines Data Model (modified) | Item document shape on create | `TestCreateItem::test_item_create_201_stores_fields` | ✅ COMPLIANT |
| List Machines (modified) | List with filters | `TestListMachines::test_list_filters_and_meta` | ✅ COMPLIANT |
| List Machines (modified) | Kind filter restricts results | `TestListKindFilter::test_filter_item_only` | ✅ COMPLIANT |
| List Machines (modified) | Legacy document treated as active | `TestListMachines::test_list_legacy_active_included_and_deleted_excluded` | ✅ COMPLIANT |
| Maintenance Summary (modified) | Summary split | `TestSummaryKindSplit::test_summary_split_machines_and_items` | ✅ COMPLIANT |
| Maintenance Summary (modified) | Item excluded from machine stats | `TestSummaryKindSplit::test_summary_split_machines_and_items` | ✅ COMPLIANT |
| Maintenance Summary (modified) | Items-only business | `TestSummaryKindSplit::test_items_only_business` | ✅ COMPLIANT |
| Add Maintenance Record (modified) | Maintenance rejected on item | `TestMaintenanceOnItem::test_maintenance_on_item_400` | ✅ COMPLIANT |
| Add Maintenance Record (modified) | Machine record still works | `TestMaintenanceOnItem::test_legacy_doc_maintenance_still_201`, `TestMaintenanceTransitions::*` | ✅ COMPLIANT |

**Compliance summary**: 23/23 scenarios compliant.

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| kind field + legacy default | ✅ Implemented | `_kind(doc) = doc.get('kind') or 'machine'` (`machines.py:95`); used in list, summary, update, maintenance. Frontend `machine.kind ?? 'machine'` in detail/list. |
| POST conditional validation | ✅ Implemented | `create_machine` branches on `kind`; unknown kind → 400 before branch; item requires `quantity` int ≥1 (bool/float rejected), `weightKg` num ≥0/null, category ∈ `ITEM_CATEGORIES`; machine branch verbatim. |
| GET kind filter | ✅ Implemented | Python filter `_kind(m) != kind` over the single `businessId`-scoped query; test asserts Firestore filters still only `businessId`. |
| Summary split | ✅ Implemented | `active_machines` drives `total`/`byStatus`/`upcomingMaintenance`; additive `items:{itemTypes,totalUnits}`; `totalUnits = Σ(int(q or 1))`. |
| Maintenance rejected on items | ✅ Implemented | Guard `if _kind(machine)=='item': return _error(400,'Los accesorios no tienen mantenimiento')` before any write. |
| PUT item fields | ✅ Implemented | Item branch accepts `quantity` (int ≥1) and `weightKg` (num ≥0/null) plus name/category/purchaseDate; invalid → 400. |
| Permissions unchanged | ✅ Implemented | `READ_ROLES`/`WRITE_ROLES` untouched; existing permission tests still pass. |
| Backward compat | ✅ Implemented | Legacy docs (no `kind`) treated as `machine` in list/summary/update/maintenance. |
| No new Firestore indexes | ✅ Verified | No `where` on `kind`; only `businessId` equality. Tests assert single-filter query. |
| Machine behavior byte-identical | ✅ Verified | Machine POST/PUT branches are the original logic; the only additions are `kind:'machine'` on the new record and `accessory` added to `VALID_CATEGORIES` (both spec-mandated, additive). |
| Two-tab UI + nav rename | ✅ Implemented | `MachinesPage` tab state `'machine'|'item'`, per-tab list/summary/create; `Layout` label "Máquinas" → "Equipamiento"; detail hides maintenance for items. |

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| 1. Kind stored on `machines` docs, default `machine` | ✅ Yes | No parallel collection. |
| 2. `_kind()` normalization for legacy | ✅ Yes | Single compat point. |
| 3. Global category set; item subset `free_weights/accessory/other` | ✅ Yes | `VALID_CATEGORIES` gains `accessory`; `ITEM_CATEGORIES` subset enforced getest. |
| 4. Validation branch, machine path verbatim | ✅ Yes | Confirmed via diff; item logic isolated in `if kind == 'item'`. |
| 5. Item defaults (status operational, isActive true, maintenance null) | ✅ Yes | Item record sets these explicitly. |
| 6. Summary additive `items` block | ✅ Yes | Machine keys stable; `items` added. |
| 7. Maintenance guard after fetch | ✅ Yes | Guard placed after `_fetch_active_machine` + scope check, before write. |
| 8. List `kind` filtered in Python | ✅ Yes | Only `businessId` reaches Firestore. |
| 9. Frontend tabs + kind-aware form | ✅ Yes | `MachinesPage` tabs + `MachineForm` branch. |
| 10. Detail hides maintenance for items | ✅ Yes | `isItem` gates Historial + maintenance modal; shows quantity/weight. |
| Open Q: items reject cardio/strength | ✅ Yes | Chosen option implemented. |
| Open Q: PUT keeps item status fixed | ✅ Yes | Item update branch ignores `status`. |

## Issues Found

**CRITICAL**: None.

**WARNING**:
1. **Spec data-model prose vs machine docs.** The MODIFIED `Machines Data Model` requirement states every document SHALL carry `quantity` (int, default 1) and `weightKg` (number|null). Machine docs created by `create_machine` include `kind:'machine'` but NOT `quantity`/`weightKg`. The binding scenario ("Machine document shape on create") lists only the original model fields + status/isActive and passes. Benign in practice: no code path reads `quantity`/`weightKg` for `kind='machine'`, and `_kind()` is the only normalization required. Recommend tightening the spec wording to scope `quantity`/`weightKg` to item docs (or add a machine-scenario clause) so spec and implementation agree.
2. **Task `5.2` incomplete (live-Firebase E2E).** The two-tab UI, kind filter and summary split were verified with mocked route tests + static inspection only; no live Firebase end-to-end run was performed. This is an infra-dependent verification task, not a core implementation task.

**SUGGESTION**:
1. `list_machines` docstring (Query Params) does not mention the new `kind` param; `machines_summary` docstring still describes `total` without noting it is now machines-only. Update docstrings for maintainability.
2. Design "Open Questions" remain unchecked in `design.md` although the chosen options were implemented — mark them resolved.

## Verdict

**PASS WITH WARNINGS**

All 23 spec scenarios are compliant with passing covering tests (63/63 route tests), `tsc --noEmit` exits 0, and the full suite shows zero new failures versus the base commit. The two warnings are a spec-wording inconsistency (no functional impact) and an infra-dependent E2E task left intentionally open.
