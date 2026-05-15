"""
Tests para el modelo de Client
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.client import ClientModel, ClientCreateSchema, ClientUpdateSchema


class TestClientModelValidateCreateData:
    """Tests para ClientModel.validate_create_data"""

    def test_valid_minimal_data(self):
        """Datos mínimos válidos"""
        data = {
            'name': 'Juan Pérez',
            'email': 'juan@test.com',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        result = ClientModel.validate_create_data(data.copy())
        assert result['name'] == 'Juan Pérez'
        assert result['email'] == 'juan@test.com'
        assert result['isActive'] is True
        assert result['status'] == 'active'

    def test_email_normalized_to_lowercase(self):
        """Email se normaliza a minúsculas"""
        data = {
            'name': 'Juan Pérez',
            'email': 'JUAN@TEST.COM',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        result = ClientModel.validate_create_data(data)
        assert result['email'] == 'juan@test.com'

    def test_phone_normalized(self):
        """Teléfono se normaliza"""
        data = {
            'name': 'Juan Pérez',
            'email': 'juan@test.com',
            'phone': '+58 414 123 4567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        result = ClientModel.validate_create_data(data)
        assert result['phone'] == '+58 414 123 4567'

    def test_name_trimmed(self):
        """Nombre se recorta"""
        data = {
            'name': '  Juan Pérez  ',
            'email': 'juan@test.com',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        result = ClientModel.validate_create_data(data)
        assert result['name'] == 'Juan Pérez'

    def test_with_optional_document_id(self):
        """Datos con documentId opcional"""
        data = {
            'name': 'Juan Pérez',
            'email': 'juan@test.com',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1',
            'documentId': 'V-30123456'
        }
        result = ClientModel.validate_create_data(data)
        assert result['documentId'] == 'V-30123456'

    def test_with_notes(self):
        """Datos con notas"""
        data = {
            'name': 'Juan Pérez',
            'email': 'juan@test.com',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1',
            'notes': 'Cliente preferencial'
        }
        result = ClientModel.validate_create_data(data)
        assert result['notes'] == 'Cliente preferencial'

    def test_missing_name(self):
        """Falta nombre"""
        data = {
            'email': 'juan@test.com',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        with pytest.raises(ValueError) as exc_info:
            ClientModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("name" in e for e in errors)

    def test_missing_email(self):
        """Falta email"""
        data = {
            'name': 'Juan Pérez',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        with pytest.raises(ValueError) as exc_info:
            ClientModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("email" in e for e in errors)

    def test_invalid_email_format(self):
        """Email con formato inválido"""
        data = {
            'name': 'Juan Pérez',
            'email': 'no-es-un-email',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        with pytest.raises(ValueError) as exc_info:
            ClientModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("email" in e.lower() for e in errors)

    def test_invalid_phone_format(self):
        """Teléfono con formato inválido"""
        data = {
            'name': 'Juan Pérez',
            'email': 'juan@test.com',
            'phone': 'abc123',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        with pytest.raises(ValueError) as exc_info:
            ClientModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("teléfono" in e.lower() for e in errors)

    def test_name_too_short(self):
        """Nombre muy corto"""
        data = {
            'name': 'Ju',
            'email': 'juan@test.com',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        with pytest.raises(ValueError) as exc_info:
            ClientModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("3 caracteres" in e for e in errors)

    def test_name_too_long(self):
        """Nombre muy largo"""
        data = {
            'name': 'A' * 101,
            'email': 'juan@test.com',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        with pytest.raises(ValueError) as exc_info:
            ClientModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("100 caracteres" in e for e in errors)

    def test_notes_too_long(self):
        """Notas muy largas"""
        data = {
            'name': 'Juan Pérez',
            'email': 'juan@test.com',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1',
            'notes': 'A' * 501
        }
        with pytest.raises(ValueError) as exc_info:
            ClientModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("500 caracteres" in e for e in errors)


class TestClientModelValidateUpdateData:
    """Tests para ClientModel.validate_update_data"""

    def test_valid_name_update(self):
        """Actualización válida de nombre"""
        data = {'name': 'Juan Pérez Actualizado'}
        result = ClientModel.validate_update_data(data)
        assert result['name'] == 'Juan Pérez Actualizado'

    def test_valid_status_update(self):
        """Actualización válida de status"""
        data = {'status': 'suspended'}
        result = ClientModel.validate_update_data(data)
        assert result['status'] == 'suspended'

    def test_update_with_invalid_status(self):
        """Actualización con status inválido"""
        data = {'status': 'invalid_status'}
        with pytest.raises(ValueError) as exc_info:
            ClientModel.validate_update_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("status" in e.lower() for e in errors)

    def test_update_with_forbidden_field(self):
        """Actualización con campo prohibido"""
        data = {'membershipPlanId': 'new-plan'}
        with pytest.raises(ValueError) as exc_info:
            ClientModel.validate_update_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("no permitidos" in e.lower() for e in errors)

    def test_update_email_normalized(self):
        """Email se normaliza en actualización"""
        data = {'email': 'JUAN@TEST.COM'}
        result = ClientModel.validate_update_data(data)
        assert result['email'] == 'juan@test.com'


class TestClientModelFromFirestore:
    """Tests para ClientModel.from_firestore"""

    def test_converts_document_id(self):
        """Convierte el ID del documento"""
        data = {'name': 'Juan', 'email': 'juan@test.com'}
        result = ClientModel.from_firestore(data, 'client-123')
        assert result['id'] == 'client-123'

    def test_converts_timestamps(self):
        """Convierte timestamps a ISO format"""
        class MockTimestamp:
            def isoformat(self):
                return '2026-04-14T10:00:00'

        data = {
            'name': 'Juan',
            'membershipStart': MockTimestamp(),
            'membershipEnd': MockTimestamp(),
            'createdAt': MockTimestamp()
        }
        result = ClientModel.from_firestore(data, 'client-123')
        assert result['membershipStart'] == '2026-04-14T10:00:00'
        assert result['membershipEnd'] == '2026-04-14T10:00:00'
        assert result['createdAt'] == '2026-04-14T10:00:00'


class TestClientModelToFirestore:
    """Tests para ClientModel.to_firestore"""

    def test_removes_id_field(self):
        """Elimina el campo id"""
        data = {
            'id': 'client-123',
            'name': 'Juan',
            'email': 'juan@test.com'
        }
        result = ClientModel.to_firestore(data)
        assert 'id' not in result
        assert result['name'] == 'Juan'


class TestClientCreateSchema:
    """Tests para ClientCreateSchema"""

    def test_valid_data(self):
        """Datos válidos"""
        data = {
            'name': 'Juan Pérez',
            'email': 'juan@test.com',
            'phone': '+584141234567',
            'branchId': 'branch-1',
            'businessId': 'biz-1',
            'membershipPlanId': 'plan-1'
        }
        schema = ClientCreateSchema(data)
        result = schema.to_dict()
        assert result['name'] == 'Juan Pérez'
        assert result['isActive'] is True


class TestClientUpdateSchema:
    """Tests para ClientUpdateSchema"""

    def test_valid_status_update(self):
        """Actualización válida de status"""
        data = {'status': 'expired'}
        schema = ClientUpdateSchema(data)
        result = schema.to_dict()
        assert result['status'] == 'expired'