"""
Tests para el modelo de User
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.user import UserModel


class TestUserModelValidateRole:
    """Tests para UserModel.validate_role"""

    def test_valid_super_admin(self):
        """Rol super_admin válido"""
        assert UserModel.validate_role('super_admin') is True

    def test_valid_branch_admin(self):
        """Rol branch_admin válido"""
        assert UserModel.validate_role('branch_admin') is True

    def test_valid_cashier(self):
        """Rol cashier válido"""
        assert UserModel.validate_role('cashier') is True

    def test_valid_trainer(self):
        """Rol trainer válido"""
        assert UserModel.validate_role('trainer') is True

    def test_invalid_role(self):
        """Rol inválido"""
        assert UserModel.validate_role('admin') is False
        assert UserModel.validate_role('user') is False
        assert UserModel.validate_role('') is False
        assert UserModel.validate_role('SUPER_ADMIN') is False


class TestUserModelGetPermissions:
    """Tests para UserModel.get_permissions"""

    def test_super_admin_has_all_permissions(self):
        """Super admin tiene permisos wildcard"""
        perms = UserModel.get_permissions('super_admin')
        assert perms == ['*']

    def test_branch_admin_permissions(self):
        """Branch admin tiene permisos específicos"""
        perms = UserModel.get_permissions('branch_admin')
        assert '*' not in perms
        assert 'read_clients' in perms
        assert 'write_clients' in perms
        assert 'read_payments' in perms
        assert 'write_payments' in perms
        assert 'read_reports' in perms

    def test_cashier_permissions(self):
        """Cashier tiene permisos específicos"""
        perms = UserModel.get_permissions('cashier')
        assert 'read_clients' in perms
        assert 'write_payments' in perms
        assert 'write_clients' not in perms
        assert 'read_reports' not in perms

    def test_trainer_permissions(self):
        """Trainer tiene permisos específicos"""
        perms = UserModel.get_permissions('trainer')
        assert perms == ['read_clients']

    def test_unknown_role_returns_empty(self):
        """Rol desconocido retorna lista vacía"""
        perms = UserModel.get_permissions('unknown_role')
        assert perms == []


class TestUserModelHasPermission:
    """Tests para UserModel.has_permission"""

    def test_super_admin_can_do_anything(self):
        """Super admin puede hacer cualquier cosa"""
        assert UserModel.has_permission('super_admin', 'read_clients') is True
        assert UserModel.has_permission('super_admin', 'write_payments') is True
        assert UserModel.has_permission('super_admin', 'delete_business') is True

    def test_branch_admin_can_read_clients(self):
        """Branch admin puede leer clientes"""
        assert UserModel.has_permission('branch_admin', 'read_clients') is True

    def test_branch_admin_cannot_write_users(self):
        """Branch admin no puede escribir usuarios"""
        assert UserModel.has_permission('branch_admin', 'write_users') is False

    def test_cashier_can_write_payments(self):
        """Cashier puede escribir pagos"""
        assert UserModel.has_permission('cashier', 'write_payments') is True

    def test_cashier_cannot_read_reports(self):
        """Cashier no puede leer reportes"""
        assert UserModel.has_permission('cashier', 'read_reports') is False

    def test_trainer_can_read_clients(self):
        """Trainer puede leer clientes"""
        assert UserModel.has_permission('trainer', 'read_clients') is True

    def test_trainer_cannot_write_payments(self):
        """Trainer no puede escribir pagos"""
        assert UserModel.has_permission('trainer', 'write_payments') is False


class TestUserModelCanAccessBusiness:
    """Tests para UserModel.can_access_business"""

    def test_same_business_allowed(self):
        """Mismo negocio permite acceso"""
        assert UserModel.can_access_business('biz-1', 'biz-1') is True

    def test_different_business_denied(self):
        """Diferente negocio denies acceso"""
        assert UserModel.can_access_business('biz-1', 'biz-2') is False


class TestUserModelCanAccessBranch:
    """Tests para UserModel.can_access_branch"""

    def test_super_admin_can_access_any_branch(self):
        """Super admin puede acceder a cualquier sede"""
        assert UserModel.can_access_branch('branch-1', 'branch-2', 'super_admin') is True
        assert UserModel.can_access_branch(None, 'branch-1', 'super_admin') is True

    def test_branch_admin_same_branch_allowed(self):
        """Branch admin puede acceder a su propia sede"""
        assert UserModel.can_access_branch('branch-1', 'branch-1', 'branch_admin') is True

    def test_branch_admin_different_branch_denied(self):
        """Branch admin no puede acceder a otra sede"""
        assert UserModel.can_access_branch('branch-1', 'branch-2', 'branch_admin') is False

    def test_cashier_same_branch_allowed(self):
        """Cashier puede acceder a su propia sede"""
        assert UserModel.can_access_branch('branch-1', 'branch-1', 'cashier') is True

    def test_cashier_different_branch_denied(self):
        """Cashier no puede acceder a otra sede"""
        assert UserModel.can_access_branch('branch-1', 'branch-2', 'cashier') is False

    def test_trainer_same_branch_allowed(self):
        """Trainer puede acceder a su propia sede"""
        assert UserModel.can_access_branch('branch-1', 'branch-1', 'trainer') is True

    def test_trainer_different_branch_denied(self):
        """Trainer no puede acceder a otra sede"""
        assert UserModel.can_access_branch('branch-1', 'branch-2', 'trainer') is False


class TestUserModelFromFirestore:
    """Tests para UserModel.from_firestore"""

    def test_converts_document_id(self):
        """Convierte el ID del documento"""
        data = {'name': 'Juan', 'email': 'juan@test.com'}
        result = UserModel.from_firestore(data, 'user-123')
        assert result['id'] == 'user-123'

    def test_preserves_all_fields(self):
        """Preserva todos los campos"""
        data = {
            'name': 'Juan',
            'email': 'juan@test.com',
            'role': 'cashier',
            'businessId': 'biz-1'
        }
        result = UserModel.from_firestore(data, 'user-123')
        assert result['name'] == 'Juan'
        assert result['email'] == 'juan@test.com'
        assert result['role'] == 'cashier'

    def test_converts_timestamp_to_isoformat(self):
        """Convierte timestamps a ISO format"""
        class MockTimestamp:
            def isoformat(self):
                return '2026-04-14T10:00:00'

        data = {
            'name': 'Juan',
            'createdAt': MockTimestamp()
        }
        result = UserModel.from_firestore(data, 'user-123')
        assert result['createdAt'] == '2026-04-14T10:00:00'

    def test_does_not_modify_original_data(self):
        """No modifica el data original"""
        original_data = {'name': 'Juan', 'email': 'juan@test.com'}
        UserModel.from_firestore(original_data, 'user-123')
        assert 'id' not in original_data


class TestUserModelToFirestore:
    """Tests para UserModel.to_firestore"""

    def test_removes_id_field(self):
        """Elimina el campo id"""
        data = {
            'id': 'user-123',
            'name': 'Juan',
            'email': 'juan@test.com'
        }
        result = UserModel.to_firestore(data)
        assert 'id' not in result
        assert result['name'] == 'Juan'

    def test_preserves_other_fields(self):
        """Preserva los demás campos"""
        data = {
            'name': 'Juan',
            'email': 'juan@test.com',
            'role': 'cashier'
        }
        result = UserModel.to_firestore(data)
        assert result['name'] == 'Juan'
        assert result['email'] == 'juan@test.com'
        assert result['role'] == 'cashier'

    def test_does_not_modify_original_data(self):
        """No modifica el data original"""
        original_data = {'name': 'Juan', 'email': 'juan@test.com'}
        UserModel.to_firestore(original_data)
        assert 'id' not in original_data