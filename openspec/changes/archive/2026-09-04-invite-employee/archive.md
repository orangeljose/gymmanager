# Archive Report: invite-employee

**Change**: invite-employee
**Archived**: 2026-09-04
**Verify verdict**: PASS WITH WARNINGS (no CRITICAL issues)
**Commit**: 66062a7 (merged to main and pushed)

## Summary

Invite employees via invitation links (same flow as invite admin). `UsersPage` "Invitar Empleado" rewired from the broken `createUser` (POST /users — wrote a Firestore doc only, no Auth account, no link) to the `createInvitation` flow. `ROLE_CAN_INVITE` extended: super_admin can now invite all roles (admin, branch_admin, cashier, trainer); admin invites branch_admin/cashier/trainer. `branchId` added to invitation creation — required for branch-scoped roles (branch_admin/cashier/trainer), resolved request → inviter → 400. Accept flow now stores the invitee's ENTERED name (was discarded): fallback chain entered name → invitation name → `''`. `InvitePage` sends the collected name via `acceptInvitation`; UsersPage shows a copyable invitation link on success (email best-effort, link shared manually). Edit path on `PUT /users` preserved; `AddAdminPage` untouched. 34 new tests (22 model + 12 route) all passing.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| invitations | Created | Full spec copied (main spec did not exist): 6 requirements — Create Invitation, Invitation Role Permissions, Branch Scoping, Validate Invitation, Accept Invitation with Name, UsersPage Invite Rewire (17 scenarios) |

REMOVED requirements: none.

## Archive Contents

- proposal.md ✅
- specs/ ✅ (invitations)
- design.md ✅
- tasks.md ✅ (12/15 complete — Phase 6 verification; 6.1/6.2 evidenced by this verify run: 34 tests pass, build + tsc clean; 6.3 manual browser pass pending)
- verify.md ✅ (PASS WITH WARNINGS)

## Source of Truth Updated

- `openspec/specs/invitations/spec.md` — created (6 requirements, 17 scenarios)

## Verification

- [x] Main specs updated correctly (`openspec/specs/invitations/spec.md` created)
- [x] Change folder moved to `openspec/changes/archive/2026-09-04-invite-employee/`
- [x] Archive contains all artifacts (proposal, specs, design, tasks, verify, archive report)
- [x] Active changes directory no longer contains `invite-employee`

## Traceability

| Artifact | Location |
|----------|----------|
| Proposal | `openspec/changes/archive/2026-09-04-invite-employee/proposal.md` |
| Specs (delta) | `openspec/changes/archive/2026-09-04-invite-employee/specs/` |
| Design | `openspec/changes/archive/2026-09-04-invite-employee/design.md` |
| Tasks | `openspec/changes/archive/2026-09-04-invite-employee/tasks.md` |
| Verify | `openspec/changes/archive/2026-09-04-invite-employee/verify.md` |
| Archive report | `openspec/changes/archive/2026-09-04-invite-employee/archive.md` |
| Main spec | `openspec/specs/invitations/spec.md` |

## Notes / Warnings Carried Forward

- 6/17 spec scenarios have no automated covering test: invalid email (pre-existing route regex, unchanged), validate endpoint ×3 (pre-existing, untouched by delta), UsersPage UI ×2 (manual-only by design). None are delta regressions.
- Task 6.3 manual browser pass (invite→accept roundtrip, copyable link, AddAdminPage regression) remains outstanding before release.
- Suggested follow-ups (non-blocking): route-level tests for invalid email + validate endpoint (valid/expired/used token); remove dead `branch_admin` default-branchId branch in `UsersPage.openModal` (`canInvite` already excludes branch_admin); move `from datetime import datetime` to top imports in `backend/routes/invitations.py` (currently line 399).
- Pre-existing baseline: 14 failures in test_users/test_plans/test_client, identical at base commit — not regressions.

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. Ready for the next change.