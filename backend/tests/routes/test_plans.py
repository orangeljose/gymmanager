"""
Tests para las rutas de Plans

Patrón: reset singleton → create fresh app per test → run test

Mismo patrón que test_users.py:
- reset_singleton (autouse, scope='module') resetea singleton antes del archivo
- client fixture crea app fresca para cada test
- Cada test tiene su propio contexto aislado
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

class TestGetPlans:
    """Tests para GET /api/plans"""

    def test_get_plans_returns_empty_list(self, client, auth_header):
        """GET /api/plans sin planes retorna lista vacía"""
        mock = create_mock_service()
        mock.query_firestore.return_value = []

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/plans', headers=auth_header)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data'] == []

    def test_get_plans_returns_plans_list(self, client, auth_header):
        """GET /api/plans retorna lista de planes"""
        mock = create_mock_service()
        mock.query_firestore.return_value = [
            {'id': 'plan-1', 'name': 'Mensual', 'price': 35000, 'durationDays': 30, 'businessId': 'biz-1'},
            {'id': 'plan-2', 'name': 'Trimestral', 'price': 90000, 'durationDays': 90, 'businessId': 'biz-1'}
        ]

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/plans', headers=auth_header)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['data']) == 2

    def test_get_plans_requires_auth(self, client):
        """GET /api/plans sin auth retorna 401"""
        response = client.get('/api/plans')
        assert response.status_code == 401

    def test_get_plans_with_active_filter(self, client, auth_header):
        """GET /api/plans?isActive=true filtra solo activos"""
        mock = create_mock_service()
        mock.query_firestore.return_value = []

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/plans?isActive=true', headers=auth_header)

            assert response.status_code == 200
            mock.query_firestore.assert_called()
            call_kwargs = mock.query_firestore.call_args.kwargs
            filters = call_kwargs.get('filters', [])
            assert any(f['field'] == 'isActive' and f['value'] is True for f in filters)


class TestGetPlanById:
    """Tests para GET /api/plans/<plan_id>"""

    def test_get_plan_returns_plan(self, client, auth_header):
        """GET /api/plans/<id> retorna plan existente"""
        mock = create_mock_service()
        mock.get_document.return_value = {
            'id': 'plan-1', 'name': 'Mensual', 'price': 35000, 'businessId': 'biz-1'
        }

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/plans/plan-1', headers=auth_header)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['name'] == 'Mensual'

    def test_get_plan_returns_404_when_not_found(self, client, auth_header):
        """GET /api/plans/<id> retorna 404 si no existe"""
        mock = create_mock_service()
        mock.get_document.return_value = None

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.get('/api/plans/nonexistent', headers=auth_header)

            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False


class TestCreatePlan:
    """Tests para POST /api/plans"""

    def test_create_plan_success(self, client, auth_header):
        """POST /api/plans crea plan exitosamente"""
        mock = create_mock_service()
        mock.create_document.return_value = {
            'name': 'Mensual',
            'price': 35000,
            'durationDays': 30,
            'businessId': 'biz-1',
            'id': 'new-plan-id',
            'isActive': True
        }

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.post(
                '/api/plans',
                data=json.dumps({
                    'name': 'Mensual',
                    'price': 35000,
                    'durationDays': 30,
                    'businessId': 'biz-1'
                }),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['name'] == 'Mensual'

    def test_create_plan_requires_auth(self, client):
        """POST /api/plans sin auth retorna 401"""
        response = client.post(
            '/api/plans',
            data=json.dumps({'name': 'Test'}),
            content_type='application/json'
        )
        assert response.status_code == 401

    def test_create_plan_missing_fields(self, client, auth_header):
        """POST /api/plans con campos faltantes retorna 400"""
        mock = create_mock_service()

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.post(
                '/api/plans',
                data=json.dumps({'name': 'Mensual'}),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False


class TestUpdatePlan:
    """Tests para PUT /api/plans/<plan_id>"""

    def test_update_plan_success(self, client, auth_header):
        """PUT /api/plans/<id> actualiza plan exitosamente"""
        mock = create_mock_service()
        mock.get_document.return_value = {'id': 'plan-1', 'name': 'Mensual', 'businessId': 'biz-1'}
        mock.update_document.return_value = {
            'id': 'plan-1', 'name': 'Mensual Plus', 'price': 40000, 'businessId': 'biz-1'
        }

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.put(
                '/api/plans/plan-1',
                data=json.dumps({'name': 'Mensual Plus'}),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['name'] == 'Mensual Plus'

    def test_update_plan_not_found(self, client, auth_header):
        """PUT /api/plans/<id> retorna 404 si no existe"""
        mock = create_mock_service()
        mock.get_document.return_value = None

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.put(
                '/api/plans/nonexistent',
                data=json.dumps({'name': 'Test'}),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 404


class TestDeletePlan:
    """Tests para DELETE /api/plans/<plan_id>"""

    def test_delete_plan_success(self, client, auth_header):
        """DELETE /api/plans/<id> desactiva plan exitosamente"""
        mock = create_mock_service()
        mock.get_document.return_value = {'id': 'plan-1', 'name': 'Test', 'businessId': 'biz-1'}
        mock.update_document.return_value = True

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.delete('/api/plans/plan-1', headers=auth_header)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    def test_delete_plan_not_found(self, client, auth_header):
        """DELETE /api/plans/<id> retorna 404 si no existe"""
        mock = create_mock_service()
        mock.get_document.return_value = None

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            response = client.delete('/api/plans/nonexistent', headers=auth_header)

            assert response.status_code == 404