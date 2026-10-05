# Verification Report

**Change**: attendance
**Version**: N/A (spec at `openspec/changes/attendance/specs/attendance/spec.md`)
**Mode**: Standard (Strict TDD not active — no TDD config/runner requirement)
**Branch**: `feature/attendance` (review branch, not merged)

## Verdict

**FAIL** — Production code is functionally sound and all 20 attendance tests pass, but the change introduces **12 new full-suite failures** through a test-isolation leak, and **2 of 12 spec scenarios have no covering test** (QR/biometric scanner contract; missing composite index).

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 18 |
| Tasks complete | 17 |
| Tasks incomplete | 1 (task 6.1 — manual Firebase composite indexes) |

## Build & Tests Execution

**Build**: ✅ Passed
```text
$ npx tsc --noEmit   (frontend/)
EXITCODE=0
```

**Tests (change scope)**: ✅ 20 passed / 0 failed / 0 skipped
```text
$ python -m pytest backend/tests/routes/test_attendance.py -v
20 passed, 20 warnings in 5.62s
```

**Tests (full backend suite)**: ❌ 30 failed / 297 passed
```text
$ python -m pytest backend/tests -q
30 failed, 297 passed   (feature/attendance)

Baseline (main, same dir + same .env):
$ python -m pytest backend/tests -q
18 failed, 289 passed

Feature suite EXCLUDING the new test file:
$ python -m pytest backend/tests --ignore=backend/tests/routes/test_attendance.py -q
18 failed, 289 passed   ← identical node IDs to main baseline
```
**Conclusion**: The 12 extra failures are caused by `backend/tests/routes/test_attendance.py` polluting shared state. See CRITICAL-01.

**Coverage**: ➖ Not available (no coverage runner/config in project; pytest plugins are only `anyio`, `Faker`).

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| REQ-01 Data Model | Document shape on check-in | `test_attendance.py::TestRegisterAttendance::test_create_new_checkin_returns_201` | ⚠️ PARTIAL (asserts id/clientName/method/date; omits businessId, branchId, checkInAt, registeredBy, registeredByName, createdAt) |
| REQ-02 Register | Successful manual check-in | `...::test_create_new_checkin_returns_201` | ✅ COMPLIANT |
| REQ-02 Register | Invalid method | `...::test_invalid_method_returns_400` | ✅ COMPLIANT |
| REQ-02 Register | Unknown or cross-tenant client | `...::test_client_not_found_returns_404`, `...::test_cross_business_returns_403`, `...::test_branch_scoped_user_other_branch_returns_403`, `...::test_deleted_client_returns_404` | ✅ COMPLIANT |
| REQ-03 Idempotent | Second scan same day | `...::test_repeat_same_day_returns_200_already_checked_in` | ✅ COMPLIANT |
| REQ-04 List | List by date and branch | `...::TestListAttendance::test_list_sorted_desc_and_summary`, `...::test_list_pagination` | ⚠️ PARTIAL (data/meta/summary asserted; business/branch isolation at the query-filter level not asserted) |
| REQ-05 History | Client history | `...::TestClientAttendance::test_client_history_and_stats`, `...::test_cross_business_client_returns_403` | ✅ COMPLIANT |
| REQ-06 Stats | Stats for a branch | `...::TestAttendanceStats::test_stats_grouping_and_series`, `...::test_stats_single_query_even_with_top_attendees` | ✅ COMPLIANT |
| REQ-07 Permissions | Trainer cannot register | `...::test_trainer_cannot_register_returns_403` (+ `test_requires_auth` 401) | ✅ COMPLIANT |
| REQ-07 Permissions | Trainer can read | `...::TestListAttendance::test_trainer_can_read` | ✅ COMPLIANT |
| REQ-08 Composite Index | Missing index | (none found) | ❌ UNTESTED (behavior also deviates — see WARNING-01) |
| REQ-09 Scanner Contract | QR scan | (none found) | ❌ UNTESTED |

