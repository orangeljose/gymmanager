# Design: Client Deletion (Soft Delete, Payments Preserved)

## Technical Approach

Add `DELETE /api/clients/:clientId` soft-deleting via `update_document('clients', id, {'isDeleted': True})`, guarded by the delete-payment permission matrix + inline access checks from `update_client`. Payments untouched (Option A). Filter `isDeleted` in-Python across client queries (list, detail, payments history, solvency, dashboard metrics). Frontend: role-gated delete + confirm modal in `ClientDetailPage` (navigate away) and `ClientsPage` row action. No membership recalculation.

## Architecture Decisions

### Decision 1: Delete logic inline in route, not a new service

| Option | Tradeoff | Decision |
|---|---|---|
| New `ClientService.delete_client()` status envelope | Consistent with payment_service, but no client service exists | ❌ |
| Inline in `clients.py` after fetch (mirror `update_client`/`get_client`) | Matches clients.py convention; unit tests target route with mocked FirebaseService (`test_dashboard.py` precedent) | ✅ |

**Choice**: Inline (clients.py has no service layer; every client op is inline).

### Decision 2: Inline branch check after fetch (not `validate_branch_access`)

| Option | Tradeoff | Decision |
|---|---|---|
| `@validate_branch_access` decorator | needs static id; client branchId known only post-fetch | ❌ |
| Inline, reusing `update_client` block | matches precedent; super_admin skips; admin without branchId may delete cross-branch | ✅ |

**Order**: fetch → 404 (missing OR `isDeleted`) → 403 (business/branch mismatch) → `update_document({'isDeleted': True})` → 200 `{id}`.

### Decision 3: In-Python isDeleted filtering everywhere (never Firestore `== False`)

| Option | Tradeoff | Decision |
|---|---|---|
| Firestore `where('isDeleted','==',False)` | omits legacy docs missing the field; spec requires them active | ❌ |
| `if c.get('isDeleted', False): skip` | missing field = active; idempotent | ✅ |

**Placement**: `get_clients` filter BEFORE search/sort/pagination (correct `meta.total`); `get_client` + `get_client_payments` → 404; solvency after query; dashboard filters `all_clients` before client metrics. `topPayingClients` + income stay payment-derived — deleted kept.

### Decision 4: No membership recalculation; minimal 200 envelope

MUST NOT touch payments or membership fields. Route maps `not_found → 404` / `forbidden → 403` / `success → 200` (delete-payment style).

### Decision 5: Frontend mirrors payment-delete modal; navigate away

`deleteClient(id)` in api.ts; `isDeleted?: boolean` on `Client`. `ClientDetailPage`: `Trash2` gated by `['super_admin','admin','branch_admin'].includes(user.role)`, inline `fixed inset-0` confirm modal (deleteTarget pattern), on success `toast.success` + `navigate('/clients')`. `ClientsPage`: same gated row action + modal, on success `fetchClients()`. **PaymentsNewPage/DashboardPage unchanged** — backend filtering covers both.

## Data Flow

```
ClientDetailPage ── DELETE /api/clients/:id ──▶ require_auth / require_role
      ▲                                                │ 403 cashier/trainer
      │                                                ▼
 navigate('/clients') ◀─ 200 {id} ── clients.py: fetch → 404? → access? → isDeleted:True
                                                              (payments untouched)
 GET /clients · solvency · dashboard · quick-pay ──▶ filter c.get('isDeleted', False)
```

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/routes/clients.py` | Modify | DELETE endpoint; isDeleted filters in list/detail/payments-history |
| `backend/routes/reports.py` | Modify | solvency + dashboard exclude deleted (keep topPayingClients) |
| `backend/tests/routes/test_client_delete.py` | Create | HTTP 200/403/404/401 matrix (test_payment_delete.py pattern) |
| `backend/tests/unit/test_client_delete.py` | Create | list/detail/delete/solvency filtering |
| `backend/tests/unit/test_dashboard.py` | Modify | deleted-exclusion cases (active/overdue/expiring/retention) |
| `frontend/src/services/api.ts` | Modify | `deleteClient(id)` |
| `frontend/src/types/index.ts` | Modify | `isDeleted?: boolean` on `Client` |
| `frontend/src/pages/ClientDetailPage.tsx` | Modify | delete button + modal + navigate away |
| `frontend/src/pages/ClientsPage.tsx` | Modify | delete row action + modal + refetch |

## Interfaces / Contracts

```python
DELETE /api/clients/:clientId
200 {"success": true, "data": {"id": "client-001"}}
404 {"success": false, "error": {"code": 404, "message": "Cliente no encontrado"}}  # missing OR isDeleted
403 {"success": false, "error": {"code": 403, "message": "No tienes acceso a este cliente"}}
```
```typescript
async deleteClient(id: string): Promise<ApiResponse<{ id: string }>>;
interface Client { ...; isDeleted?: boolean; }
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | list excludes deleted; detail 404; delete 404/403/success; payments untouched; solvency excludes | mock FirebaseService; assert `update_document(...{'isDeleted': True})` once, never on payments |
| Unit | dashboard counts/retention exclude deleted; legacy client counted | extend `test_dashboard.py` |
| Routes | role matrix 200/403 + 404 + 401 | Flask client + status-envelope mocks (test_payment_delete.py pattern) |
| Manual | UI per role; cancel sends no request; navigate away | browser |

## Migration / Rollout

No data migration. Idempotent backfill `isDeleted: false` on legacy clients — manual, documented (delete-payment precedent). Rollback: set `isDeleted: false`. **Delivery forecast**: ~500 lines → 2 chained PRs (backend, then frontend).

## Reuse vs New

| REUSE (delete-payment patterns) | NEW |
|---|---|
| `require_auth` + `require_role` matrix | client DELETE endpoint (no recalc — payments stay) |
| soft delete via `update_document`; in-Python filtering | isDeleted filtering on client queries + `Client.isDeleted` |
| inline confirm modal + Toast + api method | navigate-away on success; client backfill |
| test factories (conftest) + status-envelope tests | — |

## Open Questions

- [ ] `PUT /clients/:id` also 404 for deleted? (Recommended yes; not in spec.)
- [ ] Record `deletedBy`/`deletedAt` audit fields? (Same open question as delete-payment.)