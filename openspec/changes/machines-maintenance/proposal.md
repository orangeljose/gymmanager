# Proposal: Equipment / Machine Inventory + Maintenance Tracking

## Intent

Staff can't tell which machines exist, which are operational, which are due for preventive maintenance, or what repairs happened. This adds a `machines` module to inventory equipment and log maintenance, so admins act before a machine breaks down.

## Scope

### In Scope
- Firestore `machines`: `{id,name,brand,model,category,purchaseDate,warrantyUntil,businessId,branchId,status,nextMaintenanceDate,isActive}`.
- Firestore `machine_maintenance`: `{id,machineId,machineName,type,description,date,costCents,technician,status,resolvedStatus,businessId,branchId,registeredBy,registeredByName,createdAt}`.
- `backend/routes/machines.py`: list/create/update/soft-delete machines; list/add maintenance; summary.
- `MachinesPage.tsx` (list, filters, search, status badges) + `MachineDetailPage.tsx` (history, log modal, status update).
- Sidebar "Máquinas" (`Dumbbell`) + routes `/machines`, `/machines/new`, `/machines/:id`.

### Out of Scope
- Cash/stock/products (next module — keep machines standalone).
- QR codes (future seam only); editing records; scheduled notifications.

## Capabilities

### New Capabilities
- `machine-inventory`: machine registry, lifecycle status, CRUD, branch/business scoping.
- `machine-maintenance`: maintenance/repair records, status transitions, summary.

### Modified Capabilities
- None.

## Approach

Follow the attendance pattern: deterministic ids, denormalized `machineName`, one scoped query + in-memory grouping (no N+1), register `machines_bp` in `app.py` and `routes/__init__.py`. Machine `status` derives from a completed repair's `resolvedStatus`; preventive records update `nextMaintenanceDate`. Summary counts in memory over one scoped `machines` query (10–50 docs, cheap). Reuse `auth_middleware` for scoping.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/routes/machines.py` | New | Blueprint, 7 endpoints |
| `backend/routes/__init__.py` | Modified | Export `machines_bp` |
| `backend/app.py` | Modified | Register blueprint |
| `frontend/src/pages/MachinesPage.tsx` | New | List + filters |
| `frontend/src/pages/MachineDetailPage.tsx` | New | Detail + history + log modal |
| `frontend/src/services/api.ts` | Modified | Machine fetchers |
| `frontend/src/types/index.ts` | Modified | Machine types |
| `frontend/src/components/Layout.tsx` | Modified | Sidebar entry |
| `frontend/src/App.tsx` | Modified | `/machines` routes |
| Firestore `machines` + `machine_maintenance` + 3 indexes | New | manual, console |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Missing composite indexes | High | Document + surface index-error link |
| Quota exhaustion (Spark) | Med | One scoped query + memory grouping |
| N+1 on maintenance lookup | Med | Single scoped query grouped by `machineId` |
| Cross-branch leakage | Low | Middleware `validate_branch_access` |

## Rollback Plan

Remove `machines.py`, unregister it, revert `__init__.py`/`app.py`, sidebar, `App.tsx` routes, API/types additions. Collections stay dormant. Additive-only; nothing existing is mutated.

## Dependencies

- 3 manual composite indexes: machines `businessId+category`, `businessId+status`; machine_maintenance `businessId+machineId`.
- `lucide-react` `Dumbbell`/`Wrench` icons (installed).

## Success Criteria

- [ ] Machines CRUD scoped by business + branch; soft-delete sets `isActive:false`.
- [ ] Completing a repair sets machine `status` from `resolvedStatus`.
- [ ] Summary returns status totals, upcoming maintenance (7 days), recent repairs.
- [ ] All queries scoped, no full scan, no N+1.
- [ ] CRUD + maintenance for super_admin/admin/branch_admin; GET + summary for all roles incl. cashier/trainer.
