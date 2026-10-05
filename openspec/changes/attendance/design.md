# Design: Client Attendance Tracking

## Technical Approach

Add one Firestore collection `attendance` and one blueprint `attendance_bp` (`/api/attendance`, 4 endpoints), mirroring `clients.py`/`payments.py`: Firestore does equality/range filters, Python does sort/paginate/group (the `clients.py` pattern), so reads scale with matches. Check-ins are idempotent per client/day via a **deterministic document id** `{clientId}_{date}` — one doc max by construction, 1 read to detect a repeat, no duplicate possible. Frontend adds `AttendancePage` (search + check-in + today list + stat cards + recharts 7-day chart), nav entry, route, API methods, types.

## Architecture Decisions

### D1 — Idempotency: deterministic doc id vs query-check

| Option | Tradeoffs | Decision |
|---|---|---|
| A. id `{clientId}_{date}`; `get_document` → `set_document` | 1 read + 1 write; duplicate impossible by construction; race = last-write-wins on one doc | **CHOICE** |
| B. query `clientId== & date==` then `create_document` | ~1+ reads + write; duplicate still possible on race | Rejected |

`date` is stored for range queries/indexes. POST returns **201** first (`alreadyCheckedIn:false`), **200** on repeat (`alreadyCheckedIn:true`) — a scanner treats any 2xx as success.

### D2 — Date authority & timezone

Server computes `date` in the business timezone (authoritative invariant); client-supplied dates rejected. Add `Config.TIMEZONE = os.environ.get('BUSINESS_TIMEZONE','America/Caracas')`; `date = datetime.now(ZoneInfo(tz)).strftime('%Y-%m-%d')`; `checkInAt` = UTC ISO for display.

### D3 — Query strategy: no orderBy, Python sorts

Firestore merges single-field indexes for multiple equality filters (verified in the `firebase-firestore` reference), so `businessId==/date==/branchId==` list queries need **no composite**; fetch then sort/paginate in Python. Range stats (`date>=`) DO need a composite. Avoiding `order_by` saves DESC index variants.

### D4 — Stats: one bounded query + Python grouping

`GET /stats` runs ONE query `businessId== [branchId==] date>=today-29, date<=today`, grouped in Python into today (0d), week (rolling 7d), month (rolling 30d), `series7`, `series30`, `topAttendees` (Counter by clientId). Uses `query_firestore`, **not** `count_firestore` (its 1000 ceiling is receipt-specific). Read cost = docs in 30 days.

### D5 — Composite indexes (manual, pre-deploy)

| # | Collection | Fields | Serves |
|---|---|---|---|
| 1 | attendance | `businessId ASC, date ASC` | stats biz-scoped range |
| 2 | attendance | `businessId ASC, branchId ASC, date ASC` | stats branch-scoped range |

List/client-history are equality-only → automatic indexes. No orderBy anywhere. `FAILED_PRECONDITION` errors link console creation.

### D6 — Permissions & scoping

POST `require_role(['super_admin','admin','branch_admin','cashier'])`; GET adds `trainer`. Resolve `businessId` from the **client doc** (source of truth); non-super_admin must match `user.businessId`; branch-assigned users must match `client.branchId` (`clients.py` inline pattern). List/stats: super_admin optional `businessId` param, else `user.businessId`; branch_id filter for assigned users.

## Data Flow

```
AttendancePage search ──→ GET /api/clients?search= (reuse) ──→ select client
   │ click "Registrar Asistencia"
   ▼
POST /api/attendance {clientId, method}
   ├─ get clients/{clientId}              (1 read: name, businessId, branchId, scope)
   ├─ get attendance/{clientId}_{date}    (1 read: idempotency)
   │     exists → 200 {..., alreadyCheckedIn:true}
   └─ set attendance/{clientId}_{date}    (1 write)
         → 201 {..., alreadyCheckedIn:false}
Stats/List ──→ query_firestore(attendance, biz[/branch] [+date range])
   ──→ Python sort/page/group ──→ JSON
```

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/routes/attendance.py` | Create | Blueprint, 4 endpoints, tz helpers |
| `backend/routes/__init__.py` | Modify | export `attendance_bp` |
| `backend/app.py` | Modify | import + `register_blueprint(attendance_bp)` |
| `backend/config.py` | Modify | add `TIMEZONE` |
| `backend/tests/routes/test_attendance.py` | Create | route tests (mocked FirebaseService) |
| `frontend/src/pages/AttendancePage.tsx` | Create | UI |
| `frontend/src/App.tsx` | Modify | `/attendance` route (5 roles) |
| `frontend/src/components/Layout.tsx` | Modify | nav item after Clientes + `UserCheck` iconMap |
| `frontend/src/services/api.ts` | Modify | 4 methods |
| `frontend/src/types/index.ts` | Modify | `AttendanceMethod/Record/Stats/Filters` |
| Firestore console | Manual | indexes 1–2 pre-deploy |

## Interfaces / Contracts

```ts
type AttendanceMethod = 'manual' | 'qr' | 'biometric';
interface AttendanceRecord { id; businessId; branchId; clientId; clientName;
  method; date; checkInAt; registeredBy; createdAt; alreadyCheckedIn?: boolean }
interface AttendanceStats { today; week; month;
  series7: {date;count}[]; series30: {date;count}[];
  topAttendees: {clientId; clientName; count}[] }
```
```
POST /api/attendance {clientId, method?, branchId?} → 201|200|400|404|403
GET  /api/attendance?date&clientId&branchId&businessId&page&limit
     → {data[], meta{total,page,limit,pages}, summary{total, byMethod}}
GET  /api/attendance/client/<clientId> → {data[], stats{total, thisMonth, lastVisit}}
GET  /api/attendance/stats?date&branchId&businessId → AttendanceStats
```

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit (backend) | POST 201; repeat 200+alreadyCheckedIn; invalid method 400; client 404/deleted; cross-business 403; branch scope | Mock `FirebaseService` (`test_plans.py` pattern) |
| Unit (backend) | deterministic id `clientId_date`; date uses business tz | Patch datetime / assert `set_document` args |
| Unit (backend) | stats grouping: today/week/month boundaries, series length, topAttendees | Mock `query_firestore` rows, assert payload |
| Build (frontend) | tsc `--noEmit` + vite build | `npm run build` |
| Manual | search→check-in ≤3 interactions; repeat click toast "Ya registrado hoy"; chart/cards; branch scope | Browser + network tab |
| Manual | Indexes 1–2 exist; no `FAILED_PRECONDITION` | Firebase console |

## Migration / Rollout

No data migration. Create indexes 1–2 in console BEFORE backend deploy (build takes minutes). Rollback: remove blueprint registration/route/nav — collection stays dormant; additive-only.

## Open Questions

- None blocking. "Semana/Mes" defined as rolling 7/30 days (aligns cards with the chart); confirm acceptable vs calendar week/month.
