# Verification Report — invite-employee

**Change**: invite-employee
**Version**: invitations capability spec (6 requirements, 17 scenarios)
**Mode**: Standard (no Strict TDD active)
**Branch verified**: `feature/invite-employee-frontend` (stacked: PR 1 backend `feature/invite-employee-backend` → PR 2 frontend)

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 15 |
| Tasks complete (marked [x]) | 12 |
| Tasks incomplete (Phase 6, [ ]) | 3 — 6.1/6.2 now evidenced by this verify run; 6.3 manual browser pass pending |

## Build & Tests Execution

**Build**: ✅ Passed — `npm run build` in `frontend/` (✓ built in 17.90s; only pre-existing chunk-size/dynamic-import warnings)

**Typecheck**: ✅ Passed — `npx tsc --noEmit` in `frontend/` (0 errors)

**Tests**: ✅ 34 passed / ❌ 0 failed
```text
pytest backend/tests/models/test_invitation.py backend/tests/routes/test_invitations.py -v
34 passed, 12 warnings in 1.17s
(22 model + 12 route; warnings are flask-limiter in-memory storage, pre-existing)
```

**Baseline check (unchanged)**: ✅ — `test_users` ×7, `test_plans` ×6, `test_client` ×1 = 14 failures, identical pre-existing baseline. None of those files were touched by this change (`git diff main...` covers only invitation model/routes, invitation tests, UsersPage/InvitePage/api.ts, openspec docs).

**Coverage**: ➖ Not available (no coverage tooling configured)

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| REQ-01 Create Invitation | Admin invites cashier | `routes/test_invitations.py > test_create_with_branch_id` | ✅ COMPLIANT |
| REQ-01 | Duplicate pending invitation | `test_create_duplicate_pending_invitation` | ✅ COMPLIANT |
| REQ-01 | Invalid email | (none — pre-existing route regex, unchanged) | ⚠️ UNTESTED |
| REQ-01 | Unauthorized inviter (403) | `test_create_cashier_forbidden` | ✅ COMPLIANT |
| REQ-02 Role Permissions | Admin cannot invite admin | `test_create_admin_cannot_invite_admin` + model `test_admin_cannot_invite_admin` | ✅ COMPLIANT |
| REQ-02 | super_admin invites trainer | model `test_super_admin_invites_role_succeeds[trainer]` (+ matrix `test_super_admin_can_invite_all_roles`) | ✅ COMPLIANT |
| REQ-03 Branch Scoping | Fallback to inviter's branch | `test_create_fallback_to_inviter_branch` (route) + `test_fallback_to_inviter_branch` (model) | ✅ COMPLIANT |
| REQ-03 | Missing branch for employee → 400 | `test_create_missing_branch_for_branch_role` + `test_missing_branch_raises_value_error` | ✅ COMPLIANT |
| REQ-03 | Admin invite keeps business scope | `test_create_admin_keeps_business_scope` + `test_super_admin_invites_admin_with_business` | ✅ COMPLIANT |
| REQ-04 Validate Invitation | Valid token | (none — endpoint pre-existing, untouched by delta) | ⚠️ UNTESTED |
| REQ-04 | Expired token | (none — pre-existing `validate_token` logic) | ⚠️ UNTESTED |
| REQ-04 | Used token | (none — pre-existing) | ⚠️ UNTESTED |
| REQ-05 Accept with Name | Accept stores entered name | `test_accept_stores_entered_name` | ✅ COMPLIANT |
| REQ-05 | Accept without name (fallback) | `test_accept_fallback_to_invitation_name` + `test_accept_without_name_or_invitation_name_falls_back_to_empty` | ✅ COMPLIANT |
| REQ-05 | Reusing accepted token → 404 | `test_accept_reused_token_returns_404` | ✅ COMPLIANT |
| REQ-06 UsersPage Rewire | Invite success shows link, no user row | Static: `createInvitation` call + copyable-link card (no FE test infra; manual task 6.3 pending) | ⚠️ UNTESTED (manual-only) |
| REQ-06 | Edit still uses PUT /users | Static: `updateUser` path untouched in diff | ⚠️ UNTESTED (manual-only) |

