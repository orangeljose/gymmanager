"""
Tests para las rutas de Invitations

Patrón: reset singleton → create fresh app → run test (igual que test_users.py)

NOTA IMPORTANTE: los módulos (`routes/invitations.py`, `middleware/auth_middleware.py`)
enlazan `FirebaseService` en tiempo de import, por lo que parchear solo
`services.firebase_service.FirebaseService` NO llega a la ruta cuando otro archivo
de test importó `app` antes (binding fijo de la primera importación). La solución
es parchear los nombres tal como se usan EN TIEMPO DE LLAMADA:
`routes.invitations.FirebaseService` y `middleware.auth_middleware.FirebaseService`.
Con eso cada test usa su propio mock fresco sin importar el orden de ejecución.
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ============================================================================
# FACTORY - Crea mocks frescos
# ============================================================================

def _user_data(role='super_admin', uid='admin-123', business_id='biz-1'):
    """Datos de usuario autenticado según rol"""
    return {
        'uid': uid,
        'email': f'{role}@test.com',
        'name': f'{role.title()} Test',
        'role': role,
        'businessId': business_id,
        'branchId': None if role == 'super_admin' else 'branch-1',
        'permissions': ['*'] if role == 'super_admin' else ['read_clients', 'write_payments'],
        'isActive': True
    }


def create_mock_service(role='super_admin', uid='admin-123', business_id='biz-1'):
    """Factory para crear mocks de FirebaseService"""
    mock = MagicMock()
    mock.verify_token.return_value = {'uid': uid}
    mock.get_user_by_uid.return_value = _user_data(role, uid, business_id)
    mock.query_firestore.return_value = []
    mock.get_document.return_value = None
    mock.create_document.return_value = {'id': 'inv-1', 'isActive': True}
    mock.update_document.return_value = True
    mock.set_document.return_value = True
    return mock


def _pending_invitation(**overrides):
    """Invitation pendiente válida para tests de accept"""
    invitation = {
        'id': 'inv-1',
        'token': 'tok-123',
        'email': 'cashier@test.com',
        'name': 'Nombre Invitacion',
        'role': 'cashier',
        'businessId': 'biz-1',
        'branchId': 'branch-1',
        'invitedBy': 'admin-123',
        'status': 'pending',
        'expiresAt': (datetime.now() + timedelta(hours=72)).isoformat(),
        'createdAt': datetime.now().isoformat()
    }
    invitation.update(overrides)
    return invitation


# ============================================================================
# FIXTURES - Mock compartido + reset singleton
# ============================================================================

@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    """Resetea singleton antes de cada archivo de test"""
    from services import firebase_service
    firebase_service.FirebaseService._reset()
    yield
    firebase_service.FirebaseService._reset()


@pytest.fixture
def mock_service():
    """Mock fresco por test"""
    return create_mock_service()


@pytest.fixture
def client(mock_service, reset_singleton):
    """Crea app + client fresco para cada test con el mock parcheado en call-time.

    Debe ser yield-fixture: los patches tienen que seguir ACTIVOS durante el
    request (si se usara `return`, el with-block se cierra antes de ejecutar el
    test y la ruta cae en el binding de la primera importación del proceso).
    """
    with patch('services.firebase_service.FirebaseService', return_value=mock_service), \
         patch('middleware.auth_middleware.FirebaseService', return_value=mock_service), \
         patch('routes.invitations.FirebaseService', return_value=mock_service):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        yield app.test_client()


@pytest.fixture
def auth_header():
    return {'Authorization': 'Bearer test-token'}


# ============================================================================
# TESTS - POST /api/invitations (create)
# ============================================================================

class TestCreateInvitation:
    """Tests para POST /api/invitations"""

    def test_create_with_branch_id(self, client, mock_service, auth_header):
        """Spec: Admin invites cashier -> 201 con token, expiresAt e invitationLink"""
        with patch('routes.invitations.sendInvitationEmail', return_value={'success': True}):
            response = client.post(
                '/api/invitations',
                data=json.dumps({
                    'email': 'cashier@test.com',
                    'name': 'Cajero Nuevo',
                    'role': 'cashier',
                    'branchId': 'branch-1',
                    'businessId': 'biz-1'
                }),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['role'] == 'cashier'
            assert data['data']['token']
            assert data['data']['invitationLink'].endswith(f"?token={data['data']['token']}")
            assert data['data']['expiresAt']

            # La invitación guardada lleva branchId/businessId resueltos
            _, invitation_data = mock_service.create_document.call_args[0]
            assert invitation_data['branchId'] == 'branch-1'
            assert invitation_data['businessId'] == 'biz-1'
            assert invitation_data['status'] == 'pending'

    def test_create_missing_branch_for_branch_role(self, client, mock_service, auth_header):
        """Spec: Missing branch for employee -> 400 (super_admin sin branchId)"""
        response = client.post(
            '/api/invitations',
            data=json.dumps({
                'email': 'trainer@test.com',
                'role': 'trainer',
                'businessId': 'biz-1'
            }),
            content_type='application/json',
            headers=auth_header
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'branchId' in data['error']['message']
        mock_service.create_document.assert_not_called()

    def test_create_fallback_to_inviter_branch(self, client, mock_service, auth_header):
        """Spec: Fallback a la sucursal del invitador (admin invita cashier sin branchId)"""
        # Cambiar el usuario autenticado a admin (que sí tiene branchId propio)
        mock_service.get_user_by_uid.return_value = {
            'uid': 'admin-123',
            'email': 'admin@test.com',
            'name': 'Admin Test',
            'role': 'admin',
            'businessId': 'biz-1',
            'branchId': 'branch-1',
            'permissions': ['read_clients', 'write_payments'],
            'isActive': True
        }

        with patch('routes.invitations.sendInvitationEmail', return_value={'success': True}):
            response = client.post(
                '/api/invitations',
                data=json.dumps({
                    'email': 'cashier@test.com',
                    'role': 'cashier'
                }),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 201
            _, invitation_data = mock_service.create_document.call_args[0]
            assert invitation_data['branchId'] == 'branch-1'
            assert invitation_data['businessId'] == 'biz-1'

    def test_create_admin_keeps_business_scope(self, client, mock_service, auth_header):
        """Spec: Admin invite keeps business scope -> 201 sin branchId"""
        with patch('routes.invitations.sendInvitationEmail', return_value={'success': True}):
            response = client.post(
                '/api/invitations',
                data=json.dumps({
                    'email': 'admin2@test.com',
                    'role': 'admin',
                    'businessId': 'biz-1'
                }),
                content_type='application/json',
                headers=auth_header
            )

            assert response.status_code == 201
            _, invitation_data = mock_service.create_document.call_args[0]
            assert invitation_data['businessId'] == 'biz-1'
            assert invitation_data['branchId'] is None

    def test_create_duplicate_pending_invitation(self, client, mock_service, auth_header):
        """Spec: Duplicate pending invitation -> 400"""
        mock_service.query_firestore.return_value = [
            {'email': 'dup@test.com', 'status': 'pending'}
        ]

        response = client.post(
            '/api/invitations',
            data=json.dumps({
                'email': 'dup@test.com',
                'role': 'cashier',
                'branchId': 'branch-1',
                'businessId': 'biz-1'
            }),
            content_type='application/json',
            headers=auth_header
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        mock_service.create_document.assert_not_called()

    def test_create_cashier_forbidden(self, client, mock_service, auth_header):
        """Spec: Unauthorized inviter -> 403 (cashier)"""
        mock_service.get_user_by_uid.return_value = {
            'uid': 'cashier-123',
            'email': 'cashier@test.com',
            'name': 'Cashier Test',
            'role': 'cashier',
            'businessId': 'biz-1',
            'branchId': 'branch-1',
            'permissions': ['read_clients', 'write_payments'],
            'isActive': True
        }

        response = client.post(
            '/api/invitations',
            data=json.dumps({
                'email': 'cashier2@test.com',
                'role': 'cashier',
                'branchId': 'branch-1',
                'businessId': 'biz-1'
            }),
            content_type='application/json',
            headers=auth_header
        )

        assert response.status_code == 403

    def test_create_admin_cannot_invite_admin(self, client, mock_service, auth_header):
        """admin no puede invitar admin -> 400 (matriz de roles)"""
        mock_service.get_user_by_uid.return_value = {
            'uid': 'admin-123',
            'email': 'admin@test.com',
            'name': 'Admin Test',
            'role': 'admin',
            'businessId': 'biz-1',
            'branchId': 'branch-1',
            'permissions': ['read_clients', 'write_payments'],
            'isActive': True
        }

        response = client.post(
            '/api/invitations',
            data=json.dumps({
                'email': 'admin2@test.com',
                'role': 'admin',
                'businessId': 'biz-1'
            }),
            content_type='application/json',
            headers=auth_header
        )

        assert response.status_code == 400


# ============================================================================
# TESTS - POST /api/invitations/accept
# ============================================================================

class TestAcceptInvitation:
    """Tests para POST /api/invitations/accept"""

    def test_accept_stores_entered_name(self, client, mock_service):
        """Spec: Accept stores entered name -> 201 y user doc con el nombre ingresado"""
        mock_service.query_firestore.return_value = [_pending_invitation()]

        response = client.post(
            '/api/invitations/accept',
            data=json.dumps({
                'token': 'tok-123',
                'uid': 'user-abc',
                'name': 'Cajero Ingresado'
            }),
            content_type='application/json'
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['name'] == 'Cajero Ingresado'
        assert data['data']['role'] == 'cashier'

        user_data = mock_service.set_document.call_args[0][2]
        assert user_data['name'] == 'Cajero Ingresado'
        assert user_data['branchId'] == 'branch-1'
        assert user_data['businessId'] == 'biz-1'

    def test_accept_fallback_to_invitation_name(self, client, mock_service):
        """Spec: Accept without name -> fallback al nombre de la invitación"""
        mock_service.query_firestore.return_value = [_pending_invitation()]

        response = client.post(
            '/api/invitations/accept',
            data=json.dumps({
                'token': 'tok-123',
                'uid': 'user-abc'
            }),
            content_type='application/json'
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['data']['name'] == 'Nombre Invitacion'

        user_data = mock_service.set_document.call_args[0][2]
        assert user_data['name'] == 'Nombre Invitacion'

    def test_accept_without_name_or_invitation_name_falls_back_to_empty(self, client, mock_service):
        """Accept sin nombre y sin nombre en la invitación -> '' en el user doc"""
        mock_service.query_firestore.return_value = [_pending_invitation(name=None)]

        response = client.post(
            '/api/invitations/accept',
            data=json.dumps({
                'token': 'tok-123',
                'uid': 'user-abc'
            }),
            content_type='application/json'
        )

        assert response.status_code == 201
        user_data = mock_service.set_document.call_args[0][2]
        assert user_data['name'] == ''

    def test_accept_reused_token_returns_404(self, client, mock_service):
        """Spec: Reusing an accepted token -> 404 sin crear duplicado"""
        mock_service.query_firestore.return_value = []  # invitación ya no está pending

        response = client.post(
            '/api/invitations/accept',
            data=json.dumps({
                'token': 'tok-usado',
                'uid': 'user-abc'
            }),
            content_type='application/json'
        )

        assert response.status_code == 404
        mock_service.set_document.assert_not_called()

    def test_accept_requires_token_and_uid(self, client):
        """Accept sin token o uid -> 400"""
        response = client.post(
            '/api/invitations/accept',
            data=json.dumps({'uid': 'user-abc'}),
            content_type='application/json'
        )
        assert response.status_code == 400