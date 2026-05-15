"""
Tests para las rutas de Users

Patrón: reset singleton → create fresh app → run test

El problema de estado se resuelve con:
1. setup_module (autouse, scope='module') resetea singleton ANTES del archivo
2. Cada test crea su propio app+client fresco
3. No hay estado filtrado porque cada test tiene su propia app
"""
import pytest
import json
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ============================================================================
# FACTORY - Crea mocks frescos
# ============================================================================

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


# ============================================================================
# FIXTURES - Reset singleton antes de cada archivo
# ============================================================================

@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    """Resetea singleton antes de cada archivo de test"""
    from services import firebase_service
    firebase_service.FirebaseService._reset()
    yield
    firebase_service.FirebaseService._reset()


@pytest.fixture
def client(reset_singleton):
    """Crea app + client fresco para cada test"""
    mock = create_mock_service()

    with patch('services.firebase_service.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app.test_client()


@pytest.fixture
def auth_header():
    return {'Authorization': 'Bearer test-token'}


# ============================================================================
# TESTS
# ============================================================================

class TestGetUsers:
    """Tests para GET /api/users"""

    def test_get_users_as_super_admin(self, client, auth_header):
        """GET /api/users como super_admin retorna lista"""
        mock = create_mock_service(role='super_admin')
        mock.query_firestore.return_value = [
            {'id': 'user-1', 'name': 'Juan', 'email': 'juan@test.com', 'role': 'cashier'},
            {'id': 'user-2', 'name': 'María', 'email': 'maria@test.com', 'role': 'trainer'}
        ]

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/users', headers=auth_header)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['data']) == 2

    def test_get_users_as_cashier_denied(self, client, auth_header):
        """GET /api/users como cashier retorna 403"""
        mock = create_mock_service(role='cashier')

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/users', headers=auth_header)

            assert response.status_code == 403

    def test_get_users_requires_auth(self, client):
        """GET /api/users sin auth retorna 401"""
        response = client.get('/api/users')
        assert response.status_code == 401

    def test_get_users_with_active_filter(self, client, auth_header):
        """GET /api/users?isActive=true filtra activos"""
        mock = create_mock_service()
        mock.query_firestore.return_value = []

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/users?isActive=true', headers=auth_header)

            assert response.status_code == 200
            mock.query_firestore.assert_called()
            call_kwargs = mock.query_firestore.call_args.kwargs
            filters = call_kwargs.get('filters', [])
            assert any(f['field'] == 'isActive' and f['value'] is True for f in filters)


class TestGetUserById:
    """Tests para GET /api/users/<user_id>"""

    def test_get_user_returns_user(self, client, auth_header):
        """GET /api/users/<id> retorna usuario"""
        mock = create_mock_service()
        mock.get_document.return_value = {
            'id': 'user-1', 'name': 'Juan', 'email': 'juan@test.com', 'role': 'cashier'
        }

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/users/user-1', headers=auth_header)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['name'] == 'Juan'

    def test_get_user_not_found(self, client, auth_header):
        """GET /api/users/<id> retorna 404 si no existe"""
        mock = create_mock_service()
        mock.get_document.return_value = None

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/users/nonexistent', headers=auth_header)

            assert response.status_code == 404


class TestCreateUser:
    """Tests para POST /api/users"""

    def test_create_user_success(self, client, auth_header):
        """POST /api/users crea usuario exitosamente"""
        mock = create_mock_service()
        mock.create_document.return_value = {
            'email': 'new@test.com',
            'name': 'Nuevo Usuario',
            'role': 'cashier',
            'businessId': 'biz-1',
            'id': 'new-user-id',
            'isActive': True,
            'permissions': ['read_clients', 'write_payments']
        }

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.post(
                '/api/users',
                data=json.dumps({
                    'email': 'new@test.com',
                    'name': 'Nuevo Usuario',
                    'role': 'cashier',
                    'businessId': 'biz-1'
                }),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['email'] == 'new@test.com'

    def test_create_user_missing_fields(self, client, auth_header):
        """POST /api/users con campos faltantes retorna 400"""
        mock = create_mock_service()

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.post(
                '/api/users',
                data=json.dumps({'email': 'test@test.com'}),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False

    def test_create_user_invalid_role(self, client, auth_header):
        """POST /api/users con rol inválido retorna 400"""
        mock = create_mock_service()

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.post(
                '/api/users',
                data=json.dumps({'email': 'test@test.com', 'name': 'Test', 'role': 'invalid_role'}),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 400


class TestUpdateUser:
    """Tests para PUT /api/users/<user_id>"""

    def test_update_user_success(self, client, auth_header):
        """PUT /api/users/<id> actualiza usuario exitosamente"""
        mock = create_mock_service()
        mock.get_document.return_value = {'id': 'user-1'}
        mock.update_document.return_value = {
            'id': 'user-1', 'name': 'Juan Actualizado', 'role': 'branch_admin'
        }

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.put(
                '/api/users/user-1',
                data=json.dumps({'name': 'Juan Actualizado', 'role': 'branch_admin'}),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['name'] == 'Juan Actualizado'

    def test_update_user_not_found(self, client, auth_header):
        """PUT /api/users/<id> retorna 404 si no existe"""
        mock = create_mock_service()
        mock.get_document.return_value = None

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.put(
                '/api/users/nonexistent',
                data=json.dumps({'name': 'Test'}),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 404


class TestDeleteUser:
    """Tests para DELETE /api/users/<user_id>"""

    def test_delete_user_success(self, client, auth_header):
        """DELETE /api/users/<id> desactiva usuario exitosamente"""
        mock = create_mock_service()
        mock.get_document.return_value = {'id': 'user-1', 'name': 'Test'}
        mock.update_document.return_value = True

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.delete('/api/users/user-1', headers=auth_header)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    def test_delete_user_not_found(self, client, auth_header):
        """DELETE /api/users/<id> retorna 404 si no existe"""
        mock = create_mock_service()
        mock.get_document.return_value = None

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.delete('/api/users/nonexistent', headers=auth_header)

            assert response.status_code == 404