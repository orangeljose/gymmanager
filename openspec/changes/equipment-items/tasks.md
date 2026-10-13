# Tasks: Equipment Items (quantity-based `kind='item'`)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~520–650 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 backend (routes + tests) → PR 2 frontend (types/api/UI) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend kind support + tests (self-contained, API verifiable) | PR 1 | base `feature/machines`; includes Phase 1 + 4 |
| 2 | Frontend item support (tabs/form/detail) | PR 2 | base PR 1 branch; needs PR 1 API |

## Phase 1: Backend — Model & Validation

- [x] 1.1 `backend/routes/machines.py`: add `VALID_KINDS=['machine','item']`, `ITEM_CATEGORIES=['free_weights','accessory','other']`; add `'accessory'` to `VALID_CATEGORIES`; add `_kind(doc)=doc.get('kind') or 'machine'`.
- [x] 1.2 `create_machine`: read `kind`, unknown → 400; item branch → validate name, `quantity` int ≥1 (default 1), `weightKg` number ≥0 or null, category in `ITEM_CATEGORIES`, store `status='operational'` and null maintenance dates; machine branch verbatim. Persist `kind`/`quantity`/`weightKg`.
- [x] 1.3 `list_machines`: read `kind` query param; Python-filter `_kind(m)==kind` when present.
- [x] 1.4 `update_machine`: if `_kind(machine)=='item'`, accept `quantity` (int ≥1) and `weightKg` (number ≥0/null), 400 on invalid; machine path unchanged.
- [x] 1.5 `machines_summary`: compute `total`/`byStatus`/`upcomingMaintenance` over `_kind=='machine'`; add `items:{itemTypes,totalUnits}` (count item docs, sum `quantity`); keep `recentRepairs` unchanged.
- [x] 1.6 `add_machine_maintenance`: after `_fetch_active_machine`, `if _kind(machine)=='item': return _error(400,'Los accesorios no tienen mantenimiento')` before any write.

## Phase 2: Frontend Foundation

- [x] 2.1 `frontend/src/types/index.ts`: add `MachineKind`, `'accessory'` to `MachineCategory`, `kind?`/`quantity?`/`weightKg?` on `Machine` + `MachineFormData`; add `items:{itemTypes,totalUnits}` to `MachinesSummary`; add `kind?:MachineKind|''` to `MachineFilters`.
- [x] 2.2 `frontend/src/services/api.ts`: append `kind` param in `getMachines`.

## Phase 3: Frontend UI

- [x] 3.1 `frontend/src/components/MachineForm.tsx`: accept `kind`; item → name, item-category set, `quantity`, `weightKg`, hide status/dates; machine → unchanged.
- [x] 3.2 `frontend/src/pages/MachinesPage.tsx`: tab state `'machines'|'items'`; items tab calls `getMachines({kind:'item'})`; per-tab summary cards (items: tipos/unidades); "+ Agregar" passes `kind`.
- [x] 3.3 `frontend/src/pages/MachineDetailPage.tsx`: for `_kind==='item'` hide Historial + maintenance modal; show `quantity`/`weightKg`.
- [x] 3.4 `frontend/src/components/Layout.tsx`: nav label "Máquinas" → "Equipamiento".

## Phase 4: Backend Tests (`backend/tests/routes/test_machines.py`)

- [x] 4.1 Item POST: 201 stores fields; quantity default 1; `quantity:0`/`'x'` → 400; `weightKg:-1` → 400; unknown kind → 400; machine path unchanged.
- [x] 4.2 GET `kind` filter: item-only; machine includes legacy; no param returns all.
- [x] 4.3 Summary split: 2 machines + 3 items (5,2,1) → `total` 2, `byStatus` machines only, `items` `{itemTypes:3,totalUnits:8}`; items-only business → total 0.
- [x] 4.4 Maintenance on item → 400 "accesorios" and `create_document` not called; legacy doc maintenance still 201.
- [x] 4.5 PUT item `{quantity:12}` → 200; `{quantity:-3}` → 400.

## Phase 5: Verification

- [x] 5.1 Run `pytest backend/tests/routes/test_machines.py`; run `npm run build` in frontend.
- [ ] 5.2 Verify spec scenarios end-to-end (both tabs, kind filter, summary split) — requires live Firebase.
