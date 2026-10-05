# Proposal: Client Attendance Tracking

## Intent

Gyms can't see who attends. This adds an `attendance` module: a front-desk UI for check-ins, on an endpoint a future QR/biometric scanner can call unchanged.

## Scope

### In Scope
- Firestore collection `attendance` (one doc/check-in: `businessId`, `branchId`, `clientId`, `clientName`, `method`, `date`, `createdAt`).
- `backend/routes/attendance.py` blueprint:
  - `POST /api/attendance` — validate client + business/branch, denormalize `clientName`; `method` ∈ `manual|qr|biometric` (default `manual`).
  - `GET /api/attendance` — filters (`date`, `clientId`, `branchId`, `page`, `limit`) + daily summary.
  - `GET /api/attendance/client/:clientId` — history + stats.
  - `GET /api/attendance/stats` — today/week/month, top attendees, 7/30-day series.
- `AttendancePage.tsx`: search + "Registrar asistencia", today's list, stat cards (hoy/semana/mes), recharts chart.
- Sidebar "Asistencia" (`UserCheck`) + `/attendance` route.

### Out of Scope
- QR/biometric device integration (contract only); record edit/delete; unattended kiosk.

## Capabilities

### New Capabilities
- `attendance-tracking`: recording, querying, and aggregating check-ins with role/branch scoping.

### Modified Capabilities
- None.

## Approach

Store `date` (YYYY-MM-DD); queries filter `businessId` + `date` (or branch) in Firestore — never a scan. List/stats aggregate in Python from one scoped query (no N+1). Check-in = 1 read + 1 create. Reuse existing middleware; register in `app.py`.

POST `{clientId, method?, branchId?}` is the future seam. QR encodes `clientId` → scanner → POST `method='qr'`. Biometric maps fingerprint/face → `clientId` → POST `method='biometric'`. No later change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/routes/attendance.py` | New | Blueprint (4 endpoints) |
| `backend/app.py` | Modified | Register `attendance_bp` |
| `frontend/src/pages/AttendancePage.tsx` | New | UI (search, check-in, list, stats, chart) |
| `frontend/src/services/api.ts` | Modified | Attendance fetchers |
| `frontend/src/components/Layout.tsx` | Modified | Sidebar entry |
| `frontend/src/App.tsx` | Modified | `/attendance` route |
| Firestore `attendance` + index | New | `businessId ASC, date ASC` (manual, console) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Missing composite index | High | Document index; surface index-error link |
| Duplicate check-ins | Med | Optional same-day guard (spec) |
| Quota exhaustion | Med | One scoped query + in-memory grouping |
| Cross-branch leakage | Low | Middleware `validate_branch_access` |

## Rollback Plan

Remove `attendance.py`, unregister it, revert route/sidebar/API additions. Collection can stay dormant. Nothing existing is mutated — additive-only rollback.

## Dependencies

- Manual `businessId ASC, date ASC` index in Firebase console.
- `recharts` (installed).

## Success Criteria

- [ ] Check-in in ≤ 3 interactions; doc has `date` + `clientName`.
- [ ] List filters by date/client/branch + pagination + daily summary; stats accurate.
- [ ] All queries scoped, no full scan.
- [ ] Permissions: POST for super_admin/admin/branch_admin/cashier; GET adds trainer.
- [ ] QR/biometric path documented against the POST contract.
