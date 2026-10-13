# Design: Equipment / Machine Inventory + Maintenance Tracking

## Technical Approach

Mirror the attendance blueprint (`backend/routes/attendance.py`): a single `machines_bp` over two collections (`machines`, `machine_maintenance`), business/branch scoping from `g.current_user`, equality filters in Firestore, and all aggregation/grouping in Python. Status transitions are computed inline in the maintenance POST handler via `update_document` — no new service class or model schema (machine volume is 10–50 docs/business).

## Architecture Decisions

| # | Decision | Choice | Rationale / Alternatives |
|---|----------|--------|--------------------------|
| 1 | Blueprint & registration | New `routes/machines.py` (`machines_bp`, prefix `/api/machines`); export in `routes/__init__.py` AND import+register in `app.py` | Matches attendance exactly (both registration sites). |
| 2 | Transition logic location | Inline in route handler calling `FirebaseService.update_document` | Same as attendance; a `MachinesService` adds indirection for ~15 lines. |
| 3 | Machine `status` from repairs | On record `status=='completed'` + `type=='repair'` → `machine.status = resolvedStatus` (`operational`/`out_of_service`) | Status is derived, not manually toggled. |
| 4 | Preventive interval | On `type=='preventive'` + `status=='completed'` → `machine.nextMaintenanceDate = date + 90d`; flip `status` to `operational` only if currently `maintenance` | 90d is the default; don't resurrect an `out_of_service` machine. |
| 5 | In-progress/scheduled | `status in ('scheduled','in_progress')` → `machine.status='maintenance'` | Surfaces "being worked on". |
| 6 | Summary quota | 1 scoped `machines` query → Python counts (`byStatus`) + upcoming (`nextMaintenanceDate <= now+7d`) | Low volume. Avoids range indexes on `machines`. |
| 7 | Recent repairs | 1 query `machine_maintenance` (businessId, `order_by=date DESC`, `limit=5`) | Bounded reads as maintenance grows; requires index (businessId, date DESC). |
| 8 | Soft delete | `DELETE` → `update {isActive:false, deletedBy, deletedAt}`; list excludes `isActive===false`; GET-by-id → 404 | Follows delete-client audit fields. Proposal field is `isActive`. |
| 9 | Machine form | Shared `MachineForm.tsx` rendered in a modal from both list (create) and detail (edit); NO `/machines/new` route | DRY; modal fits the existing page style. |
| 10 | Nav order | "Máquinas" (`Dumbbell`) after "Clientes", before "Asistencia"; roles = all | Machines are an operational hub, higher than attendance. |

## Data Flow

    MachinesPage ──getMachines()────► GET /machines ──where(businessId)──► Firestore machines
         │                                                                        │
         └──getMachinesSummary()──► GET /machines/summary ◄── python counts ──────┘
    MachineDetailPage ──getMachine(id)/getMachineMaintenance(id)──► machine_maintenance
         └──addMachineMaintenance(id,rec)──► POST /machines/<id>/maintenance
                                              ├─ create record
                                              └─ update machine.status / nextMaintenanceDate

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/routes/machines.py` | Create | Blueprint, 8 endpoints |
| `backend/routes/__init__.py` | Modify | Export `machines_bp` |
| `backend/app.py` | Modify | Import + `register_blueprint(machines_bp)` |
| `backend/tests/routes/test_machines.py` | Create | Route tests (isolation-safe fixture) |
| `frontend/src/pages/MachinesPage.tsx` | Create | List, filters, summary cards |
| `frontend/src/pages/MachineDetailPage.tsx` | Create | Ficha, history, log modal |
| `frontend/src/components/MachineForm.tsx` | Create | Shared create/edit modal |
| `frontend/src/services/api.ts` | Modify | 7 machine methods |
| `frontend/src/types/index.ts` | Modify | Machine types |
| `frontend/src/App.tsx` | Modify | `/machines`, `/machines/:id` (all roles) |
| `frontend/src/components/Layout.tsx` | Modify | Nav item + `Dumbbell` icon |

## Interfaces / Contracts

Endpoints (`GET`/`summary` = all roles; `POST`/`PUT`/`DELETE`/maintenance-POST = super_admin/admin/branch_admin):

| Method & Path | Notes |
|---|---|
| `GET /api/machines` | `?category=&status=&search=&branchId=&page=&limit=`; category/status/search filtered in Python |
| `GET /api/machines/<id>` | Detail; 404 if missing or `isActive===false` |
| `POST /api/machines` | Create (`create_document`) |
| `PUT /api/machines/<id>` | Update |
| `DELETE /api/machines/<id>` | Soft delete |
| `GET /api/machines/summary` | `{total, byStatus:{operational,maintenance,out_of_service}, upcomingMaintenance:[...], recentRepairs:[...]}` |
| `GET /api/machines/<id>/maintenance` | History, sorted `date` DESC |
| `POST /api/machines/<id>/maintenance` | Create record + status transition |

```ts
export type MachineStatus = 'operational' | 'maintenance' | 'out_of_service';
export type MachineCategory = 'cardio' | 'strength' | 'functional' | 'free_weights' | 'other';
export type MachineMaintenanceType = 'preventive' | 'repair';
export type MachineMaintenanceStatus = 'scheduled' | 'in_progress' | 'completed';

export interface Machine { id: string; name: string; brand?: string; model?: string;
  category: MachineCategory; purchaseDate?: string; warrantyUntil?: string;
  businessId: string; branchId?: string | null; status: MachineStatus;
  nextMaintenanceDate?: string | null; isActive: boolean;
  deletedBy?: string; deletedAt?: string; createdAt: string; }

export interface MachineMaintenance { id: string; machineId: string; machineName: string;
  type: MachineMaintenanceType; description?: string; date: string; costCents?: number;
  technician?: string; status: MachineMaintenanceStatus;
  resolvedStatus?: 'operational' | 'out_of_service'; businessId: string; branchId?: string | null;
  registeredBy: string; registeredByName: string; createdAt: string; }
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (route) | CRUD, role gates, scope 403/404, soft-delete exclusion | `pytest` + `MagicMock` FirebaseService, patching `routes.machines` + `middleware.auth_middleware` + `services.firebase_service` |
| Unit (logic) | repair+completed→status; preventive+completed→+90d; scheduled/in_progress→`maintenance` | Assert `update_document` args on the `machines` collection |
| Unit (summary) | `byStatus` counts, 7-day upcoming window, recentRepairs limit 5 | Mocked `query_firestore` returns; assert single query per collection |
| Isolation | Prime `app` modules with a `super_admin` mock first | Copy `prime_app_modules` fixture from `test_attendance.py` |

## Migration / Rollout

No data migration (additive collections). Create 2 composite indexes manually in the Firebase console:

- `machine_maintenance` (businessId ASC, machineId ASC) — per-machine history.
- `machine_maintenance` (businessId ASC, date DESC) — summary recent repairs.

**Not needed** (verified): proposal's `machines (businessId, category)` and `(businessId, status)`. `category`/`status`/`branchId` are filtered in Python; the `machines` query only filters `businessId` (equality) → automatic single-field index suffices.

## Open Questions

- [ ] If maintenance volume ever makes the 5-doc recent query the dominant read, add a per-machine rollup. Not needed now.
- [ ] Confirm whether trainers should also log repairs (`server` currently restricts to admin+ per proposal success criteria).
