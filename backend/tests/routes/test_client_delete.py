"""
Tests para la ruta DELETE /api/clients/<client_id>

Cubre la matriz HTTP del endpoint (patrón test_payment_delete.py):
- 200 super_admin / admin / branch_admin (sede propia)
- 403 cashier / trainer (rol no permitido por require_role)
- 403 branch_admin cross-branch (sede distinta)
- 404 cliente inexistente o ya eliminado
- 401 sin token

La lógica de negocio (fetch, branch check inline, soft delete con auditoría) se
valida en tests/unit/test_client_delete.py; aquí se verifica el mapeo HTTP.

NOTA de patrón: a diferencia del baseline roto (test_dashboard.py), cada request
se ejecuta DENTRO de los patches de los call-sites (middleware.auth_middleware y
routes.clients) para que cada test use SU mock y no dependa del orden de ejecución.
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


CLIENT_DATA = {
    'id': 'client-001',
    'name': 'Juan Pérez',
    'businessId': 'biz-1',
    'branchId': 'branch-1',
    'isActive': True,
}


def _app_with():
    """
    Crea la app Flask una vez (los call-sites se parchean por request).

    IMPORTANTE: el primer import del módulo `app` del proceso fija los bindings
    de FirebaseService en middleware/rutas para TODOS los archivos de test que
    no parcheen su call-site. Por eso aquí se parchea con un mock BIEN
    configurado (super_admin), equivalente al primer importer del baseline
    (test_payment_delete) — un MagicMock() trivial rompería require_role en los
    archivos siguientes.
    """
    with patch('services.firebase_service.FirebaseService', return_value=create_mock_service()):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app


@pytest.fixture(scope='module')
def app():
    return _app_with()


def _delete(app, mock, client_id, headers=None):
    """Ejecuta la request DELETE con los patches de call-site activos."""
    client = app.test_client()
    with patch('services.firebase_service.FirebaseService', return_value=mock), \
         patch('middleware.auth_middleware.FirebaseService', return_value=mock), \
         patch('routes.clients.FirebaseService', return_value=mock):
        return client.delete(f'/api/clients/{client_id}', headers=headers or {})


class TestDeleteClientSuccess:
    def test_super_admin_deletes_client_200(self, app, auth_header):
        mock = create_mock_service(role='super_admin')
        mock.get_document.return_value = dict(CLIENT_DATA)
        mock.update_document.return_value = True

        response = _delete(app, mock, 'client-001', auth_header)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['id'] == 'client-001'
        # Soft delete con auditoría: una sola actualización sobre 'clients'
        mock.update_document.assert_called_once()
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'clients'
        assert doc_id == 'client-001'
        assert update['isDeleted'] is True
        assert update['deletedBy'] == 'admin-123'
        assert update['deletedAt']

    def test_admin_deletes_client_200(self, app, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(CLIENT_DATA)
        mock.update_document.return_value = True

        response = _delete(app, mock, 'client-001', auth_header)

        assert response.status_code == 200
        assert json.loads(response.data)['success'] is True

    def test_branch_admin_deletes_own_branch_client_200(self, app, auth_header):
        mock = create_mock_service(role='branch_admin')
        mock.get_document.return_value = dict(CLIENT_DATA)
        mock.update_document.return_value = True

        response = _delete(app, mock, 'client-001', auth_header)

        assert response.status_code == 200
        assert json.loads(response.data)['success'] is True


class TestDeleteClientNotFound:
    def test_missing_client_404(self, app, auth_header):
        mock = create_mock_service(role='super_admin')
        mock.get_document.return_value = None

        response = _delete(app, mock, 'nonexistent', auth_header)

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        mock.update_document.assert_not_called()

    def test_already_deleted_client_404(self, app, auth_header):
        mock = create_mock_service(role='super_admin')
        client = dict(CLIENT_DATA)
        client['isDeleted'] = True
        mock.get_document.return_value = client

        response = _delete(app, mock, 'client-001', auth_header)

        assert response.status_code == 404
        assert json.loads(response.data)['success'] is False
        mock.update_document.assert_not_called()


class TestDeleteClientForbidden:
    def test_cashier_role_denied_403(self, app, auth_header):
        mock = create_mock_service(role='cashier')

        response = _delete(app, mock, 'client-001', auth_header)

        assert response.status_code == 403
        assert json.loads(response.data)['success'] is False
        mock.get_document.assert_not_called()

    def test_trainer_role_denied_403(self, app, auth_header):
        mock = create_mock_service(role='trainer')

        response = _delete(app, mock, 'client-001', auth_header)

        assert response.status_code == 403
        assert json.loads(response.data)['success'] is False
        mock.get_document.assert_not_called()

    def test_branch_admin_cross_branch_403(self, app, auth_header):
        mock = create_mock_service(role='branch_admin')
        client = dict(CLIENT_DATA)
        client['branchId'] = 'branch-2'  # sede distinta a la del branch_admin
        mock.get_document.return_value = client

        response = _delete(app, mock, 'client-001', auth_header)

        assert response.status_code == 403
        assert json.loads(response.data)['success'] is False
        # No debe haberse intentado modificar el cliente
        mock.update_document.assert_not_called()


class TestDeleteClientRequiresAuth:
    def test_no_token_returns_401(self, app):
        mock = create_mock_service(role='super_admin')
        mock.get_document.return_value = dict(CLIENT_DATA)

        response = _delete(app, mock, 'client-001')

        assert response.status_code == 401