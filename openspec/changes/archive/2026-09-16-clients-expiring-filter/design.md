# Design: Clients Expiring Filter & Solvency Report Removal

## Technical Approach

Two workstreams:

1. **expiringSoon filter**: extend `GET /api/clients` with `expiringSoon=true`, pushing a `membershipEnd` window `[now, now+7d]` into Firestore. Python keeps `isDeleted` exclusion, sort, pagination. Requires 2 composite indexes (manual, same workflow as payments indexes).
2. **Solvency removal**: delete page, card link, api method, types, endpoint, tests. Verified: `App.tsx` has no solvency route/import — no change (proposal over-scoped).

## Architecture Decisions

### D1 — `expiringSoon=true`: precedence over `status`

| Option | Tradeoffs | Decision |
|---|---|---|
| A. expiringSoon wins; status ignored | Forgiving, no new error path; single-select UI never sends both | **CHOICE** |
| B. 400 on both | Explicit misuse; error path the app can never trigger | Rejected |

Parse `request.args.get('expiringSoon','').lower() in ('true','1')` (else off, no 400). Active ⇒ skip `status` block, append `membershipEnd >= now`, `<= now + timedelta(days=7)` (`now = datetime.now(timezone.utc)`; add `timedelta` import). In `get_clients` ~L85-96; docstring L25.

### D2 — Composite indexes (manual, pre-deploy)

Equality + range on different fields ⇒ composite; equality fields precede range; Firestore can't skip middle fields ⇒ BOTH required:

| # | Collection | Fields | Serves |
|---|---|---|---|
| 1 | clients | `businessId ASC, membershipEnd ASC` | business-scoped (admin w/o branch) |
| 2 | clients | `businessId ASC, branchId ASC, membershipEnd ASC` | branch-scoped (branch_admin) |

No `order_by` (Python sorts) ⇒ ASC-only. `isDeleted` excluded (legacy docs lack field). Range omits docs missing `membershipEnd` — fine: no membership = not expiring. `FAILED_PRECONDITION` error links console creation.

### D3 — Frontend wiring

- Dropdown: replace `suspended` option with `<option value="expiring">Próximos 7 días</option>`; `statusFilter` widens to `ClientStatus | 'expiring' | ''`. Helper `buildClientFilters(page?)` maps `'expiring'` → `{expiringSoon: true}` — reused by debounced effect (L49-64, single fetch owner), page-change, delete-refresh.
- `ClientFilters` gains `expiringSoon?: boolean`; `api.ts` appends `expiringSoon=true` when set. Hook spreads filters already — no change.
- `ClientStatus` → `'active' | 'expired'`. **Keep** `'Suspendido'` fallback labels (ClientsPage L286, ClientDetailPage L191, PaymentsNewPage L145/L212) + yellow badge case: legacy docs may carry the value; type change blocks NEW code from writing it. No changes in those pages.

### D4 — Solvency removal file map

| File | Action | Description |
|---|---|---|
| `frontend/src/pages/SolvencyReportPage.tsx` | Delete | Dead page |
| `frontend/src/App.tsx` | — | NO CHANGE (route/import absent — verified) |
| `frontend/src/pages/ReportsPage.tsx` | Modify | Remove "Reporte de Membresías" card + unused `AlertTriangle` import |
| `frontend/src/services/api.ts` | Modify | Remove `getSolvencyReport` (L298-306) + its type imports |
| `frontend/src/types/index.ts` | Modify | Remove `SolvencyReport` (L180), `ReportFilters` (L312); only used by api.ts + page |
| `backend/routes/reports.py` | Modify | Remove `/solvency` (L35-238) + unused `_get_membership_end` (L15-31) |
| `backend/tests/unit/test_solvency_report.py` | Delete | Endpoint tests die with endpoint |
| `backend/tests/unit/test_client_delete.py` | Modify | Remove `TestSolvencyExcludesDeleted` (L246-265) |
| `backend/tests/models/test_client.py` | Modify | `test_valid_status_update`: `'suspended'` → `'expired'`; add rejection test |
| `backend/models/client.py` | Modify | `valid_statuses` → `['active','expired']` (L85) |
| `backend/routes/clients.py` | Modify | Same (L87); docstrings L25/L395 |
| `backend/README.md` | Modify | Remove solvency line (L110); document `expiringSoon` (L98) |
| Firebase console | Manual | Indexes 1 + 2 (D2) |

## Data Flow

    ClientsPage ("Próximos 7 días") ──→ GET /api/clients?expiringSoon=true[&branchId=…]
        ├─ businessId == (scope)                 (Firestore, idx 1/2)
        ├─ branchId == (if scoped)               (Firestore, idx 2)
        ├─ membershipEnd >= now                  (Firestore range, idx 1/2)
        ├─ membershipEnd <= now+7d               (Firestore range, idx 1/2)
        └─ Python: isDeleted exclusion + sort + paginate ──→ 200 {data, meta}

## Interfaces / Contracts

```ts
export type ClientStatus = 'active' | 'expired';              // 'suspended' removed
export interface ClientFilters {
  businessId?: string; branchId?: string; status?: ClientStatus;
  expiringSoon?: boolean;   // NEW — overrides status when true
  search?: string; page?: number; limit?: number;
}
```

`GET /api/clients?expiringSoon=true` → `membershipEnd >= now` AND `<= now+7d`; `status` ignored; response shape unchanged.

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit (backend) | expiringSoon builds both bounds; status ignored when both sent; isDeleted exclusion intact | Mocked `query_firestore`; assert filters in kwargs (test_reports_income pattern) |
| Unit (backend) | `'suspended'` rejected in model + route | Update test_client.py + new assertions |
| Unit (backend) | Solvency gone | Delete test_solvency_report.py; drop TestSolvencyExcludesDeleted |
| Build (frontend) | tsc `--noEmit` + vite build | `npm run build` |
| Manual | Dropdown 4 options; `?expiringSoon=true` sent; one GET per change ("Single Fetch" scenarios); pagination; branch scope | Browser + network tab |
| Manual | Indexes pre-deploy; no `FAILED_PRECONDITION` | Firebase console |

## Migration / Rollout

No data migration. Create indexes 1+2 BEFORE deploying backend (build takes minutes; index-error link guides). Rollback: `git revert` — status-only filtering works without new indexes; orphan indexes harmless.

## Open Questions

- [ ] None blocking. Cosmetic: do legacy clients with `status='suspended'` exist in prod (only affects fallback label rendering).