**Compliance summary**: 9/12 scenarios ✅ COMPLIANT, 2 ⚠️ PARTIAL, 2 ❌ UNTESTED.

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Attendance data model | ✅ Implemented | `register_attendance` writes all 11 spec fields (attendance.py:211-223). |
| POST registers check-in | ✅ Implemented | Validates `clientId`, default `method='manual'`, enum `manual|qr|biometric` → 400; fetch client, 404 missing/deleted, 403 cross-business/branch; 201 new. |
| Denormalized clientName | ✅ Implemented | `clientName: client.get('name')`. |
| Idempotent same-day | ✅ Implemented | Deterministic id `{clientId}_{date}`; `get_document` hit → 200 + `alreadyCheckedIn:true`, no write. |
| method enum + 400 | ✅ Implemented | `VALID_METHODS`; invalid → 400 with message. |
| List filtered + paginated, no N+1 | ✅ Implemented | ONE `query_firestore` (businessId + date [+branch/client]); Python sort/paginate; `meta{total,page,limit,pages}`, `summary{total,byMethod}`. |
| Client history + stats | ✅ Implemented | ONE query; `stats{total,thisMonth,lastVisit}`; scoped to client business/branch. |
| Stats today/rolling-7/rolling-30, top attendees, 7-day series | ✅ Implemented | ONE bounded query (30-day range); Python grouping; `series7`/`series30`/`last7Days`/`topAttendees`. |
| Permissions | ✅ Implemented | POST `POST_ROLES` (4), GET `READ_ROLES` (+trainer); 401 unauthenticated, 403 unauthorized. |
| Composite index documented | ⚠️ Partial | Documented in design D5 and task 6.1; runtime error surfacing ineffective (WARNING-01). |
| Scanner contract | ✅ Implemented (untested) | `method` qr/biometric accepted by same POST; no new endpoint. |
| Quota-conscious reads | ✅ Implemented | POST ≤2 reads + 1 write; list/stats/history single scoped queries; no full scans; no N+1; no `orderBy` (Python sort). |
| tzdata dependency | ✅ Implemented | `tzdata==2026.5` added to `backend/requirements.txt`; `Config.TIMEZONE` default `America/Caracas` with fixed-offset fallback. |

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 Deterministic doc id `{clientId}_{date}`; 201/200 split | ✅ Yes | Verified by test asserting `set_document('attendance', f'c1_{today}')` and status codes. |
| D2 Server-authoritative date in business TZ | ✅ Yes | `_business_today()` uses `ZoneInfo(Config.TIMEZONE)` + fallback. |
| D3 No `orderBy`; Python sorts/paginates | ✅ Yes | No `order_by` passed; `.sort(key=checkInAt)`. |
| D4 Stats: ONE bounded query + Python grouping | ✅ Yes | Test asserts `query_firestore.assert_called_once()`; range is 30 days. |
| D5 Composite indexes (manual) + actionable error | ⚠️ Partial | Indexes documented; `_index_error_response` is effectively dead code because `FirebaseService.query_firestore` swallows exceptions and returns `[]` (firebase_service.py:196-200). |
| D6 Permissions & scope from client doc | ✅ Yes | businessId/branchId resolved from client; branch-scoped users enforced. |
| Frontend file plan (types, api, page, nav, route) | ✅ Yes | All planned files created/modified; `/attendance` route and "Asistencia" nav wired with `UserCheck`. |

## Issues Found

### 🔴 CRITICAL

**CRITICAL-01 — New test file breaks the shared suite via auth-state leak (12 new failures).**
`backend/tests/routes/test_attendance.py` is alphabetically the first route test (before `test_auth.py`/`test_clients.py`). Its `make_client` fixture calls `create_app()` while `services.firebase_service.FirebaseService` is patched, and also patches `middleware.auth_middleware.FirebaseService`. Because `middleware/auth_middleware.py` binds `FirebaseService` at import time and the module is cached, the middleware ends up permanently holding an attendance test mock (`role='cashier'`) after teardown. Subsequent baseline route tests then authenticate as the stale role (evidence: `WARNING middleware.auth_middleware: Acceso denegado: rol cashier no en ['super_admin','admin','branch_admin']` → `assert 403 == 200`).
Impact: `pytest backend/tests` goes 18 → 30 failures; the change's own acceptance criterion ("no new failures") fails. Reproduce: `pytest backend/tests/routes/test_attendance.py backend/tests/routes/test_payment_delete.py` (1 failed). Fix direction: do not import `app`/middleware while the service is patched, or standardize the 2-point/3-point binding, or patch `middleware.auth_middleware.FirebaseService` for all route tests.
(Note: the pre-existing suite already has 18 order-dependent baseline failures; this change newly triggers 12 more.)

