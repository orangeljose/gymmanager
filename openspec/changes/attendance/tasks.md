# Tasks: Client Attendance Tracking

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~900-1,150 (mostly new files) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 backend → PR 2 frontend → PR 3 tests + manual |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

NOTE: this run applies all slices on one `feature/attendance` branch; user reviews before merge.

### Suggested Work Units

| Unit | Goal | Likely PR |
|------|------|-----------|
| 1 | Backend blueprint + config + wiring | PR 1 (base main) |
| 2 | Frontend types/api/page/nav/route | PR 2 (base PR 1) |
| 3 | Backend tests + manual indexes | PR 3 (base PR 2) |

## Phase 1: Backend Foundation & Wiring

- [x] 1.1 `backend/config.py` — add `TIMEZONE = os.environ.get('BUSINESS_TIMEZONE', 'America/Caracas')` to `Config`.
- [x] 1.2 `backend/routes/attendance.py` (NEW) — create `attendance_bp` (`url_prefix='/api/attendance'`); import `ZoneInfo`; add `_business_today()` and `_index_error_response()`.
- [x] 1.3 `backend/routes/__init__.py` — import + add `attendance_bp` to `__all__`.
- [x] 1.4 `backend/app.py` — import `attendance_bp` (L17) and `register_blueprint` (after `clients_bp`).

## Phase 2: Backend Endpoints

- [x] 2.1 `POST ''` — `@require_role([...cashier])`; validate `clientId`, `method ∈ manual|qr|biometric` (default `manual`) else 400; fetch client (404 missing/deleted), scope 403; id = `{clientId}_{date}`; `get_document` → 200 `alreadyCheckedIn:true`, else `set_document` → 201 `alreadyCheckedIn:false`.
- [x] 2.2 `GET ''` — `@require_auth` (all roles); filters `businessId` (+`user.branchId` if scoped) `date` (default today), optional `branchId`/`clientId`; ONE `query_firestore`; Python sort desc + paginate; return `{data, meta{total,page,limit,pages}, summary{total,byMethod}}`.
- [x] 2.3 `GET '/client/<client_id>'` — fetch client, 404 missing/deleted, scope 403; query by `clientId`+`businessId`; return history desc + `stats{total,thisMonth,lastVisit}`.
- [x] 2.4 `GET '/stats'` — ONE bounded query `businessId` [branch] `date>=today-29` `date<=today`; Python group today/rolling-7/rolling-30, `series7`/`series30`, `topAttendees` (Counter by clientId); return `AttendanceStats`.
- [x] 2.5 Wrap queries: `FAILED_PRECONDITION` → 500 message referencing console index. (best-effort: `FirebaseService.query_firestore` swallows errors; helper guards now/future)

## Phase 3: Frontend Foundation

- [x] 3.1 `frontend/src/types/index.ts` — add `AttendanceMethod`, `AttendanceRecord`, `AttendanceStats`, `AttendanceFilters`. (plus `AttendanceSeriesPoint`, `AttendanceTopAttendee`, `AttendanceSummary`, `ClientAttendanceStats`)
- [x] 3.2 `frontend/src/services/api.ts` — add `registerAttendance`, `getAttendance`, `getClientAttendance`, `getAttendanceStats` (auth, query params).

## Phase 4: Frontend UI & Wiring

- [x] 4.1 `frontend/src/pages/AttendancePage.tsx` (NEW) — client search (reuse `getClients({search})`), select + "Registrar Asistencia", today list, cards, recharts 7-day chart, toast when `alreadyCheckedIn`.
- [x] 4.2 `frontend/src/App.tsx` — import page + `/attendance` route with ProtectedRoute, roles `super_admin,admin,branch_admin,cashier,trainer`.
- [x] 4.3 `frontend/src/components/Layout.tsx` — nav "Asistencia" (`UserCheck`) after Clientes; add to `iconMap`.

## Phase 5: Tests

- [x] 5.1 `backend/tests/routes/test_attendance.py` (NEW) — POST 201, repeat 200 `alreadyCheckedIn`, invalid method 400, client 404/deleted, cross-business 403, branch scope, deterministic id `clientId_date`, trainer POST 403, trainer GET 200. (20 tests pass)
- [x] 5.2 Same file — stats grouping boundaries (today/rolling-7/rolling-30), series lengths, `topAttendees`; list pagination + summary; mock `FirebaseService`. (NOTE: used a corrected 3-point patch binding; the `test_plans.py` binding is broken/baseline-failing)
- [x] 5.3 Frontend — `npm run build` (tsc `--noEmit` + vite) passes.

## Phase 6: Manual (pre-deploy)

- [ ] 6.1 MANUAL: Firebase console — indexes `attendance (businessId, date)` and `(businessId, branchId, date)`; verify no `FAILED_PRECONDITION`.
