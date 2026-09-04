"""
Tests para el modelo de Invitation
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.invitation import InvitationModel


def _inviter(role='super_admin', uid='u1', business_id=None, branch_id=None, name='Owner'):
    """Factory de datos de invitador"""
    return {
        'uid': uid,
        'role': role,
        'businessId': business_id,
        'branchId': branch_id,
        'name': name
    }


class TestRoleInviteMatrix:
    """Tests para la matriz de roles que pueden invitar"""

    def test_super_admin_can_invite_all_roles(self):
        """super_admin puede invitar admin y roles de sucursal"""
        allowed = set(InvitationModel.ROLE_CAN_INVITE['super_admin'])
        assert allowed == {'admin', 'branch_admin', 'cashier', 'trainer'}

    @pytest.mark.parametrize('target_role', ['admin', 'branch_admin', 'cashier', 'trainer'])
    def test_super_admin_invites_role_succeeds(self, target_role):
        """super_admin crea invitación para cualquier rol"""
        data = InvitationModel.create_invitation_data(
            email=f'{target_role}@test.com',
            inviter_data=_inviter(),
            target_role=target_role,
            business_id_from_request='biz-1',
            branch_id_from_request=None if target_role == 'admin' else 'branch-1'
        )
        assert data['role'] == target_role
        assert data['status'] == 'pending'

    @pytest.mark.parametrize('target_role', ['branch_admin', 'cashier', 'trainer'])
    def test_admin_can_invite_branch_roles(self, target_role):
        """admin puede invitar roles de sucursal"""
        data = InvitationModel.create_invitation_data(
            email=f'{target_role}@test.com',
            inviter_data=_inviter(role='admin', uid='u2', business_id='biz-1', branch_id='branch-1', name='Admin'),
            target_role=target_role
        )
        assert data['role'] == target_role

    def test_admin_cannot_invite_admin(self):
        """admin no puede invitar a otro admin"""
        with pytest.raises(ValueError, match='no puede invitar'):
            InvitationModel.create_invitation_data(
                email='admin2@test.com',
                inviter_data=_inviter(role='admin', uid='u2', business_id='biz-1', branch_id='branch-1', name='Admin'),
                target_role='admin'
            )

    @pytest.mark.parametrize('inviter_role', ['branch_admin', 'cashier', 'trainer'])
    def test_branch_roles_cannot_invite(self, inviter_role):
        """branch_admin/cashier/trainer no pueden crear invitaciones"""
        with pytest.raises(ValueError, match='no puede invitar'):
            InvitationModel.create_invitation_data(
                email='cashier@test.com',
                inviter_data=_inviter(role=inviter_role, uid='u3', business_id='biz-1', branch_id='branch-1', name='X'),
                target_role='cashier'
            )

    def test_can_invite_role_helper(self):
        """Helper can_invite_role refleja la matriz"""
        assert InvitationModel.can_invite_role('super_admin', 'trainer') is True
        assert InvitationModel.can_invite_role('admin', 'cashier') is True
        assert InvitationModel.can_invite_role('admin', 'admin') is False
        assert InvitationModel.can_invite_role('cashier', 'cashier') is False


class TestBranchResolution:
    """Tests para la resolución de branchId/businessId en roles de sucursal"""

    def test_request_branch_takes_precedence(self):
        """branchId del request gana sobre el del invitador"""
        data = InvitationModel.create_invitation_data(
            email='cashier@test.com',
            inviter_data=_inviter(role='admin', uid='u2', business_id='biz-1', branch_id='branch-1', name='Admin'),
            target_role='cashier',
            branch_id_from_request='branch-2'
        )
        assert data['branchId'] == 'branch-2'
        assert data['businessId'] == 'biz-1'

    def test_request_business_takes_precedence(self):
        """businessId del request gana sobre el del invitador"""
        data = InvitationModel.create_invitation_data(
            email='cashier@test.com',
            inviter_data=_inviter(role='admin', uid='u2', business_id='biz-1', branch_id='branch-1', name='Admin'),
            target_role='cashier',
            business_id_from_request='biz-2'
        )
        assert data['businessId'] == 'biz-2'
        assert data['branchId'] == 'branch-1'

    def test_fallback_to_inviter_branch(self):
        """Spec: Fallback a la sucursal del invitador cuando no se pasa branchId"""
        data = InvitationModel.create_invitation_data(
            email='cashier@test.com',
            inviter_data=_inviter(role='admin', uid='u2', business_id='biz-1', branch_id='branch-1', name='Admin'),
            target_role='cashier'
        )
        assert data['branchId'] == 'branch-1'
        assert data['businessId'] == 'biz-1'

    def test_missing_branch_raises_value_error(self):
        """Spec: Missing branch for employee -> 400 (ValueError)"""
        with pytest.raises(ValueError, match='branchId y businessId'):
            InvitationModel.create_invitation_data(
                email='trainer@test.com',
                inviter_data=_inviter(),
                target_role='trainer',
                business_id_from_request='biz-1'
            )

    def test_missing_business_raises_value_error(self):
        """businessId requerido para roles de sucursal (D3)"""
        with pytest.raises(ValueError, match='branchId y businessId'):
            InvitationModel.create_invitation_data(
                email='trainer@test.com',
                inviter_data=_inviter(),
                target_role='trainer',
                branch_id_from_request='branch-1'
            )

    def test_branch_role_without_any_scope_raises(self):
        """Sin branchId ni businessId (ni request ni invitador) -> ValueError"""
        with pytest.raises(ValueError, match='branchId y businessId'):
            InvitationModel.create_invitation_data(
                email='cashier@test.com',
                inviter_data=_inviter(),
                target_role='cashier'
            )


class TestAdminInviteScoping:
    """Tests para el path admin: businessId gobierna, branchId queda None"""

    def test_super_admin_invites_admin_with_business(self):
        """Spec: Admin invite keeps business scope -> businessId, sin branchId"""
        data = InvitationModel.create_invitation_data(
            email='admin@test.com',
            inviter_data=_inviter(),
            target_role='admin',
            business_id_from_request='biz-1'
        )
        assert data['businessId'] == 'biz-1'
        assert data['branchId'] is None

    def test_super_admin_invites_admin_onboarding(self):
        """super_admin -> admin sin negocio: onboarding (ambos None)"""
        data = InvitationModel.create_invitation_data(
            email='admin@test.com',
            inviter_data=_inviter(),
            target_role='admin'
        )
        assert data['businessId'] is None
        assert data['branchId'] is None

    def test_admin_target_does_not_require_branch(self):
        """Rol admin no dispara la validación de branchId de roles de sucursal"""
        with pytest.raises(ValueError, match='no puede invitar'):
            InvitationModel.create_invitation_data(
                email='admin2@test.com',
                inviter_data=_inviter(role='admin', uid='u2', business_id='biz-1', branch_id=None, name='Admin'),
                target_role='admin'
            )