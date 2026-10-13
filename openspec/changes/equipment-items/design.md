# Design: Equipment Items — quantity-based equipment (`kind='item'`)

## Technical Approach

Extend the existing `machines` module with a discriminator field `kind`, reusing the same
collection, blueprint and Python-side filtering. No new collection, route, index, or migration. A
`_kind(doc)` helper normalizes legacy documents to `machine`. Validation branches on `kind`;
summary stays a single scoped query split by kind in Python. The frontend reuses the list/query
layer with a `kind` param and adds tabs inside `MachinesPage`.

## Architecture Decisions

| # | Decision | Choice | Rationale / Alternatives |
|---|----------|--------|--------------------------|
| 1 | Kind storage | One `kind` field on `machines` docs, explicit on create, default `machine` | Avoids a parallel module; legacy-safe via `_kind()`. Rejected: separate `equipment_items` collection (new queries/indexes, dup UI). |
| 2 | Normalization | `_kind(m) = m.get('kind') or 'machine'` used in list, summary, detail, update, maintenance | Single compat point. Rejected: data migration (out of scope, quota risk). |
| 3 | Category set | Global `cardio,strength,functional,free_weights,accessory,other`; item subset `free_weights,accessory,other` | Additive only (nothing removed). Items reject `cardio/strength` as physically meaningless. |
| 4 | Validation branch | `if kind == 'item'` → validate `quantity`/`weightKg`/item-category; else existing path verbatim | Keeps machine path byte-identical → zero machine regression. |
| 5 | Item defaults | Items stored `status='operational'`, `isActive=true`, maintenance fields null | Detail page can hide maintenance cleanly; no status machine needed. |
| 6 | Summary shape | Keep `total/byStatus/upcomingMaintenance/recentRepairs` computed over `kind=='machine'`; add `items:{itemTypes,totalUnits}` | Additive keys; consumers unaffected. Note: `total` now means machines only (items counted in `items`). |
| 7 | Maintenance guard | After `_fetch_active_machine`, `if _kind(machine)=='item': return _error(400, 'Los accesorios no tienen mantenimiento')` | Cheapest, before any write; one test. |
| 8 | List filter | `kind` param filtered in Python alongside `category`/`status` | No new composite index; single scoped query preserved. |
| 9 | Frontend tabs | `MachinesPage` tab state `'machines'|'items'`; item tab queries `kind='item'`; `MachineForm` branches on `kind` | Reuses existing page/list/form. |
| 10 | Detail page | For items hide Historial + maintenance modal, show `quantity`/`weightKg` | Minimal conditional render; no new route. |

## Data Flow

    MachinesPage(tab) ──getMachines({kind})──► GET /machines ──where(businessId)──► Firestore machines
        │                                        └── Python: _kind filter + category/status
        └──getMachinesSummary()──► GET /machines/summary ── Python split by _kind ──┐
                                                                     machine stats + items block ─┘
    MachineDetailPage(item) ── hides maintenance section, shows quantity/weight
    MachineForm(kind) ──POST/PUT ──► kind-branched validation ──► machines

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/routes/machines.py` | Modify | `_kind()` helper; `kind` + item-category constants; kind-branched POST validation; `quantity`/`weightKg` (+ item fields) on create/update; `kind` list filter; kind-split summary; maintenance 400 guard |
| `backend/tests/routes/test_machines.py` | Modify | Add kind cases (validation, filter, summary split, maintenance-on-item, legacy default) |
| `frontend/src/types/index.ts` | Modify | `MachineKind`, `accessory` category, `kind`/`quantity`/`weightKg` on `Machine` + `MachineFormData`, `items` block on `MachinesSummary`, `kind` on `MachineFilters` |
| `frontend/src/services/api.ts` | Modify | Append `kind` param in `getMachines` |
| `frontend/src/components/MachineForm.tsx` | Modify | Branch fields on `kind` (machine vs item); item shows `weightKg`, `quantity` |
| `frontend/src/pages/MachinesPage.tsx` | Modify | Tab state, per-tab list + summary cards, item create |
| `frontend/src/pages/MachineDetailPage.tsx` | Modify | Hide maintenance for items; show quantity/weight |
| `frontend/src/components/Layout.tsx` | Modify | Nav label "Máquinas" → "Equipamiento" |

## Interfaces / Contracts

```ts
export type MachineKind = 'machine' | 'item';
export type MachineCategory = 'cardio' | 'strength' | 'functional' | 'free_weights' | 'accessory' | 'other';

// Machine gains:
kind?: MachineKind;            // absent legacy doc ⇒ 'machine'
quantity?: number;             // items, default 1
weightKg?: number | null;      // items, optional

// MachineFormData gains the same three optional fields.
// MachineFilters gains: kind?: MachineKind | '';

export interface MachinesSummary {
  total: number;               // machines only
  byStatus: Record<MachineStatus, number>;
  upcomingMaintenance: Machine[];
  recentRepairs: MachineMaintenance[];
  items: { itemTypes: number; totalUnits: number }; // additive
}
```

Endpoint behavior: `GET /api/machines?kind=item|machine`; `POST`/`PUT` accept `kind` and item
fields; all permissions unchanged (`GET`/summary all roles, writes admin+).

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (route) | Conditional POST validation (item quantity/weightKg/category, machine unchanged), unknown kind 400, PUT item fields | `pytest` + `MagicMock` FirebaseService (existing `prime_app_modules` fixture) |
| Unit (route) | `kind` list filter (item only, machine includes legacy), no filter returns all | Assert filtered ids + single-query `filters` arg |
| Unit (route) | Summary split: `total`/`byStatus`/`upcomingMaintenance` over machines only; `items.itemTypes`/`totalUnits`; one query per collection | Mocked `query_firestore` side_effect |
| Unit (route) | Maintenance on item → 400 "accesorios", no `create_document`; legacy doc (no kind) maintenance still 201 | Assert status + `create_document.assert_not_called()` |
| Frontend | Tab switch, item form branch, detail hides maintenance | Manual / component-level (existing frontend has no test runner) |

## Migration / Rollout

No data migration and **no new composite indexes**: `kind`/`category`/`status` are filtered in
Python; the `machines` query still filters only `businessId` (single-field index). Additive writes
and additive response keys keep existing machine consumers working. Rollback = drop the new writes
and UI branches; docs with `kind` simply read as their stored value.

## Open Questions

- [ ] Confirm items MUST reject `cardio`/`strength` categories (chosen) vs. allowing any category for flexibility.
- [ ] Should `PUT` allow changing an item's `status`, or keep items fixed at `operational`? (Chosen: items stay `operational`.)
