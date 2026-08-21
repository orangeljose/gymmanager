"""
Tests para la ruta DELETE /api/payments/<payment_id>

Cubre el mapeo HTTP del status envelope del servicio:
- 200 success (super_admin / admin / branch_admin)
- 404 not_found
- 403 cashier / trainer (rol no permitido)
- 403 branch_admin cross-branch (sede distinta)

La lógica de negocio (fetch, branch check, soft delete, recalc) se valida en
los tests unitarios de PaymentService.delete_payment; aquí solo se verifica el
mapeo del endpoint a las respuestas HTTP. Se sigue el patrón de los otros tests
de rutas: se parchea FirebaseService y el PaymentService alrededor de cada
request para no mutar estado global entre archivos.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import json
from unittest.mock import patch, MagicMock


def create_mock_service(role='super_admin', uid='admin-123', business_id='biz-1'):
    """Factory para crear mocks de FirebaseService"""
    user_data = {
        'uid': uid,
        'email': f'{role}@test.com',
        'name': f'{role.title()} Test',
        'role': role,
        'businessId': business_id,
        'branchId': None if role == 'super_admin' else 'branch-1',
        'permissions': ['*'] if role == 'super_admin' else ['read_clients', 'write_payments'],
        'isActive': True
    }

    mock = MagicMock()
    mock.verify_token.return_value = {'uid': uid}
    mock.get_user_by_uid.return_value = user_data
    mock.query_firestore.return_value = []
    mock.get_document.return_value = None
    mock.create_document.return_value = {'id': 'new-doc-id', 'isActive': True}
    mock.update_document.return_value = True
    return mock


@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    """Resetea singleton antes de cada archivo de test"""
    from services import firebase_service
    firebase_service.FirebaseService._reset()
    yield
    firebase_service.FirebaseService._reset()


@pytest.fixture
def auth_header():
    return {'Authorization': 'Bearer test-token'}


def _envelope_client(role, status, data=None):
    """
    Devuelve (app, firebase_mock, payment_service_cls, instance).
    La request se hace en el método de test dentro de los `with patch(...)`.
    """
    mock = create_mock_service(role=role)
    payment_service_cls = MagicMock()
    instance = payment_service_cls.return_value
    instance.delete_payment.return_value = {'status': status, 'data': data}

    with patch('services.firebase_service.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
    app.config['TESTING'] = True

    return app, mock, payment_service_cls, instance


def _delete(app, mock, payment_service_cls, payment_id, headers=None):
    """Ejecuta la request DELETE con los patches activos (patrón test_plans)."""
    client = app.test_client()
    with patch('services.firebase_service.FirebaseService', return_value=mock), \
         patch('routes.payments.PaymentService', payment_service_cls):
        return client.delete(f'/api/payments/{payment_id}', headers=headers or {})


MEMBERSHIP_DATA = {
    'clientId': 'client-001',
    'membershipStart': '2026-03-01T00:00:00Z',
    'membershipEnd': '2026-05-01T00:00:00Z',
    'membershipPlanId': 'plan-mensual',
    'isActive': True,
    'status': 'active',
}


class TestDeletePaymentSuccess:
    def test_super_admin_deletes_payment_200(self, auth_header):
        app, mock, cls, instance = _envelope_client('super_admin', 'success', MEMBERSHIP_DATA)
        response = _delete(app, mock, cls, 'payment-001', auth_header)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['clientId'] == 'client-001'
        instance.delete_payment.assert_called_once()

    def test_admin_deletes_payment_200(self, auth_header):
        app, mock, cls, instance = _envelope_client('admin', 'success', MEMBERSHIP_DATA)
        response = _delete(app, mock, cls, 'payment-001', auth_header)
        assert response.status_code == 200
        assert json.loads(response.data)['success'] is True

    def test_branch_admin_deletes_own_branch_payment_200(self, auth_header):
        app, mock, cls, instance = _envelope_client('branch_admin', 'success', MEMBERSHIP_DATA)
        response = _delete(app, mock, cls, 'payment-001', auth_header)
        assert response.status_code == 200
        assert json.loads(response.data)['success'] is True


class TestDeletePaymentNotFound:
    def test_missing_payment_404(self, auth_header):
        app, mock, cls, instance = _envelope_client('super_admin', 'not_found')
        response = _delete(app, mock, cls, 'nonexistent', auth_header)
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False


class TestDeletePaymentForbidden:
    def test_cashier_role_denied_403(self, auth_header):
        app, mock, cls, instance = _envelope_client('cashier', 'forbidden')
        response = _delete(app, mock, cls, 'payment-001', auth_header)
        assert response.status_code == 403
        assert json.loads(response.data)['success'] is False

    def test_trainer_role_denied_403(self, auth_header):
        app, mock, cls, instance = _envelope_client('trainer', 'forbidden')
        response = _delete(app, mock, cls, 'payment-001', auth_header)
        assert response.status_code == 403

    def test_branch_admin_cross_branch_403(self, auth_header):
        app, mock, cls, instance = _envelope_client('branch_admin', 'forbidden')
        response = _delete(app, mock, cls, 'payment-001', auth_header)
        assert response.status_code == 403
        assert json.loads(response.data)['success'] is False
        # No debe haberse intentado modificar el pago
        instance.delete_payment.assert_called_once()


class TestDeletePaymentRequiresAuth:
    def test_no_token_returns_401(self):
        app, mock, cls, instance = _envelope_client('super_admin', 'success', MEMBERSHIP_DATA)
        response = _delete(app, mock, cls, 'payment-001')
        assert response.status_code == 401