**CRITICAL-02 — Scanner Contract (QR/biometric) scenario has no covering test (UNTESTED).**
`VALID_METHODS` accepts `qr`/`biometric` and the code path is clearly correct, but no test posts `method:"qr"` or `"biometric"`. Per the verify protocol a spec scenario is compliant only with a passing covering test. Add a test asserting POST `{clientId, method:"qr"}` → 201 and stored `method:"qr"`.

### 🟡 WARNING

**WARNING-01 — Composite-index missing-index behavior deviates from spec and is untested.**
Spec REQ-08 scenario: on missing index the API SHOULD respond 500 referencing the index. In practice `FirebaseService.query_firestore` catches all exceptions and returns `[]` (firebase_service.py:196-200), so the route returns **200 with empty data**. `_index_error_response()` (attendance.py:62-85) never fires for query paths. Task 2.5 acknowledges this as "best-effort". Manual task 6.1 (create indexes) remains pending. Either make the service propagate `FAILED_PRECONDITION`, or formally downgrade/annotate the spec (it is a SHOULD).

**WARNING-02 — Document-shape scenario only partially asserted.**
`test_create_new_checkin_returns_201` checks `clientName`, `method`, `date`, id — but not `businessId`, `branchId`, `checkInAt`, `registeredBy`, `registeredByName`, `createdAt`. Extend assertions to cover the full model contract.

**WARNING-03 — List business/branch isolation not asserted at query level.**
The list test feeds a mocked query and only checks sorting/pagination/summary. It does not assert the filters passed to `query_firestore` (e.g. `businessId == B`, `branchId == A`), so the "only records for business B are returned" guarantee is unverified. Add filter-argument assertions.

**WARNING-04 — Non-numeric `page`/`limit` yield 500 instead of 400.**
`int(request.args.get('page', 1))` / `int(...limit...)` (attendance.py:270-271) raise `ValueError` for inputs like `?page=abc`, caught by the outer handler → 500. Wrap in a validation returning 400.

**WARNING-05 — `createdAt` type inconsistency between write path and reads.**
`register_attendance` sets `createdAt = now_iso` (ISO string), but `FirebaseService.set_document` overwrites it with `firestore.SERVER_TIMESTAMP` (firebase_service.py:332). The 201 response returns the in-memory ISO string, while a repeat check-in reads a Firestore timestamp (serialized differently by Flask). Consider a consistent timestamp representation.

### 🟢 SUGGESTION

- **SUGGESTION-01**: `_TZ_FALLBACK_OFFSETS` hardcodes offsets for 7 cities; since `tzdata` is now a dependency, `ZoneInfo` will normally succeed. Keep the fallback but consider logging when it is used.
- **SUGGESTION-02**: `/stats` returns both `series7` and the `last7Days` alias. Harmless, but document the alias or drop the duplicate.
- **SUGGESTION-03**: Frontend `getAttendance` return type omits `meta`/`summary` even though the backend sends them; typed access would be cleaner if the UI ever paginates.
- **SUGGESTION-04**: The AttendancePage is well-structured and attractive (search dropdown, stat cards, recharts 7-day bar chart, toast "Ya registrado hoy", method badges/icons) and is correctly wired into the `/attendance` route and "Asistencia" nav — no action needed; noted as verified-delightful.

## Verdict

**FAIL**
Production logic and UI are correct and all 20 change-scoped tests pass, but the change introduces 12 new full-suite failures (test-isolation leak) and leaves 2 of 12 spec scenarios with no covering test. To reach PASS: fix CRITICAL-01 (test isolation), add a QR/biometric test (CRITICAL-02), and resolve or formally accept WARNING-01 (index error surfacing) and manual task 6.1.
