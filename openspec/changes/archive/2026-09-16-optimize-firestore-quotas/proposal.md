# Proposal: Optimize Firestore Quotas

## Intent

Spark plan caps Firestore at 50K reads/day, yet ~1 week of LIGHT use burned the full quota (50K reads in one 3-hour window). Data volume is tiny (~50 payments, ~47 clients) — the burn comes from inefficient code: unfiltered full-collection scans with Python-side filtering, N+1 loops, and duplicate frontend fetches. This change eliminates the biggest read burners so normal operation stays far below quota.

## Scope

### In Scope
- **Backend: real Firestore filters** (biggest win, ~70-80% of volume)
  - `reports.py` income daily + by-method: push businessId + date-range into the Firestore query instead of reading all payments (~2,300 reads/report view)
  - `payment_service.py` `generate_receipt_number`: replace full-history scan (~300 reads/payment, grows forever) with Firestore `count()` aggregation or business-doc counter
  - Dashboard payments query: verify/fix businessId filter
  - Document required composite indexes (businessId + createdAt range)
- **Frontend: ClientsPage dedupe** — one data-fetch owner; remove hook + debounce double-fire (2x requests)
- **Frontend: dashboard lighten** — drop `getClients({limit:100})`; use recent clients from getDashboard payload (verify) or reduce to limit:5

### Out of Scope (deferred)
- Request-level URL cache in `api.ts`
- Auth `getIdToken(true)` removal; `require_auth` per-request user read
- Search min-length enforcement
- N+1 loops: solvency last-payment (reports.py L166), membership recalculate (membership_service.py L324), sync batches (payment_service.py L257)
- Receipts 1,000-doc scan (payments.py L396)
- ClientDetailPage/PaymentsNewPage duplicated plans + payment-accounts fetches

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `payment-flow`: Receipt Number Generation — mechanism changes from history scan to count/counter; MUST preserve unique sequential numbering; delta spec defines gap tolerance per approach
- `dashboard-analytics`: Dashboard data contract — recent-clients widget source changes from separate `GET /clients` to getDashboard payload (or reduced limit)

## Approach

Push filters into Firestore queries (equality + range), keeping existing defensive Python `isDeleted` handling (Firestore equality omits missing fields). Use `count()` aggregation for receipt numbering to preserve len+1 semantics cheaply. Frontend: single fetch owner per page. Extend existing backend tests (test_dashboard.py) with filtered-query coverage.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/routes/reports.py` | Modified | Income endpoints add businessId + date-range filters |
| `backend/services/payment_service.py` | Modified | Receipt number via count()/counter, not full scan |
| `backend` dashboard endpoint | Modified | Verify businessId filter; getDashboard payload may add recent clients |
| Firestore composite indexes | New | businessId+createdAt (+ variants) — created pre-deploy |
| `frontend/src/pages/ClientsPage.tsx` | Modified | Single fetch owner, remove double-fire |
| `frontend/src/pages/DashboardPage.tsx` | Modified | Remove getClients({limit:100}) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Missing composite index → query 400 until built | Med | Document + create indexes before deploy |
| Receipt number gaps/dupes after mechanism change | Med | count() preserves len+1; counter via transaction; tests |
| Report filter regression (isDeleted missing-field) | Med | Keep defensive Python filter; extend tests |
| Dashboard widget breaks if payload lacks recent clients | Low | Verify payload first; fallback limit:5 |

## Rollback Plan

Per-change `git revert` — Python-side filtering still works without new indexes; receipt scan logic restores on revert. Frontend reverts restore double-fetch (wasteful but functional).

## Dependencies

- Firestore composite indexes (created before deploy; build takes minutes)
- Firestore `count()` aggregation (available on Spark)

## Success Criteria

- [ ] Income report view reads ≤ ~30 docs (vs ~2,300)
- [ ] Payment write reads do NOT grow with payment history
- [ ] ClientsPage fires exactly 1 GET /clients per mount/filter change
- [ ] Dashboard load no longer fetches 100 clients
- [ ] No 429 quota errors across 1 week of light use
- [ ] All existing + new backend tests pass