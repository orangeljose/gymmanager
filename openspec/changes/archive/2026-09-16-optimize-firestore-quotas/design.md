# Design: Optimize Firestore Quotas

## Technical Approach

Push filters into Firestore so reads scale with matches, not collection size; keep the defensive Python `isDeleted`/deleted-client filtering (Firestore `where` omits docs missing a field — legacy docs without `isDeleted` would silently vanish). Receipt numbers move to a constant-cost `count()` aggregation with the spec'd timestamp fallback. Frontend gets a single fetch owner per page. Two composite indexes created manually pre-deploy.

## Architecture Decisions

### D1 — Receipt number: `count()` aggregation + timestamp fallback

| Option | Tradeoffs | Decision |
|---|---|---|
| A. `count()` over `businessId ==` | 1 read ≤1000 payments, zero migration, keeps len+1 (soft-deleted counted — no isDeleted filter); ceiling 1000 → timestamp fallback (spec mandates) | **CHOICE** |
| B. Business-doc counter | O(1) forever, transaction-safe; but schema change + backfill, 1 write/payment, serializes writes per business | Rejected (migration + lazy-seed race) |
| C. Full scan | O(P) reads per payment — the quota bug | Rejected |

count() with a filter bills 1 read per 1000 index entries and honors filters. Concurrent-write race = pre-existing len+1 behavior, unchanged. A failed/ceiling count MUST fall back to the timestamp number — never fabricate `-001` (dupe risk). Upgrade path to B when a business nears 1000 payments.

### D2 — Income reports range on `createdAt`, not `paymentDate`

| Field | Tradeoffs | Decision |
|---|---|---|
| createdAt | Always set (SERVER_TIMESTAMP); legacy-safe; matches spec indexes | **Range field** |
| paymentDate | Optional — Firestore range silently omits docs missing the field → drops ALL legacy payments | Rejected for query |

Documented behavior delta: backdated payments (paymentDate set, createdAt = registration) now appear in the window covering `createdAt`, not `paymentDate`, when registration falls outside the requested window. Keep the existing Python `paymentDate or createdAt` check as a final in-memory filter — semantics unchanged for everything the query returns.

Queries: `businessId ==` (super_admin: from request param; else user), `branchId ==` when effective, `createdAt >= start`, `createdAt <= end`. NO order_by (Python sorts) → ASC indexes suffice. Keep deleted-client exclusion (deleted_client_ids set) and isDeleted Python filter.

### D3 — Dashboard: recentClients + 30-day bound

- `recentClients`: computed from the already-fetched clients list (business+branch scoped, isDeleted excluded): Python-sort by `createdAt` DESC, top 5 → `{id, name, email, membershipEnd, status}`. Zero extra reads, no new index (client counts small; full list already required for metrics).
- Payments query: add `createdAt >= now-30d` Firestore bound (businessId/branchId filters already present); keep Python window filter + exclusions. Requires indexes 1/2.

### D4 — ClientsPage: single fetch owner

| Owner | Change |
|---|---|
| `useClients` hook | Remove mount effect — hook is shared by ClientFormPage/ClientDetailPage which never read `clients` (each currently wastes 1 GET on mount) |
| ClientsPage effect | `useEffect(() => { if (effectiveBusinessId) fetchClients(); }, [effectiveBusinessId])` — owns initial + businessId-change fetch |
| Debounce effect | First-render `useRef` guard (skip mount); owns status/branch/search fetches, passes `page: 1` |
| Handlers | status/branch/Limpiar become state-only (debounce refetches); page-change and delete keep explicit `fetchClients` |

Result: exactly 1 GET per mount, per filter change; search stays debounced.

### D5 — Firestore composite indexes (manual, pre-deploy)

| # | Collection | Fields | Serves | Status |
|---|---|---|---|---|
| 1 | payments | `businessId ASC, createdAt ASC` | income (biz-scoped), dashboard window | NEW |
| 2 | payments | `businessId ASC, branchId ASC, createdAt ASC` | income/dashboard (branch-scoped) | NEW |
| 3 | — | none — no order_by used on these queries | (adding order_by later ⇒ DESC variants needed) | none |

Already exist (verify in console): single-field indexes (auto); documented `payments (isDeleted ASC, createdAt DESC)` (delete-payment archive); inferred `payments`/`clients (businessId, branchId)` (dashboard works today). count() uses the single-field businessId index. Do NOT push isDeleted into queries (legacy docs lack the field).

## Data Flow

    register_payment ──→ count_firestore(payments, businessId==) ──→ seq+1 ──→ P-YYYYMMDD-XXX
                              └─ error/ceiling ──→ P-YYYYMMDD-HHMMSSfff (never blocks)
    income report ──→ query_firestore(payments, biz==, [branch==,] createdAt>= <=)
                          ──→ Python: isDeleted + deleted-client + date check ──→ group

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/services/firebase_service.py` | Modify | Add `count_firestore(collection, filters) -> int`; raises on failure (never fake 0) |
| `backend/services/payment_service.py` | Modify | `generate_receipt_number` → count()+1; timestamp fallback on error |
| `backend/routes/reports.py` | Modify | Income daily/by-method: filtered queries; dashboard: createdAt>= bound + recentClients |
| `backend/tests/unit/test_dashboard.py` | Modify | recentClients contract + filtered-query assertions |
| `backend/tests/unit/test_receipt_number.py` | Create | count seq, fallback, count query has no isDeleted filter |
| `backend/tests/unit/test_reports_income.py` | Create | filter construction, super_admin resolution, Python exclusions |
| `frontend/src/types/index.ts` | Modify | `RecentClient` + `DashboardData.recentClients` |
| `frontend/src/pages/DashboardPage.tsx` | Modify | Drop `getClients`; render recentClients from payload |
| `frontend/src/hooks/useClients.ts` | Modify | Remove mount effect |
| `frontend/src/pages/ClientsPage.tsx` | Modify | Single-fetch ownership |
| Firestore console | Manual | Indexes 1 and 2 |

## Interfaces / Contracts

```ts
interface RecentClient { id: string; name: string; email: string; membershipEnd: string; status: string }
interface DashboardData { /* existing */; recentClients: RecentClient[] }
```

```python
def count_firestore(self, collection: str, filters: List[Dict[str, Any]]) -> int:
    """Count aggregation; RAISES on failure/ceiling — caller falls back, never fakes a count."""
```

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit | Receipt seq = count+1; timestamp fallback on error; count has NO isDeleted filter | Mock count_firestore; assert formats |
| Unit | Income query args (biz/branch/createdAt bounds); super_admin businessId from param; isDeleted + deleted-client Python exclusion | Mock query_firestore; assert_called_with |
| Unit | recentClients: ≤5, desc order, deleted excluded, empty state; payments query called with createdAt>= | Extend test_dashboard.py (existing reset-singleton pattern) |
| Manual | ClientsPage: 1 GET /clients per mount/filter in network tab; dashboard no /clients call; quota meter over a week | Browser + Firebase console |

## Migration / Rollout

No data migration. Create indexes 1+2 in Firebase console BEFORE deploy (build takes minutes; index-error messages link direct creation). Rollback: `git revert` — old Python-side filtering works without new indexes; receipt scan logic restores.

## Open Questions

- None blocking. Pre-deploy: confirm in console whether `payments/clients (businessId, branchId)` composites exist (dashboard functioning today implies yes).