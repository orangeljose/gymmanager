# Tasks: Client Deletion (Soft Delete, Payments Preserved)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500–600 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 backend → PR 2 frontend |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend: DELETE endpoint + PUT 404 + isDeleted filters + backend tests | PR 1 | routes + unit + dashboard tests included; base main/tracker branch |
| 2 | Frontend: deleteClient + Client.isDeleted + delete UI | PR 2 | base = PR 1 branch (feature-branch-chain) or main (stacked) |

## Phase 1: Backend — DELETE endpoint & audit (clients.py)

- [x] 1.1 Add `DELETE /api/clients/<client_id>` in `backend/routes/clients.py` with `@require_role(['super_admin','admin','branch_admin'])`: fetch → 404 if missing or `isDeleted` → inline business/branch check (mirror `update_client`) → 403 → `update_document('clients', id, {'isDeleted': True, 'deletedBy': g.current_user['uid'], 'deletedAt': now-iso})` → 200 `{'success': True, 'data': {'id': id}}`
- [x] 1.2 Modify `update_client` (PUT) in `backend/routes/clients.py`: return 404 when `client.get('isDeleted')` is True (user-confirmed)
- [x] 1.3 `get_clients`: filter `if c.get('isDeleted', False): continue` BEFORE search/sort/pagination (keeps `meta.total` correct; also covers quick-pay search)
- [x] 1.4 `get_client` + `get_client_payments`: 404 when client `isDeleted` (same check as 1.1)

## Phase 2: Backend — reports filtering (reports.py)

- [x] 2.1 `get_solvency_report`: skip `c.get('isDeleted', False)` clients after query, before enrichment
- [x] 2.2 `get_dashboard`: filter `all_clients` by `isDeleted` before active/overdue/expiring/retentionRate; leave `topPayingClients` payment-derived (deleted kept)

## Phase 3: Backend tests

- [x] 3.1 Create `backend/tests/unit/test_client_delete.py` (test_dashboard.py pattern): list excludes deleted; detail 404 deleted; DELETE 404 missing/already-deleted, 403 cross-branch, success writes isDeleted+deletedBy+deletedAt; `update_document` never on payments; PUT 404 for deleted; solvency excludes deleted
- [x] 3.2 Create `backend/tests/routes/test_client_delete.py` (test_payment_delete.py pattern): 200 super_admin/admin/branch_admin own-branch; 403 cashier/trainer/cross-branch; 404; 401
- [x] 3.3 Extend `backend/tests/unit/test_dashboard.py`: deleted excluded from active/overdue/expiring; legacy client (no field) counted; deleted client's payments kept in topPayingClients

## Phase 4: Frontend

- [x] 4.1 Add `isDeleted?: boolean` to `Client` in `frontend/src/types/index.ts`
- [x] 4.2 Add `deleteClient(id): Promise<ApiResponse<{id: string}>>` to `frontend/src/services/api.ts` (deletePayment pattern)
- [x] 4.3 `frontend/src/pages/ClientDetailPage.tsx`: delete button gated by `['super_admin','admin','branch_admin'].includes(user.role)`, inline confirm modal (deleteTarget pattern), on success toast + `navigate('/clients')`
- [x] 4.4 `frontend/src/pages/ClientsPage.tsx`: role-gated row delete action + modal, on success `fetchClients()` refetch

## Phase 5: Cleanup / Verification

- [ ] 5.1 Document idempotent backfill `isDeleted: false` for legacy clients (manual Firestore command) in PR description
- [ ] 5.2 Run `pytest` (backend) + frontend build/tsc; confirm all green