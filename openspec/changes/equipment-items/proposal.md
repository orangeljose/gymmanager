# Proposal: Equipment Items (free weights / accessories in quantity)

## Intent

The gym owns equipment sold/used in QUANTITIES (dumbbells, discos, bands, mats) with no maintenance and a per-unit weight — it does NOT fit the per-unit `machines` model. Staff need to register these cleanly alongside machines without a second, parallel module.

## Scope

### In Scope
- Extend `machines` docs: `kind` (`machine|item`, default `machine`), `quantity` (default 1), `weightKg` (`number|null`).
- `backend/routes/machines.py`: kind-aware POST validation, `kind` list filter, kind-split summary, item-editable PUT, maintenance rejected on items (400).
- Frontend: `MachinesPage.tsx` → "Equipamiento" with TABS "Máquinas" / "Pesas y Accesorios"; kind-aware `MachineForm.tsx`; summary cards per tab; item detail shows quantity/weight; sidebar label → "Equipamiento".
- Backend tests: conditional validation, kind filter, summary split, maintenance-rejected-on-item.

### Out of Scope
- Separate collection or migration script; QR codes; stock movements/consumption; barcode; notifications.

## Capabilities

### New Capabilities
- `equipment-items`: quantity-based equipment (kind='item') registry — model fields, conditional create/update validation, kind filter, item summary (total units + type count).

### Modified Capabilities
- `machine-inventory`: adds `kind` field (default `machine`), `kind` query filter, and conditional validation branching on `kind`. Existing machine behavior unchanged.
- `machine-maintenance`: maintenance endpoints MUST reject `kind='item'` (400); summary SHALL split machine counts (by status, kind='machine') from item aggregates (kind='item').

## Approach

Reuse the existing blueprint/page — NO new collection, route, or index. `kind` is filtered in Python like `category`/`status`, so existing `businessId`-scoped queries and indexes keep working. Missing `kind` is treated as `machine` (backward compat) via a `_kind(doc)` helper. Frontend reuses the list/query layer with a `kind` param; the form branches on `kind`; one summary endpoint returns both machine and item blocks so each tab reads its slice.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/routes/machines.py` | Modified | `kind` validation, filter, summary split, maintenance guard |
| `backend/tests/test_machines*.py` | Modified | kind cases |
| `frontend/src/pages/MachinesPage.tsx` | Modified | Tabs + item list |
| `frontend/src/components/MachineForm.tsx` | Modified | kind-aware fields |
| `frontend/src/pages/MachineDetailPage.tsx` | Modified | item detail (qty/weight) |
| `frontend/src/services/api.ts` | Modified | `kind` param |
| `frontend/src/types/index.ts` | Modified | `kind`/`quantity`/`weightKg` |
| `frontend/src/components/Layout.tsx` | Modified | Label → "Equipamiento" |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Legacy docs miscounted as items | Low | `_kind()` defaults missing → `machine` |
| Maintenance accidentally allowed on items | Med | Explicit 400 guard + test |
| Summary shape breaks existing consumers | Med | Additive fields; keep machine keys stable |
| Quota regression | Low | No new queries/indexes; Python filtering |

## Rollback Plan

Revert commits on `feature/machines`; additive-only — drop `kind`/`quantity`/`weightKg` writes and the tab/form branches. Existing machine code paths stay intact; docs with the new fields simply read as `machine`. No data migration to undo.

## Dependencies

- Active `machines-maintenance` change (same branch) provides `machines` module + `machine-inventory`/`machine-maintenance` specs.
- `lucide-react` icons (installed).

## Success Criteria

- [ ] POST/PUT validate by `kind` (item requires `quantity>=1`; `weightKg` optional); machine path unchanged.
- [ ] `GET /api/machines?kind=item|machine` filters; no `kind` returns all; legacy docs = machine.
- [ ] Summary returns machine status counts + item total units and type count.
- [ ] Maintenance on an item returns 400 with a clear message.
- [ ] Two tabs render their own list, "+ Agregar", and summary cards.
- [ ] No new composite indexes; all queries scoped, no N+1.