**Compliance summary**: 11/17 scenarios with passing covering tests; 6 without automated covering tests — 4 are pre-existing behaviors outside the delta (invalid email regex, validate ×3), 2 are frontend UI behaviors scheduled for manual browser pass (task 6.3, still open). The delta's own testing strategy (design.md) is delivered 100%: every planned model/route test exists and passes.

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| super_admin invite matrix extended | ✅ Implemented | `ROLE_CAN_INVITE['super_admin'] = ['admin','branch_admin','cashier','trainer']` (user-confirmed, D1) |
| branchId resolution request → inviter → 400 | ✅ Implemented | `branch_id_from_request or inviter_data['branchId']`, ValueError → 400 route (D2) |
| businessId resolution for branch roles | ✅ Implemented | request → inviter → 400 (D3); admin path unchanged (`elif`, branchId stays None) |
| Accept name fallback chain | ✅ Implemented | entered name → invitation name → `''`; returned in response (D4) |
| UsersPage create → createInvitation | ✅ Implemented | `createUser` dropped from create path; branchId required client-side + branch selector required |
| UsersPage role select branch-roles only | ✅ Implemented | options: branch_admin/cashier/trainer (D6); admin invites stay on AddAdminPage |
| UsersPage copyable-link success card | ✅ Implemented | AddAdminPage pattern, copy button, no user row added |
| UsersPage edit path unchanged | ✅ Implemented | `updateUser` (PUT /users) intact in diff |
| AddAdminPage preserved | ✅ Implemented | Not in diff; sends `role:'admin'` + `businessId` (D5) |
| InvitePage sends name | ✅ Implemented | `acceptInvitation(token, uid, name.trim())` |

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 super_admin invite matrix extended | ✅ Yes | exact list |
| D2 branchId request → inviter → 400 | ✅ Yes | model + route + tests |
| D3 businessId for branch roles → 400 | ✅ Yes | raises when branch or business missing |
| D4 accept name fallback chain | ✅ Yes | entered → invitation → `''` |
| D5 AddAdminPage kept as-is | ✅ Yes | zero diff; role admin + businessId |
| D6 UsersPage branch roles only | ✅ Yes | no admin option in select |

## Issues Found

**CRITICAL**: None

**WARNING**:
1. 6/17 spec scenarios have no passing automated covering test — none are delta regressions, but per verify protocol they are UNTESTED: invalid email (pre-existing regex), validate ×3 (pre-existing endpoint), UsersPage UI ×2 (manual-only by design).
2. tasks.md Phase 6 (6.1, 6.2, 6.3) still marked `[ ]` — 6.1 and 6.2 evidence is now provided by this verify run (34 tests pass, build passes); 6.3 manual invite→accept roundtrip + copyable-link + AddAdminPage browser pass remains outstanding before release.

**SUGGESTION**:
1. Add cheap route-level tests for invalid email (400) and validate endpoint (valid/expired/used token) to close the untested scenarios — `InvitationModel.validate_token` is already testable.
2. `UsersPage.openModal` retains a dead `branch_admin` default-branchId branch — `canInvite` already excludes branch_admin; removable.
3. `from datetime import datetime` sits at the bottom of `backend/routes/invitations.py` (line 399) — move to top imports.
4. Frontend build warns 1.12 MB chunk (pre-existing) — unrelated to this change.

## Verdict

**PASS WITH WARNINGS** — Core delta (backend branch scoping + accept-name + matrix extension + UsersPage rewire) is fully implemented, matches spec/design/tasks, and is covered by 34 passing tests + clean tsc + clean build; the 6 untested scenarios are pre-existing/UI behaviors pending the scheduled manual browser pass (task 6.3).