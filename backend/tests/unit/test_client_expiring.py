"""
Tests del filtro expiringSoon en GET /api/clients.

Cubre (patrón test_reports_income.py: mock de FirebaseService + Flask test client,
request ejecutada DENTRO de los patches de los call-sites):
- Ambos bounds membershipEnd >= now y <= now+7d empujados a Firestore (tz-aware UTC)
- Precedencia de expiringSoon sobre status (status ignorado, sin 400)
- Valores inválidos de expiringSoon → 400
- status='suspended' → 400
- Alcance por sede (branch_admin) combinado con los bounds
- isDeleted excluido en Python + legacy sin campo incluido
- Paginación: meta.total correcto con expiringSoon activo
"""
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from services.firebase_service import FirebaseService


@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    FirebaseService._reset()
    yield
    FirebaseService._reset()


def create_mock_service(role='super_admin', uid='admin-123', business_id='biz-1'):
    """Factory para mocks de FirebaseService (mismo patrón que test_reports_income)."""
    user_data = {
        'uid': uid,
        'email': f'{role}@test.com',
        'name': f'{role.title()} Test',
        'role': role,
        'businessId': business_id,
        'branchId': None if role == 'super_admin' else 'branch-1',
        'permissions': ['*'] if role == 'super_admin' else ['read_clients', 'write_payments'],
        'isActive': True,
    }

    mock = MagicMock()
    mock.verify_token.return_value = {'uid': uid}
    mock.get_user_by_uid.return_value = user_data
    mock.query_firestore.return_value = []
    mock.get_document.return_value = None
    mock.create_document.return_value = {'id': 'new-doc-id', 'isActive': True}
    mock.update_document.return_value = True
    return mock


