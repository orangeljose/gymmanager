# invitations Specification

## Purpose

Invitation link lifecycle for onboarding employees (branch_admin, cashier, trainer) and admins: create scoped invitations, validate tokens, accept with the invitee's own name, and rewire `UsersPage` to invite via links instead of direct user creation.

## Requirements

### Requirement: Create Invitation

`POST /api/invitations` SHALL accept `email`, `name`, `role`, and optional `businessId`/`branchId`. The system SHALL generate a unique token and an invitation link with 72h expiry, SHALL create a `pending` invitation document, and SHALL return 201 with the link. Email delivery SHALL be best-effort; the UI SHALL show a copyable link regardless.

#### Scenario: Admin invites cashier

- GIVEN an authenticated admin and a valid email
- WHEN they POST /api/invitations with role cashier and branchId
- THEN the system SHALL return 201 with token, expiresAt (72h), and invitationLink
- AND a pending invitation SHALL exist for that email

#### Scenario: Duplicate pending invitation

- GIVEN a pending invitation already exists for the email
- WHEN POST /api/invitations is sent again with the same email
- THEN the system SHALL return 400 with a duplicate-email error

#### Scenario: Invalid email

- GIVEN an email not matching the email pattern
- WHEN POST /api/invitations is sent
- THEN the system SHALL return 400

#### Scenario: Unauthorized inviter

- GIVEN a cashier or trainer authenticated request
- WHEN they POST /api/invitations
- THEN the system SHALL return 403

### Requirement: Invitation Role Permissions

super_admin MAY invite admin (existing AddAdminPage flow: role admin, businessId; onboarding when businessId absent) and MAY invite branch_admin, cashier, and trainer. admin MAY invite branch_admin, cashier, and trainer. branch_admin, cashier, and trainer MUST NOT create invitations.

| Inviter | admin | branch_admin | cashier | trainer |
|---------|-------|--------------|---------|---------|
| super_admin | ✓ | ✓ | ✓ | ✓ |
| admin | ✗ | ✓ | ✓ | ✓ |
| branch_admin | ✗ | ✗ | ✗ | ✗ |
| cashier | ✗ | ✗ | ✗ | ✗ |
| trainer | ✗ | ✗ | ✗ | ✗ |

#### Scenario: Admin cannot invite an admin

- GIVEN an authenticated admin
- WHEN they POST /api/invitations with role admin
- THEN the system SHALL reject the invitation

#### Scenario: super_admin invites trainer

- GIVEN an authenticated super_admin and a chosen business branch
- WHEN they POST /api/invitations with role trainer and branchId
- THEN the system SHALL return 201 with a valid invitation link

### Requirement: Branch Scoping

For branch-scoped roles (branch_admin, cashier, trainer), the invitation SHALL carry a branchId resolved from the explicit request `branchId`, or fall back to the inviter's own branchId. If neither exists, the system SHALL return 400. For role admin, branchId SHALL NOT be required; businessId SHALL govern (explicit request businessId, else inviter's, else None for onboarding).

#### Scenario: Fallback to inviter's branch

- GIVEN an admin with an own branchId inviting a cashier without passing branchId
- WHEN POST /api/invitations is sent
- THEN the invitation SHALL be created with the admin's branchId (201)

#### Scenario: Missing branch for employee

- GIVEN a super_admin (no own branch) inviting a trainer without branchId
- WHEN POST /api/invitations is sent
- THEN the system SHALL return 400 with a missing-branchId error

#### Scenario: Admin invite keeps business scope

- GIVEN a super_admin inviting an admin for an existing business
- WHEN POST /api/invitations is sent with role admin and businessId
- THEN the invitation SHALL carry the businessId and no branchId (201)

### Requirement: Validate Invitation

`GET /api/invitations/validate/<token>` SHALL return the invitation's email, role, name, businessId, branchId, and businessName when the token is valid and pending.

#### Scenario: Valid token

- GIVEN a pending, unexpired invitation
- WHEN validate is called for its token
- THEN the system SHALL return 200 with the invitation data

#### Scenario: Expired token

- GIVEN an invitation past its 72h expiry
- WHEN validate is called
- THEN the system SHALL return 400 with an expired error

#### Scenario: Used token

- GIVEN an already-accepted invitation
- WHEN validate is called
- THEN the system SHALL return 404

### Requirement: Accept Invitation with Name

The invitee SHALL enter name, password (min 8 chars), and confirmation on InvitePage; the Firebase Auth account SHALL be created client-side (existing flow). `POST /api/invitations/accept` SHALL accept `token`, `uid`, and the entered `name`, and SHALL store the ENTERED name on the Firestore user doc. The invitation SHALL be single-use: status becomes `accepted`; a second accept SHALL return 404.

#### Scenario: Accept stores entered name

- GIVEN a valid pending invitation and a Firebase Auth account created with the invitee's email
- WHEN accept is called with token, uid, and the entered name
- THEN the system SHALL create the user doc with the entered name, role, businessId, and branchId (201)
- AND the invitation SHALL be marked accepted

#### Scenario: Accept without name

- GIVEN accept is called with token and uid only
- THEN the user doc SHALL fall back to the invitation name, or empty

#### Scenario: Reusing an accepted token

- GIVEN an invitation already accepted
- WHEN accept is called again with the same token
- THEN the system SHALL return 404 and SHALL NOT create a duplicate user

### Requirement: UsersPage Invite Rewire

The "Invitar Empleado" create flow on UsersPage SHALL call createInvitation (NOT createUser / POST /users) and SHALL require a branch for branch-scoped roles. On success the UI SHALL show the copyable invitation link and SHALL NOT create a user doc. The edit flow SHALL remain on PUT /users, unchanged.

#### Scenario: Invite success shows link

- GIVEN an admin on UsersPage with the invite modal open
- WHEN they submit email, name, role, and branchId
- THEN the UI SHALL show the invitation link to copy
- AND no user SHALL appear in the list until the invitee accepts

#### Scenario: Edit still uses PUT /users

- GIVEN an existing user row
- WHEN the admin edits and saves
- THEN the system SHALL call PUT /users and SHALL NOT create an invitation