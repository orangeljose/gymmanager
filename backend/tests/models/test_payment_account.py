"""
Tests para el modelo de PaymentAccount
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.payment_account import (
    PaymentAccountModel,
    PaymentAccountCreateSchema,
    PaymentAccountUpdateSchema
)


class TestPaymentAccountModelValidateCreateData:
    """Tests para PaymentAccountModel.validate_create_data"""

    def test_valid_zelle_account(self):
        """Datos válidos para cuenta Zelle"""
        data = {
            'type': 'zelle',
            'identifier': 'test@example.com',
            'businessId': 'test-business'
        }
        result = PaymentAccountModel.validate_create_data(data.copy())
        assert result['type'] == 'zelle'
        assert result['identifier'] == 'test@example.com'
        assert result['isActive'] is True

    def test_valid_pago_movil_account(self):
        """Datos válidos para cuenta Pago Móvil"""
        data = {
            'type': 'pago_movil',
            'identifier': '+584141234567',
            'businessId': 'test-business'
        }
        result = PaymentAccountModel.validate_create_data(data)
        assert result['type'] == 'pago_movil'
        assert result['identifier'] == '+584141234567'

    def test_valid_bank_account(self):
        """Datos válidos para cuenta bancaria"""
        data = {
            'type': 'bank',
            'identifier': '12345678901234567890',
            'businessId': 'test-business'
        }
        result = PaymentAccountModel.validate_create_data(data)
        assert result['type'] == 'bank'
        assert result['identifier'] == '12345678901234567890'

    def test_missing_required_type(self):
        """Falta campo requerido 'type'"""
        data = {
            'identifier': 'test@example.com',
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("'type'" in e for e in errors)

    def test_missing_required_identifier(self):
        """Falta campo requerido 'identifier'"""
        data = {
            'type': 'zelle',
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("identificador" in e.lower() for e in errors)

    def test_missing_required_businessId(self):
        """Falta campo requerido 'businessId'"""
        data = {
            'type': 'zelle',
            'identifier': 'test@example.com'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("'businessId'" in e for e in errors)

    def test_invalid_type(self):
        """type debe ser zelle, pago_movil o bank"""
        data = {
            'type': 'paypal',
            'identifier': 'test@example.com',
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("tipo" in e.lower() for e in errors)

    def test_zelle_invalid_email_format(self):
        """Email Zelle debe ser válido"""
        data = {
            'type': 'zelle',
            'identifier': 'not-an-email',
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("zelle" in e.lower() and "válido" in e.lower() for e in errors)

    def test_zelle_email_normalized_to_lowercase(self):
        """Email Zelle se convierte a minúsculas"""
        data = {
            'type': 'zelle',
            'identifier': 'TEST@EXAMPLE.COM',
            'businessId': 'test-business'
        }
        result = PaymentAccountModel.validate_create_data(data)
        assert result['identifier'] == 'test@example.com'

    def test_pago_movil_invalid_phone(self):
        """Teléfono pago móvil debe ser válido"""
        data = {
            'type': 'pago_movil',
            'identifier': '123',  # Muy corto
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("teléfono" in e.lower() for e in errors)

    def test_pago_movil_valid_phone_formats(self):
        """Teléfonos válidos para pago móvil"""
        valid_phones = [
            '+584141234567',
            '0414-123-4567',
            '+58 414 123 4567',
            '584141234567'
        ]
        for phone in valid_phones:
            data = {
                'type': 'pago_movil',
                'identifier': phone,
                'businessId': 'test-business'
            }
            result = PaymentAccountModel.validate_create_data(data)
            assert result['identifier'] == phone

    def test_bank_account_too_short(self):
        """Número de cuenta bancaria debe tener al menos 4 dígitos"""
        data = {
            'type': 'bank',
            'identifier': '123',
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("cuenta" in e.lower() for e in errors)

    def test_auto_label_for_zelle(self):
        """Label auto-generado para Zelle sin label"""
        data = {
            'type': 'zelle',
            'identifier': 'user@example.com',
            'businessId': 'test-business'
        }
        result = PaymentAccountModel.validate_create_data(data)
        assert result['label'] == 'user'

    def test_auto_label_for_pago_movil(self):
        """Label auto-generado para Pago Móvil sin label"""
        data = {
            'type': 'pago_movil',
            'identifier': '+584141234567',
            'businessId': 'test-business'
        }
        result = PaymentAccountModel.validate_create_data(data)
        assert result['label'] == '+584141234567'

    def test_custom_label(self):
        """Label personalizado"""
        data = {
            'type': 'zelle',
            'identifier': 'test@example.com',
            'label': 'Mi Zelle Personal',
            'businessId': 'test-business'
        }
        result = PaymentAccountModel.validate_create_data(data)
        assert result['label'] == 'Mi Zelle Personal'

    def test_label_too_long(self):
        """Label no puede exceder 50 caracteres"""
        data = {
            'type': 'zelle',
            'identifier': 'test@example.com',
            'label': 'A' * 51,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("alias" in e.lower() for e in errors)

    def test_description_too_long(self):
        """Description no puede exceder 200 caracteres"""
        data = {
            'type': 'zelle',
            'identifier': 'test@example.com',
            'description': 'A' * 201,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("descripción" in e.lower() for e in errors)


class TestPaymentAccountModelValidateUpdateData:
    """Tests para PaymentAccountModel.validate_update_data"""

    def test_update_valid_identifier(self):
        """Actualización válida de identifier"""
        data = {'identifier': 'new@example.com'}
        result = PaymentAccountModel.validate_update_data(data)
        assert result['identifier'] == 'new@example.com'

    def test_update_valid_label(self):
        """Actualización válida de label"""
        data = {'label': 'Nuevo Label'}
        result = PaymentAccountModel.validate_update_data(data)
        assert result['label'] == 'Nuevo Label'

    def test_update_valid_isActive(self):
        """Actualización válida de isActive"""
        data = {'isActive': False}
        result = PaymentAccountModel.validate_update_data(data)
        assert result['isActive'] is False

    def test_update_invalid_field(self):
        """Campo no permitido"""
        data = {'invalidField': 'value'}
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_update_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("no permitidos" in e.lower() for e in errors)

    def test_update_zelle_invalid_email(self):
        """Email Zelle inválido en actualización"""
        data = {'identifier': 'not-email'}
        result = PaymentAccountModel.validate_update_data(data)
        assert 'identifier' in result
        assert result['identifier'] == 'not-email'

    def test_update_invalid_isActive_type(self):
        """isActive debe ser booleano"""
        data = {'isActive': 'false'}
        with pytest.raises(ValueError) as exc_info:
            PaymentAccountModel.validate_update_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("booleano" in e.lower() for e in errors)


class TestPaymentAccountCreateSchema:
    """Tests para PaymentAccountCreateSchema"""

    def test_schema_valid_zelle(self, sample_payment_account_data):
        """Schema procesa cuenta Zelle válida"""
        schema = PaymentAccountCreateSchema(sample_payment_account_data)
        result = schema.to_dict()
        assert result['type'] == 'zelle'
        assert result['isActive'] is True

    def test_schema_invalid_raises_error(self):
        """Schema lanza error en datos inválidos"""
        data = {
            'type': 'invalid_type',
            'identifier': '',
            'businessId': ''
        }
        with pytest.raises(ValueError):
            PaymentAccountCreateSchema(data)


class TestPaymentAccountFromFirestore:
    """Tests para PaymentAccountModel.from_firestore"""

    def test_from_firestore_adds_id(self):
        """Agrega id al convertir"""
        doc = {
            'type': 'zelle',
            'identifier': 'test@example.com',
            'businessId': 'test-business'
        }
        result = PaymentAccountModel.from_firestore(doc, 'acc-123')
        assert result['id'] == 'acc-123'

    def test_from_firestore_converts_timestamp(self):
        """Convierte timestamps"""
        from datetime import datetime
        doc = {
            'type': 'zelle',
            'identifier': 'test@example.com',
            'createdAt': datetime(2026, 5, 13, 10, 0, 0)
        }
        result = PaymentAccountModel.from_firestore(doc, 'acc-123')
        assert 'createdAt' in result
        assert isinstance(result['createdAt'], str)