# Design: Invite Employees via Invitation Links

## Technical Approach

Rewire `UsersPage`'s create flow from direct user creation (`POST /users`) to the existing invitation-link flow (`POST /api/invitations`), extending the backend to carry `branchId` for branch-scoped roles and to store the invitee's entered name at accept time. The model stays the single source of truth for role+branch resolution; the frontend only collects and forwards data. Maps to proposal approach steps 1–5 and satisfies all spec requirements (invitations, role permissions, branch scoping, accept-with-name, UsersPage rewire).

## Architecture Decisions

| # | Decision | Options | Tradeoff | Chosen |
|---|----------|---------|----------|--------|
| D1 | super_admin invite matrix | keep `['admin']` vs extend | owner locked out of employee invites vs wider blast radius | Extend to `['admin','branch_admin','cashier','trainer']` (user-confirmed) |
| D2 | branchId resolution | request-only vs request→inviter fallback vs derive from branch doc | fallback matches inviter intent and hides UI mistakes; doc derivation adds Firestore read into a pure model | Request → inviter fallback; raise 400 when neither exists |
| D3 | businessId for branch roles | require explicitly vs derive from branch doc | explicit keeps model pure; UI (super_admin business selector, admin context) already provides it | Request → inviter fallback → 400 (prevents branch-without-business lockout) |
| D4 | accept name handling | overwrite vs fallback chain | overwrite discards invite name | Entered name → invitation name → `''` (spec: Accept without name) |
| D5 | AddAdminPage | add branch picker vs keep as-is | admin is business-scoped, branch irrelevant | Keep as-is — verified it sends `role:'admin'` + `businessId`; `branchId` stays optional |
| D6 | UsersPage role select | include admin for super_admin vs branch roles only | duplicate AddAdminPage surface | Branch roles only; admin invites stay on AddAdminPage |

## Data Flow

    UsersPage modal ──createInvitation{email,name,role,branchId,businessId?}──▶ POST /api/invitations
        │                                                              │ read branchId
        ▼                                                              ▼
    inviteLink ◀── 201 {invitationLink} ◀── create_invitation_data (branch resolution, 400 if missing)
        │
        ▼
    InvitePage (/invite?token) ──▶ validate ──▶ firebaseAuth.createUser ──▶ acceptInvitation(token, uid, name)
                                                                              │
                                                                              ▼
                                                              POST /api/invitations/accept
                                                              user doc {name: enteredName, role, businessId, branchId}
                                                              invitation → accepted (single-use)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/models/invitation.py` | Modify | Extend `ROLE_CAN_INVITE['super_admin']`; add `BRANCH_SCOPED_ROLES`; add `branch_id_from_request` param + branch resolution in `create_invitation_data` |
| `backend/routes/invitations.py` | Modify | Create: read `branchId` from body → model. Accept: read optional `name`, store on user doc (fallback chain) |
| `frontend/src/services/api.ts` | Modify | `createInvitation` input type `+branchId?`; `acceptInvitation(token, uid, name?)` sends name in body |
| `frontend/src/pages/UsersPage.tsx` | Modify | Create path → `createInvitation`; branch selector REQUIRED; copyable-link success card (AddAdminPage pattern); gate invite button to super_admin/admin; modal title/labels updated; edit path untouched |
| `frontend/src/pages/InvitePage.tsx` | Modify | Pass `name` state to `acceptInvitation` |
| `backend/tests/models/test_invitation.py` | Create | Model unit tests |
| `backend/tests/routes/test_invitations.py` | Create | Route tests |

## Interfaces / Contracts

`create_invitation_data` gains `branch_id_from_request: str = None`. The only non-obvious logic is branch resolution:

```python
BRANCH_SCOPED_ROLES = {'branch_admin', 'cashier', 'trainer'}

if target_role in BRANCH_SCOPED_ROLES:
    branch_id = branch_id_from_request or inviter_data.get('branchId')
    business_id = business_id_from_request or inviter_data.get('businessId')
    if not branch_id or not business_id:
        raise ValueError('branchId y businessId son requeridos para roles de sucursal')
    invitation_data['branchId'] = branch_id
    invitation_data['businessId'] = business_id
# else: existing admin businessId logic unchanged (branchId stays None)
```

`POST /api/invitations` body: `+branchId?`. `POST /api/invitations/accept` body: `+name?`; response `name` = stored name. Note: production admins have no `branchId` (admin invitations set it None), so the fallback path for admins yields 400 — the UI's required branch picker prevents this in practice; the 400 is the API safety net.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit (models) | invite matrix (super_admin→all, admin→no admin), branch resolution precedence, missing branch/business → ValueError | New `tests/models/test_invitation.py` |
| Route | create: 201 with branchId, 400 missing branchId (super_admin), 400 duplicate email, 403 cashier inviter; accept: 201 stores entered name, fallback to invitation name, 404 reused token | New `tests/routes/test_invitations.py` using existing conftest mock pattern |
| Manual | copyable-link UI, invite→accept roundtrip, AddAdminPage regression | Browser pass |

## Migration / Rollout

No migration: invitations are additive docs; existing users untouched. Rollback = revert `UsersPage` create path to `createUser` + drop `branchId` from backend, same PR.

## Open Questions

None blocking.