# Proposal: Invite Employees via Invitation Links

## Intent

Let the owner invite employees (cashier, trainer, branch_admin) like admins: share a link the employee opens to create their own account (name + password). No corporate email needed.

Backend invitation endpoints already support all employee roles, but the frontend never uses them: `UsersPage` "Invitar Empleado" calls `POST /api/users`, which only writes a Firestore doc — no Auth account, no link.

## Scope

### In Scope
- Rewire `UsersPage` "Invitar Empleado" modal → `createInvitation` (role + branchId + name).
- Add `branchId` to `POST /api/invitations` + `create_invitation_data`; required for branch-scoped roles (cashier, trainer, branch_admin).
- Fix name: `InvitePage` sends entered name via `acceptInvitation`; backend stores it.
- Keep `UsersPage` edit path on `PUT /users` (unchanged).
- Verify `AddAdminPage` already uses invitation flow (unchanged).

### Out of Scope
- Changing admin invitation flow (`AddAdminPage`).
- Email delivery guarantees (Resend stays best-effort).
- User deactivation/edit behavior beyond current implementation.

## Capabilities

> Contract for sdd-spec.

### New Capabilities
- `invitations`: invitation link lifecycle — create (with branchId + name for employees), validate, accept, token expiry, duplicate-email.

### Modified Capabilities
- None

## Approach

1. `api.ts`: add `branchId` to `createInvitation`, `name` to `acceptInvitation`.
2. `UsersPage.tsx`: create path → `createInvitation`, show link; keep edit path on `updateUser`.
3. Backend: read `branchId` → `create_invitation_data`; require for branch-scoped roles (400), default to inviter's branch.
4. `InvitePage.tsx`: send collected name via `acceptInvitation`.
5. Backend accept: optional `name`, store on user doc when provided.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/pages/UsersPage.tsx` | Modified | Create path → `createInvitation`; branchId + name |
| `frontend/src/services/api.ts` | Modified | `createInvitation` + `acceptInvitation` signatures |
| `frontend/src/pages/InvitePage.tsx` | Modified | Send entered name on accept |
| `backend/routes/invitations.py` | Modified | Accept `branchId` (create) + `name` (accept) |
| `backend/models/invitation.py` | Modified | `create_invitation_data` branchId |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Employee without branchId locked out | High | Backend 400 + branch picker |
| Duplicate/expired token errors | Med | Reuse existing error handling |
| Breaking admin invite flow | Low | AddAdminPage untouched; branchId defaulted |

## Rollback Plan

Revert `UsersPage` create path to `createUser` and remove `branchId` from backend. Invitations are additive docs, so existing users are unaffected. Revert both in the same PR.

## Dependencies

- None (invitation endpoints already exist).

## Success Criteria

- [ ] admin/super_admin invites cashier/trainer/branch_admin via link with branchId
- [ ] Employee creates account from link; name + role + branchId persisted
- [ ] Branch-scoped invite without branchId returns 400
- [ ] `UsersPage` edit path still works via `PUT /users`
- [ ] `AddAdminPage` flow unchanged
