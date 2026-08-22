"""
Tests unitarios para el soft delete de clientes y el filtrado isDeleted.

Cubre (patrón test_dashboard.py: mock de FirebaseService + Flask test client):
- GET /api/clients excluye eliminados (y legacy sin campo)
- GET /api/clients/:id devuelve 404 para eliminados
- DELETE /api/clients/:id: 404 missing / 404 ya-eliminado / 403 cross-branch /
  success escribe isDeleted + deletedBy + deletedAt y NUNCA toca la colección payments
- PUT /api/clients/:id devuelve 404 para eliminados
- GET /api/reports/solvency excluye eliminados

NOTA sobre el patrón de patch: la request se ejecuta DENTRO de los patches de los
call-sites (middleware.auth_middleware, routes.clients, routes.reports) para que cada
test use SU mock. El patrón de test_dashboard.py (request fuera del patch) es
order-dependent por bindings de módulo y es parte del baseline roto pre-existente.
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
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


def _request(mock, method, url, json_body=None, headers=None):
    """Ejecuta una request con los patches de call-site activos (determinista)."""
    with patch('services.firebase_service.FirebaseService', return_value=mock), \
         patch('middleware.auth_middleware.FirebaseService', return_value=mock), \
         patch('routes.clients.FirebaseService', return_value=mock), \
         patch('routes.reports.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()
        return client.open(
            url,
            method=method,
            json=json_body,
            headers=headers or {'Authorization': 'Bearer test-token'}
        )


def make_client(client_id, name='Juan', is_deleted=False, branch_id='branch-1',
                business_id='biz-1', is_active=True, membership_end=None):
    """Factory para datos de cliente de muestra"""
    from datetime import datetime, timedelta
    client = {
        'id': client_id,
        'name': name,
        'isActive': is_active,
        'membershipEnd': membership_end or (datetime.now() + timedelta(days=30)).isoformat(),
        'businessId': business_id,
        'branchId': branch_id,
    }
    if is_deleted is not None:
        client['isDeleted'] = is_deleted
    return client


class TestListExcludesDeleted:
    def test_list_excludes_deleted_and_keeps_total_correct(self, auth_header):
        clients = [make_client(f'c{i}') for i in range(1, 11)]
        clients[0]['isDeleted'] = True
        clients[1]['isDeleted'] = True

        mock = create_mock_service()
        mock.query_firestore.return_value = clients

        response = _request(mock, 'GET', '/api/clients', headers=auth_header)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        ids = [c['id'] for c in data['data']]
        assert len(ids) == 8
        assert 'c1' not in ids and 'c2' not in ids
        assert data['meta']['total'] == 8

    def test_list_keeps_legacy_client_without_field(self, auth_header):
        legacy = make_client('c-legacy')
        legacy.pop('isDeleted', None)  # campo ausente -> activo

        mock = create_mock_service()
        mock.query_firestore.return_value = [legacy]

        response = _request(mock, 'GET', '/api/clients', headers=auth_header)

        data = json.loads(response.data)
        assert [c['id'] for c in data['data']] == ['c-legacy']
        assert data['meta']['total'] == 1


class TestDetailDeleted:
    def test_detail_returns_404_for_deleted(self, auth_header):
        mock = create_mock_service()
        mock.get_document.return_value = make_client('c1', is_deleted=True)

        response = _request(mock, 'GET', '/api/clients/c1', headers=auth_header)

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False

    def test_detail_returns_200_for_legacy_without_field(self, auth_header):
        client = make_client('c1')
        client.pop('isDeleted', None)

        mock = create_mock_service()
        mock.get_document.return_value = client

        response = _request(mock, 'GET', '/api/clients/c1', headers=auth_header)

        assert response.status_code == 200
        assert json.loads(response.data)['success'] is True


class TestDeleteEndpoint:
    def test_delete_404_when_missing(self, auth_header):
        mock = create_mock_service()
        mock.get_document.return_value = None

        response = _request(mock, 'DELETE', '/api/clients/nonexistent', headers=auth_header)

        assert response.status_code == 404
        assert json.loads(response.data)['success'] is False
        mock.update_document.assert_not_called()

    def test_delete_404_when_already_deleted(self, auth_header):
        mock = create_mock_service()
        mock.get_document.return_value = make_client('c1', is_deleted=True)

        response = _request(mock, 'DELETE', '/api/clients/c1', headers=auth_header)

        assert response.status_code == 404
        mock.update_document.assert_not_called()

    def test_delete_403_cross_branch_branch_admin(self, auth_header):
        mock = create_mock_service(role='branch_admin')
        mock.get_document.return_value = make_client('c1', branch_id='branch-2')

        response = _request(mock, 'DELETE', '/api/clients/c1', headers=auth_header)

        assert response.status_code == 403
        assert json.loads(response.data)['success'] is False
        mock.update_document.assert_not_called()

    def test_delete_success_writes_audit_fields(self, auth_header):
        mock = create_mock_service(role='super_admin')
        mock.get_document.return_value = make_client('c1')
        mock.update_document.return_value = True

        response = _request(mock, 'DELETE', '/api/clients/c1', headers=auth_header)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['id'] == 'c1'

        # Soft delete con auditoría: isDeleted + deletedBy + deletedAt
        mock.update_document.assert_called_once()
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'clients'
        assert doc_id == 'c1'
        assert update['isDeleted'] is True
        assert update['deletedBy'] == 'admin-123'
        assert update['deletedAt']

    def test_delete_success_admin_without_branch_cross_branch(self, auth_header):
        """Admin sin branchId puede eliminar clientes de cualquier sede de su negocio"""
        mock = create_mock_service(role='admin')
        # create_mock_service asigna branch-1 a admin; forzar branchId None
        mock.get_user_by_uid.return_value['branchId'] = None
        mock.get_document.return_value = make_client('c1', branch_id='branch-2')
        mock.update_document.return_value = True

        response = _request(mock, 'DELETE', '/api/clients/c1', headers=auth_header)

        assert response.status_code == 200
        assert json.loads(response.data)['success'] is True

    def test_delete_never_touches_payments(self, auth_header):
        """El soft delete del cliente NO modifica la colección payments"""
        mock = create_mock_service(role='super_admin')
        mock.get_document.return_value = make_client('c1')
        mock.update_document.return_value = True

        _request(mock, 'DELETE', '/api/clients/c1', headers=auth_header)

        # Única llamada a update_document y es sobre 'clients'
        assert mock.update_document.call_count == 1
        assert mock.update_document.call_args[0][0] == 'clients'


class TestUpdateDeleted:
    def test_put_returns_404_for_deleted(self, auth_header):
        mock = create_mock_service()
        mock.get_document.return_value = make_client('c1', is_deleted=True)

        response = _request(mock, 'PUT', '/api/clients/c1', json_body={'name': 'Nuevo'}, headers=auth_header)

        assert response.status_code == 404
        assert json.loads(response.data)['success'] is False
        mock.update_document.assert_not_called()


class TestSolvencyExcludesDeleted:
    def test_solvency_excludes_deleted_clients(self, auth_header):
        deleted = make_client('c-del', is_deleted=True)
        active = make_client('c-ok')

        mock = create_mock_service()
        # 1ra llamada: query de clientes; 2da: query de pagos del cliente sobreviviente
        mock.query_firestore.side_effect = [
            [deleted, active],
            [],
        ]

        response = _request(mock, 'GET', '/api/reports/solvency', headers=auth_header)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        ids = [c['id'] for c in data['data']]
        assert ids == ['c-ok']
        assert data['meta']['total'] == 1