def _clients_with(mock, url):
    """Request DETERMINISTA: se ejecuta DENTRO de los patches de los call-sites."""
    with patch('services.firebase_service.FirebaseService', return_value=mock), \
         patch('middleware.auth_middleware.FirebaseService', return_value=mock), \
         patch('routes.clients.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()
        return client.get(url, headers={'Authorization': 'Bearer test-token'})


def _clients_call_filters(mock):
    """Devuelve los filters del call a query_firestore sobre 'clients'."""
    for call in mock.query_firestore.call_args_list:
        if call.args[0] == 'clients':
            return call.kwargs.get('filters') or []
    return None


def make_client(cid, membership_end=None, branch_id='branch-1', business_id='biz-1',
                is_deleted=None):
    client = {
        'id': cid,
        'name': f'Client {cid}',
        'phone': f'+{cid}',
        'membershipEnd': membership_end,
        'isActive': True,
        'branchId': branch_id,
        'businessId': business_id,
    }
    if is_deleted is not None:
        client['isDeleted'] = is_deleted
    return client


def _assert_bounds(filters, before, after):
    """Ambos bounds presentes: >= now y <= now+7d, tz-aware, dentro de [before, after]."""
    lower = next(f for f in filters if f['field'] == 'membershipEnd' and f['operator'] == '>=')
    upper = next(f for f in filters if f['field'] == 'membershipEnd' and f['operator'] == '<=')
    assert before <= lower['value'] <= after
    assert before + timedelta(days=7) <= upper['value'] <= after + timedelta(days=7)
    assert lower['value'].tzinfo is not None and upper['value'].tzinfo is not None


class TestExpiringSoonBounds:
    """expiringSoon=true empuja la ventana [now, now+7d] a Firestore."""

    def test_pushes_inclusive_bounds_to_firestore(self):
        """Operadores >= y <= (inclusivos) con now y now+7d tz-aware UTC."""
        mock = create_mock_service(role='super_admin', business_id='biz-1')
        mock.query_firestore.return_value = []

        before = datetime.now(timezone.utc)
        response = _clients_with(mock, '/api/clients?expiringSoon=true')
        after = datetime.now(timezone.utc)

        assert response.status_code == 200
        filters = _clients_call_filters(mock)
        assert filters is not None
        _assert_bounds(filters, before, after)

    def test_returns_only_clients_matching_firestore_range(self):
        """El response solo contiene lo que Firestore devolvió tras aplicar el rango
        (past/3 días/30 días → solo el de 3 días; el rango lo aplica Firestore)."""
        in_three_days = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        mock = create_mock_service(role='super_admin', business_id='biz-1')
        mock.query_firestore.return_value = [make_client('c-in3', in_three_days)]

        response = _clients_with(mock, '/api/clients?expiringSoon=true')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert [c['id'] for c in data['data']] == ['c-in3']
        assert data['meta']['total'] == 1


class TestExpiringSoonPrecedence:
    """expiringSoon=true ignora status (sin 400)."""

    def test_status_ignored_when_expiring_soon_true(self):
        mock = create_mock_service(role='super_admin', business_id='biz-1')
        mock.query_firestore.return_value = []

        before = datetime.now(timezone.utc)
        response = _clients_with(mock, '/api/clients?expiringSoon=true&status=active')
        after = datetime.now(timezone.utc)

        assert response.status_code == 200
        filters = _clients_call_filters(mock)
        assert all(f['field'] != 'status' for f in filters)
        _assert_bounds(filters, before, after)


class TestExpiringSoonRejectedValues:
    """Valores inválidos → 400."""

    def test_invalid_expiring_soon_value_returns_400(self):
        mock = create_mock_service(role='super_admin', business_id='biz-1')

        response = _clients_with(mock, '/api/clients?expiringSoon=yes')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == 400

    def test_suspended_status_returns_400(self):
        mock = create_mock_service(role='super_admin', business_id='biz-1')

        response = _clients_with(mock, '/api/clients?status=suspended')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == 400


class TestExpiringSoonScope:
    """Alcance por negocio/sede se combina con los bounds (índices compuestos)."""

    def test_branch_admin_sends_branch_and_business_equality(self):
        mock = create_mock_service(role='branch_admin', business_id='biz-1')
        mock.query_firestore.return_value = []

        before = datetime.now(timezone.utc)
        response = _clients_with(mock, '/api/clients?expiringSoon=true')
        after = datetime.now(timezone.utc)

        assert response.status_code == 200
        filters = _clients_call_filters(mock)
        assert {'field': 'businessId', 'operator': '==', 'value': 'biz-1'} in filters
        assert {'field': 'branchId', 'operator': '==', 'value': 'branch-1'} in filters
        _assert_bounds(filters, before, after)


class TestExpiringSoonDeletedExclusion:
    """isDeleted se excluye en Python; legacy sin campo se incluye."""

    def test_excludes_deleted_and_keeps_legacy(self):
        deleted = make_client('c-del', is_deleted=True)
        legacy = make_client('c-legacy')  # sin campo isDeleted
        legacy.pop('isDeleted', None)
        active = make_client('c-ok')

        mock = create_mock_service(role='super_admin', business_id='biz-1')
        mock.query_firestore.return_value = [deleted, legacy, active]

        response = _clients_with(mock, '/api/clients?expiringSoon=true')

        assert response.status_code == 200
        data = json.loads(response.data)
        ids = [c['id'] for c in data['data']]
        assert ids == ['c-legacy', 'c-ok']
        assert data['meta']['total'] == 2


class TestExpiringSoonPagination:
    """meta.total correcto con expiringSoon activo."""

    def test_page_2_limit_10_total_25(self):
        mock = create_mock_service(role='super_admin', business_id='biz-1')
        end = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        mock.query_firestore.return_value = [make_client(f'c{i}', end) for i in range(1, 26)]

        response = _clients_with(mock, '/api/clients?expiringSoon=true&page=2&limit=10')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['meta']['total'] == 25
        assert len(data['data']) == 10
        assert data['meta']['pages'] == 3
        assert data['meta']['page'] == 2