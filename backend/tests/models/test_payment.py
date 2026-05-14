"""
Tests para el modelo de Payment (expandido con zelle y pago_movil)
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.payment import PaymentModel, PaymentCreateSchema, PaymentSyncSchema


class TestPaymentModelValidateCreateData:
    """Tests para PaymentModel.validate_create_data"""

    def test_valid_cash_payment(self):
        """Pago en efectivo válido"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'cash',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte'
        }
        result = PaymentModel.validate_create_data(data.copy())
        assert result['method'] == 'cash'
        assert result['monthsPaid'] == 1
        assert result['methodDetails'] == {}

    def test_valid_card_payment(self):
        """Pago con tarjeta válido"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'card',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {
                'cardLast4': '1234',
                'cardBrand': 'Visa'
            }
        }
        result = PaymentModel.validate_create_data(data)
        assert result['method'] == 'card'
        assert result['methodDetails']['cardLast4'] == '1234'

    def test_valid_transfer_payment(self):
        """Pago con transferencia válido"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'transfer',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {
                'reference': 'REF-123456'
            }
        }
        result = PaymentModel.validate_create_data(data)
        assert result['method'] == 'transfer'
        assert result['methodDetails']['reference'] == 'REF-123456'

    def test_valid_zelle_payment(self):
        """Pago con Zelle válido"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'zelle',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {
                'senderEmail': 'cliente@example.com',
                'destinationAccountId': 'acc-001'
            }
        }
        result = PaymentModel.validate_create_data(data)
        assert result['method'] == 'zelle'
        assert result['methodDetails']['senderEmail'] == 'cliente@example.com'
        assert result['methodDetails']['destinationAccountId'] == 'acc-001'

    def test_valid_pago_movil_payment(self):
        """Pago con Pago Móvil válido"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'pago_movil',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {
                'phoneSender': '+584141234567',
                'paymentCode': 'PM-12345678',
                'destinationAccountId': 'acc-002'
            }
        }
        result = PaymentModel.validate_create_data(data)
        assert result['method'] == 'pago_movil'
        assert result['methodDetails']['phoneSender'] == '+584141234567'
        assert result['methodDetails']['paymentCode'] == 'PM-12345678'

    def test_missing_required_client_id(self):
        """Falta clientId"""
        data = {
            'amount': 35000,
            'method': 'cash',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('clientId' in e for e in errors)

    def test_missing_required_amount(self):
        """Falta amount"""
        data = {
            'clientId': 'client-001',
            'method': 'cash',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('amount' in e for e in errors)

    def test_invalid_method(self):
        """method debe ser válido"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'bitcoin',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('método' in e.lower() for e in errors)

    def test_invalid_amount_not_integer(self):
        """amount debe ser entero"""
        data = {
            'clientId': 'client-001',
            'amount': '35000',
            'method': 'cash',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('entero' in e.lower() for e in errors)

    def test_invalid_amount_negative(self):
        """amount no puede ser negativo"""
        data = {
            'clientId': 'client-001',
            'amount': -1000,
            'method': 'cash',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte'
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('positivo' in e.lower() for e in errors)

    def test_zelle_missing_sender_email(self):
        """Zelle requiere senderEmail"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'zelle',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {
                'destinationAccountId': 'acc-001'
            }
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('zelle' in e.lower() or 'senderemail' in e.lower() for e in errors)

    def test_pago_movil_missing_phone_sender(self):
        """Pago Móvil requiere phoneSender"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'pago_movil',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {
                'paymentCode': 'PM-12345678'
            }
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('pago' in e.lower() and 'móvil' in e.lower() or 'mobil' in e.lower() or 'phonesender' in e.lower() for e in errors)

    def test_pago_movil_missing_payment_code(self):
        """Pago Móvil requiere paymentCode"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'pago_movil',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {
                'phoneSender': '+584141234567'
            }
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('pago' in e.lower() and ('móvil' in e.lower() or 'mobil' in e.lower()) or 'paymentcode' in e.lower() for e in errors)

    def test_card_missing_card_last4(self):
        """Tarjeta requiere cardLast4"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'card',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {}
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('tarjeta' in e.lower() for e in errors)

    def test_card_invalid_card_last4_format(self):
        """cardLast4 debe tener exactamente 4 dígitos"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'card',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {
                'cardLast4': '12345'  # 5 dígitos
            }
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('4 dígitos' in e for e in errors)

    def test_transfer_missing_reference(self):
        """Transferencia requiere reference"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'transfer',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'methodDetails': {}
        }
        with pytest.raises(ValueError) as exc_info:
            PaymentModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any('transferencia' in e.lower() for e in errors)

    def test_all_payment_methods_valid(self):
        """Todos los métodos de pago son válidos"""
        valid_methods = ['cash', 'card', 'transfer', 'zelle', 'pago_movil', 'other']
        for method in valid_methods:
            data = {
                'clientId': 'client-001',
                'amount': 35000,
                'method': method,
                'membershipPlanId': 'plan-mensual',
                'branchId': 'sede-norte'
            }
            result = PaymentModel.validate_create_data(data)
            assert result['method'] == method


class TestPaymentSyncSchema:
    """Tests para PaymentSyncSchema"""

    def test_sync_valid_single_payment(self):
        """Sync de un pago válido"""
        data = [{
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'cash',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'localId': 'offline-001',
            'registeredAt': '2026-05-13T10:00:00Z'
        }]
        schema = PaymentSyncSchema(data)
        result = schema.to_list()
        assert len(result) == 1
        assert result[0]['localId'] == 'offline-001'

    def test_sync_missing_local_id(self):
        """Sync requiere localId"""
        data = [{
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'cash',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'registeredAt': '2026-05-13T10:00:00Z'
        }]
        with pytest.raises(ValueError) as exc_info:
            PaymentSyncSchema(data)
        errors = exc_info.value.args[0]['errors']
        assert any('localId' in e for e in errors)

    def test_sync_missing_registered_at(self):
        """Sync requiere registeredAt"""
        data = [{
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'cash',
            'membershipPlanId': 'plan-mensual',
            'branchId': 'sede-norte',
            'localId': 'offline-001'
        }]
        with pytest.raises(ValueError) as exc_info:
            PaymentSyncSchema(data)
        errors = exc_info.value.args[0]['errors']
        assert any('registeredAt' in e for e in errors)

    def test_sync_multiple_payments(self):
        """Sync de múltiples pagos"""
        data = [
            {
                'clientId': 'client-001',
                'amount': 35000,
                'method': 'cash',
                'membershipPlanId': 'plan-mensual',
                'branchId': 'sede-norte',
                'localId': 'offline-001',
                'registeredAt': '2026-05-13T10:00:00Z'
            },
            {
                'clientId': 'client-002',
                'amount': 90000,
                'method': 'zelle',
                'membershipPlanId': 'plan-trimestral',
                'branchId': 'sede-norte',
                'localId': 'offline-002',
                'registeredAt': '2026-05-13T11:00:00Z'
            }
        ]
        schema = PaymentSyncSchema(data)
        result = schema.to_list()
        assert len(result) == 2


class TestPaymentModelFromFirestore:
    """Tests para PaymentModel.from_firestore"""

    def test_from_firestore_adds_id(self):
        """Agrega id al convertir"""
        doc = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'cash'
        }
        result = PaymentModel.from_firestore(doc, 'payment-123')
        assert result['id'] == 'payment-123'

    def test_from_firestore_converts_timestamps(self):
        """Convierte timestamps a strings"""
        from datetime import datetime
        doc = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'cash',
            'createdAt': datetime(2026, 5, 13, 10, 0, 0),
            'endDate': datetime(2026, 6, 13, 10, 0, 0)
        }
        result = PaymentModel.from_firestore(doc, 'payment-123')
        assert isinstance(result['createdAt'], str)
        assert isinstance(result['endDate'], str)


class TestPaymentModelToFirestore:
    """Tests para PaymentModel.to_firestore"""

    def test_to_firestore_removes_id(self):
        """Elimina id al convertir"""
        data = {
            'id': 'payment-123',
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'cash'
        }
        result = PaymentModel.to_firestore(data)
        assert 'id' not in result
        assert result['clientId'] == 'client-001'

    def test_to_firestore_removes_local_id(self):
        """Elimina localId (solo para sync)"""
        data = {
            'clientId': 'client-001',
            'amount': 35000,
            'method': 'cash',
            'localId': 'offline-001'
        }
        result = PaymentModel.to_firestore(data)
        assert 'localId' not in result