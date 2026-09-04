# Tasks: Invite Employees via Invitation Links

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~420–500 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 backend+tests → PR 2 frontend |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend branch scoping + accept name + tests | PR 1 | base main; self-contained API contract |
| 2 | Frontend rewire (api.ts, UsersPage, InvitePage) | PR 2 | base main; depends on PR 1 contract |

## Phase 1: Backend Model

- [x] 1.1 `backend/models/invitation.py`: extend `ROLE_CAN_INVITE['super_admin']` → `['admin','branch_admin','cashier','trainer']`
- [x] 1.2 Add `BRANCH_SCOPED_ROLES = {'branch_admin','cashier','trainer'}`
- [x] 1.3 Add `branch_id_from_request: str = None` param to `create_invitation_data`
- [x] 1.4 Branch roles: resolve branchId (request → inviter) and businessId (request → inviter); raise ValueError if either missing; admin businessId path unchanged (branchId stays None)

## Phase 2: Backend Routes

- [x] 2.1 `backend/routes/invitations.py` create: read `branchId` from body → pass as `branch_id_from_request`
- [x] 2.2 Accept: read optional `name` from body; store entered name → invitation name → '' fallback on user doc; return stored name

## Phase 3: Frontend API Service

- [ ] 3.1 `frontend/src/services/api.ts`: `createInvitation` input type `+branchId?: string` (forwarded in body)
- [ ] 3.2 `acceptInvitation(token, uid, name?: string)`: send `name` in body

## Phase 4: Frontend Pages

- [ ] 4.1 `UsersPage.tsx`: create path → `apiService.createInvitation` (email, name, role, branchId, businessId); drop `createUser` call
- [ ] 4.2 Branch selector REQUIRED for branch roles; gate invite button to super_admin/admin
- [ ] 4.3 Success → copyable-link card (AddAdminPage pattern); no user row added; edit path stays on `updateUser` (PUT /users)
- [ ] 4.4 `InvitePage.tsx`: pass `name` state to `acceptInvitation(token, uid, name)`

## Phase 5: Tests

- [x] 5.1 Create `backend/tests/models/test_invitation.py`: invite matrix (super_admin→all, admin→no admin), branch resolution precedence, missing branch/business → ValueError
- [x] 5.2 Create `backend/tests/routes/test_invitations.py` (conftest mock): create 201 with branchId, 400 missing branchId (super_admin), 400 duplicate email, 403 cashier inviter
- [x] 5.3 Same file: accept 201 stores entered name, fallback to invitation name, 404 reused token

## Phase 6: Verification

- [ ] 6.1 Run backend tests: `pytest backend/tests/models/test_invitation.py backend/tests/routes/test_invitations.py`
- [ ] 6.2 Frontend build/typecheck: `npm run build` in `frontend/`
- [ ] 6.3 Manual: invite→accept roundtrip, copyable link, AddAdminPage regression