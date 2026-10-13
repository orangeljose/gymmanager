# Tasks: Equipment / Machine Inventory + Maintenance Tracking

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,600–2,000 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 backend inventory → PR2 backend maintenance → PR3 frontend wiring → PR4 frontend pages |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend inventory CRUD + registration + inventory tests | PR 1 | base `main` |
| 2 | Backend maintenance + summary + tests | PR 2 | base `main`; depends on PR 1 |
| 3 | Frontend types/api/routes/nav wiring | PR 3 | base `main`; needs PR 1 API |
| 4 | Frontend pages + shared form + theme | PR 4 | base `main`; depends on PR 3 |
| 5 | Manual indexes + docs + final verify | ops | no code PR |

## Phase 1: Foundation

- [x] 1.1 Add `Machine`, `MachineMaintenance`, `MachineStatus`, `MachineCategory`, `MachineMaintenanceType`, `MachineMaintenanceStatus` to `frontend/src/types/index.ts`
- [x] 1.2 Create `backend/routes/machines.py`: `machines_bp` prefix `/api/machines`, constants `VALID_CATEGORIES`/`VALID_STATUSES`/`POST_ROLES`/`READ_ROLES`
- [x] 1.3 Export `machines_bp` in `backend/routes/__init__.py`; import + `register_blueprint` in `backend/app.py`

## Phase 2: Backend — Inventory

- [x] 2.1 `GET /` — one scoped query; Python filter `category`/`status`/`search`/`branchId`; paginate; exclude `isActive:false`, treat missing as active; `meta{total,page,limit,pages}`
- [x] 2.2 `GET /<id>` — 404 if missing or `isActive:false`; scope 403
- [x] 2.3 `POST /` — validate non-empty `name`, allowed `category`, branch scope; defaults `status='operational'`, `isActive=true`; 201
- [x] 2.4 `PUT /<id>` — 404 missing/inactive; update fields including `status`
- [x] 2.5 `DELETE /<id>` — soft delete `{isActive:false,deletedBy,deletedAt}`; document retained

## Phase 3: Backend — Maintenance & Summary

- [x] 3.1 `GET /<id>/maintenance` — single query `businessId+machineId`; sort `date` DESC; paginate
- [x] 3.2 `POST /<id>/maintenance` — validate machine exists/active/scope and `type in preventive|repair`; denormalize `machineName`; 201
- [x] 3.3 Transition: `repair` + `completed` → `machine.status=resolvedStatus`; reject completed repair without `resolvedStatus` (400)
- [x] 3.4 Transition: `preventive` + `completed` → `nextMaintenanceDate=date+90d` (explicit override allowed); `scheduled`/`in_progress` → `maintenance`
- [x] 3.5 `GET /summary` — one scoped machines query → Python `total`/`byStatus`/upcoming (≤now+7d); `recentRepairs` = one query `date` DESC limit 5
- [x] 3.6 Add `_index_error_response` helper returning actionable 500 on missing-index errors

## Phase 4: Backend Tests (`backend/tests/routes/test_machines.py`)

- [x] 4.1 Port `prime_app_modules` + `make_client` fixtures; patch `routes.machines`, `middleware.auth_middleware`, `services.firebase_service`
- [x] 4.2 List: filters, pagination, legacy-active inclusion, deleted exclusion
- [x] 4.3 Create valid / invalid (400) / cross-branch (403); update; soft-delete preserves doc
- [x] 4.4 Permissions: trainer POST 403, cashier GET 200, unauth 401
- [x] 4.5 Transitions: repair+completed→status; preventive→+90d and override; scheduled→`maintenance`
- [x] 4.6 Summary: `byStatus` counts, 7-day window, `recentRepairs`≤5, one query per collection
- [x] 4.7 History: order/pagination; cross-tenant 403/404

## Phase 5: Frontend Wiring

- [x] 5.1 Add 8 machine methods to `frontend/src/services/api.ts` (list/detail/create/update/delete/summary/maintenance-list/maintenance-add)
- [x] 5.2 Add `/machines` and `/machines/:id` routes (all roles) in `frontend/src/App.tsx`
- [x] 5.3 Add "Máquinas" (`Dumbbell`) nav after Clientes in `frontend/src/components/Layout.tsx`; register icon in `iconMap`

## Phase 6: Frontend Pages

- [x] 6.1 Create `frontend/src/components/MachineForm.tsx` — shared create/edit modal (name, brand, model, category, dates, status)
- [x] 6.2 Create `frontend/src/pages/MachinesPage.tsx` — summary cards, filters, search, status badges, create modal
- [x] 6.3 Create `frontend/src/pages/MachineDetailPage.tsx` — ficha, history, log modal, status update, edit modal
- [x] 6.4 Apply GoatGym orange theme + status badge colors across both pages

## Phase 7: Manual Indexes & Verification

- [ ] 7.1 Create Firebase-console composite indexes: `machine_maintenance (businessId ASC, machineId ASC)` and `(businessId ASC, date DESC)`; record in docs — docs recorded in `indexes.md`; **console creation pending (manual ops)**
- [x] 7.2 Run `pytest backend/tests/routes/test_machines.py` and `npm run build` (frontend)
- [ ] 7.3 Manually verify inventory + maintenance spec scenarios end-to-end via API — **pending (requires live Firebase)**
