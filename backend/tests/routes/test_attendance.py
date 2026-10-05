"""
Tests para las rutas de Attendance (/api/attendance)

Patrón de mock (corrige el binding de `test_plans.py`): las rutas importan
`FirebaseService` a nivel de módulo, por lo que se parchea el símbolo en
`routes.attendance` y en `middleware.auth_middleware` (además del módulo
`services.firebase_service` que usa `app.py` al inicializar).

Cubre: POST (idempotencia, id determinístico, validación, scope), GET list
(paginación/summary), GET stats (agrupación rolling 7/30), historial de cliente
y permisos por rol.
"""
import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from zoneinfo import ZoneInfo  # noqa: E402


# ============================================================================
# FACTORY
# ============================================================================

def create_mock_service(role='cashier', uid='user-123', business_id='biz-1', branch_id='branch-1'):
    """Crea un FirebaseService mockeado con un usuario del rol indicado."""
    user_data = {
        'uid': uid,
        'email': f'{role}@test.com',
        'name': f'{role.title()} Test',
        'role': role,
        'businessId': business_id,
        'branchId': None if role == 'super_admin' else branch_id,
        'permissions': ['*'] if role == 'super_admin' else [],
        'isActive': True,
    }

    mock = MagicMock()
    mock.verify_token.return_value = {'uid': uid}
    mock.get_user_by_uid.return_value = user_data
    mock.query_firestore.return_value = []
    mock.get_document.return_value = None
    mock.set_document.return_value = True
    mock.create_document.return_value = {'id': 'new-doc-id'}
    mock.update_document.return_value = True
    return mock


def business_today():
    return datetime.now(ZoneInfo('America/Caracas')).strftime('%Y-%m-%d')


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    from services import firebase_service
    firebase_service.FirebaseService._reset()
    yield
    firebase_service.FirebaseService._reset()


@pytest.fixture(scope='module', autouse=True)
def prime_app_modules():
    """
    CRITICAL-01 (aislamiento entre archivos): el PRIMER import de `app` del
    proceso fija el binding de `FirebaseService` en middleware/rutas para TODOS
    los archivos que no parchean su call-site (p. ej. test_payment_delete). Este
    archivo corre primero (alfabéticamente), así que se primea con un mock
    super_admin bien configurado —equivalente al primer importer del baseline
    (test_client_delete)— en vez de dejar el mock de rol específico del primer
    test (cashier), que hacía fallar require_role en los archivos siguientes.

    Cada request de este archivo igual parchea sus call-sites (services + routes
    + middleware) con SU propio mock dentro de `make_client`.
    """
    with patch('services.firebase_service.FirebaseService',
               return_value=create_mock_service(role='super_admin')):
        from app import create_app
        create_app()
    yield


@pytest.fixture
def auth_header():
    return {'Authorization': 'Bearer test-token'}


@pytest.fixture
def make_client():
    """Devuelve un factory que arma el test_client con el mock dado."""
    contexts = []

    def _factory(mock):
        ctx1 = patch('services.firebase_service.FirebaseService', return_value=mock)
        ctx1.start()
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        ctx2 = patch('routes.attendance.FirebaseService', return_value=mock)
        ctx3 = patch('middleware.auth_middleware.FirebaseService', return_value=mock)
        ctx2.start()
        ctx3.start()
        contexts.append((ctx1, ctx2, ctx3))
        return app.test_client()

    yield _factory

    for ctx1, ctx2, ctx3 in contexts:
        ctx3.stop()
        ctx2.stop()
        ctx1.stop()


# ============================================================================
# POST /api/attendance
# ============================================================================

class TestRegisterAttendance:

    def test_create_new_checkin_returns_201(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1', branch_id='branch-1')
        client_doc = {'id': 'c1', 'name': 'Juan Pérez', 'businessId': 'biz-1', 'branchId': 'branch-1'}

        def get_doc(collection, doc_id):
            if collection == 'clients':
                return client_doc
            return None  # no existe aún el attendance

        mock.get_document.side_effect = get_doc
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1', 'method': 'manual'},
                               headers=auth_header)

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['alreadyCheckedIn'] is False
        assert data['data']['clientName'] == 'Juan Pérez'
        assert data['data']['method'] == 'manual'
        # Id determinístico {clientId}_{date} con la fecha en tz del negocio
        args = mock.set_document.call_args
        assert args[0][0] == 'attendance'
        assert args[0][1] == f"c1_{business_today()}"

        # W-02: el documento persistido debe contener TODOS los campos del modelo
        # (Requirement: Attendance Data Model).
        stored = args[0][2]
        assert set(stored.keys()) == {
            'id', 'clientId', 'clientName', 'businessId', 'branchId',
            'date', 'checkInAt', 'method', 'registeredBy', 'registeredByName',
            'createdAt',
        }
        assert stored['id'] == f"c1_{business_today()}"
        assert stored['clientId'] == 'c1'
        assert stored['clientName'] == 'Juan Pérez'
        assert stored['businessId'] == 'biz-1'
        assert stored['branchId'] == 'branch-1'
        assert stored['date'] == business_today()
        assert stored['method'] == 'manual'
        assert stored['checkInAt']
        assert stored['registeredBy'] == 'user-123'
        assert stored['registeredByName'] == 'Cashier Test'
        assert stored['createdAt']
        # checkInAt y createdAt se generan con el mismo instante ISO UTC
        assert stored['checkInAt'] == stored['createdAt']

        assert data['data']['date'] == business_today()

    def test_default_method_is_manual(self, make_client, auth_header):
        mock = create_mock_service()
        mock.get_document.side_effect = lambda c, i: (
            {'id': 'c1', 'name': 'Ana', 'businessId': 'biz-1', 'branchId': 'branch-1'}
            if c == 'clients' else None
        )
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1'}, headers=auth_header)

        assert response.status_code == 201
        assert response.get_json()['data']['method'] == 'manual'

    @pytest.mark.parametrize('method', ['qr', 'biometric'])
    def test_create_checkin_with_scanner_method_returns_201(self, make_client, auth_header, method):
        """
        CRITICAL-02 / Scanner Contract: un futuro lector QR/biométrico usa el
        mismo POST y el método se persiste tal cual.
        """
        mock = create_mock_service(role='cashier', business_id='biz-1', branch_id='branch-1')
        client_doc = {'id': 'c1', 'name': 'Juan Pérez', 'businessId': 'biz-1', 'branchId': 'branch-1'}
        mock.get_document.side_effect = lambda c, i: client_doc if c == 'clients' else None
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1', 'method': method},
                               headers=auth_header)

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['method'] == method
        _, doc_id, stored = mock.set_document.call_args[0]
        assert doc_id == f"c1_{business_today()}"
        assert stored['method'] == method

    @pytest.mark.parametrize('method', ['qr', 'biometric'])
    def test_repeat_same_day_scanner_method_returns_200_already_checked_in(
        self, make_client, auth_header, method
    ):
        """Un segundo escaneo QR/biométrico el mismo día NO duplica y preserva el método."""
        mock = create_mock_service()
        existing = {
            'id': f"c1_{business_today()}", 'clientId': 'c1', 'clientName': 'Juan',
            'businessId': 'biz-1', 'branchId': 'branch-1', 'date': business_today(),
            'checkInAt': '2026-10-05T10:00:00+00:00', 'method': method,
        }
        mock.get_document.side_effect = lambda c, i: (
            {'id': 'c1', 'name': 'Juan', 'businessId': 'biz-1', 'branchId': 'branch-1'}
            if c == 'clients' else existing
        )
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1', 'method': method},
                               headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['alreadyCheckedIn'] is True
        assert data['data']['method'] == method
        mock.set_document.assert_not_called()

    def test_repeat_same_day_returns_200_already_checked_in(self, make_client, auth_header):
        mock = create_mock_service()
        existing = {
            'id': f"c1_{business_today()}", 'clientId': 'c1', 'clientName': 'Juan',
            'businessId': 'biz-1', 'branchId': 'branch-1', 'date': business_today(),
            'checkInAt': '2026-10-05T10:00:00+00:00', 'method': 'manual',
        }
        mock.get_document.side_effect = lambda c, i: (
            {'id': 'c1', 'name': 'Juan', 'businessId': 'biz-1', 'branchId': 'branch-1'}
            if c == 'clients' else existing
        )
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1'}, headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['alreadyCheckedIn'] is True
        mock.set_document.assert_not_called()

    def test_invalid_method_returns_400(self, make_client, auth_header):
        mock = create_mock_service()
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1', 'method': 'nfc'},
                               headers=auth_header)

        assert response.status_code == 400
        assert response.get_json()['success'] is False
        mock.set_document.assert_not_called()

    def test_missing_client_id_returns_400(self, make_client, auth_header):
        mock = create_mock_service()
        client = make_client(mock)

        response = client.post('/api/attendance', json={'method': 'manual'}, headers=auth_header)

        assert response.status_code == 400

    def test_client_not_found_returns_404(self, make_client, auth_header):
        mock = create_mock_service()
        mock.get_document.return_value = None
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'ghost'}, headers=auth_header)

        assert response.status_code == 404
        mock.set_document.assert_not_called()

    def test_deleted_client_returns_404(self, make_client, auth_header):
        mock = create_mock_service()
        mock.get_document.return_value = {'id': 'c1', 'name': 'X', 'isDeleted': True,
                                          'businessId': 'biz-1', 'branchId': 'branch-1'}
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1'}, headers=auth_header)

        assert response.status_code == 404

    def test_cross_business_returns_403(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-2')
        mock.get_document.return_value = {'id': 'c1', 'name': 'X', 'businessId': 'biz-1',
                                          'branchId': 'branch-1'}
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1'}, headers=auth_header)

        assert response.status_code == 403
        mock.set_document.assert_not_called()

    def test_branch_scoped_user_other_branch_returns_403(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-2')
        mock.get_document.return_value = {'id': 'c1', 'name': 'X', 'businessId': 'biz-1',
                                          'branchId': 'branch-1'}
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1'}, headers=auth_header)

        assert response.status_code == 403

    def test_trainer_cannot_register_returns_403(self, make_client, auth_header):
        mock = create_mock_service(role='trainer')
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1'}, headers=auth_header)

        assert response.status_code == 403

    def test_requires_auth(self, make_client):
        mock = create_mock_service()
        client = make_client(mock)

        response = client.post('/api/attendance', json={'clientId': 'c1'})

        assert response.status_code == 401


# ============================================================================
# GET /api/attendance
# ============================================================================

class TestListAttendance:

    def test_list_sorted_desc_and_summary(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = [
            {'id': 'a', 'clientId': 'c1', 'clientName': 'A', 'method': 'manual',
             'date': '2026-10-05', 'checkInAt': '2026-10-05T08:00:00+00:00'},
            {'id': 'b', 'clientId': 'c2', 'clientName': 'B', 'method': 'qr',
             'date': '2026-10-05', 'checkInAt': '2026-10-05T12:00:00+00:00'},
            {'id': 'c', 'clientId': 'c3', 'clientName': 'C', 'method': 'manual',
             'date': '2026-10-05', 'checkInAt': '2026-10-05T10:00:00+00:00'},
        ]
        client = make_client(mock)

        response = client.get('/api/attendance?date=2026-10-05', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()
        assert [r['id'] for r in data['data']] == ['b', 'c', 'a']
        assert data['meta']['total'] == 3
        assert data['summary']['total'] == 3
        assert data['summary']['byMethod'] == {'manual': 2, 'qr': 1}

    def test_list_pagination(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = [
            {'id': f'r{i}', 'clientId': f'c{i}', 'method': 'manual', 'date': '2026-10-05',
             'checkInAt': f'2026-10-05T0{i}:00:00+00:00'} for i in range(3)
        ]
        client = make_client(mock)

        response = client.get('/api/attendance?date=2026-10-05&page=1&limit=2', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 2
        assert data['meta'] == {'total': 3, 'page': 1, 'limit': 2, 'pages': 2}

    def test_non_numeric_page_and_limit_fall_back_to_defaults(self, make_client, auth_header):
        """W-04: page/limit no numéricos no deben romper (500) sino usar defaults."""
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = []
        client = make_client(mock)

        response = client.get('/api/attendance?page=abc&limit=xyz', headers=auth_header)

        assert response.status_code == 200
        meta = response.get_json()['meta']
        assert meta['page'] == 1
        assert meta['limit'] == 20

    def test_invalid_date_returns_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.get('/api/attendance?date=05-10-2026', headers=auth_header)

        assert response.status_code == 400

    def test_trainer_can_read(self, make_client, auth_header):
        mock = create_mock_service(role='trainer')
        client = make_client(mock)

        response = client.get('/api/attendance', headers=auth_header)

        assert response.status_code == 200


# ============================================================================
# GET /api/attendance/stats
# ============================================================================

class TestAttendanceStats:

    def test_stats_grouping_and_series(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin')
        rows = [
            {'clientId': 'c1', 'clientName': 'Uno', 'date': '2026-10-05'},
            {'clientId': 'c1', 'clientName': 'Uno', 'date': '2026-10-05'},
            {'clientId': 'c2', 'clientName': 'Dos', 'date': '2026-10-04'},
            {'clientId': 'c3', 'clientName': 'Tres', 'date': '2026-09-26'},
            {'clientId': 'c3', 'clientName': 'Tres', 'date': '2026-09-26'},
            {'clientId': 'c3', 'clientName': 'Tres', 'date': '2026-09-26'},
            {'clientId': 'c4', 'clientName': 'Viejo', 'date': '2026-08-26'},  # fuera de 30d
        ]
        mock.query_firestore.return_value = rows
        client = make_client(mock)

        response = client.get('/api/attendance/stats?date=2026-10-05', headers=auth_header)

        assert response.status_code == 200
        stats = response.get_json()['data']
        assert stats['today'] == 2
        assert stats['week'] == 3          # 10-05 (2) + 10-04 (1)
        assert stats['month'] == 6         # incluye 09-26 (3); excluye 08-26
        assert len(stats['series7']) == 7
        assert len(stats['series30']) == 30
        assert stats['series7'][-1] == {'date': '2026-10-05', 'count': 2}
        assert stats['series7'][-2] == {'date': '2026-10-04', 'count': 1}
        assert stats['topAttendees'][0] == {'clientId': 'c3', 'clientName': 'Tres', 'count': 3}
        # UNA sola query acotada
        mock.query_firestore.assert_called_once()

    def test_stats_single_query_even_with_top_attendees(self, make_client, auth_header):
        mock = create_mock_service(role='super_admin', business_id=None)
        mock.query_firestore.return_value = []
        client = make_client(mock)

        response = client.get('/api/attendance/stats', headers=auth_header)

        assert response.status_code == 200
        stats = response.get_json()['data']
        assert stats['today'] == 0
        assert stats['topAttendees'] == []
        mock.query_firestore.assert_called_once()


# ============================================================================
# GET /api/attendance/client/<id>
# ============================================================================

class TestClientAttendance:

    def test_client_history_and_stats(self, make_client, auth_header):
        mock = create_mock_service(role='trainer', business_id='biz-1', branch_id='branch-1')
        mock.get_document.return_value = {'id': 'c1', 'name': 'Juan', 'businessId': 'biz-1',
                                          'branchId': 'branch-1'}
        this_month = business_today()[:7]
        mock.query_firestore.return_value = [
            {'id': 'a1', 'clientId': 'c1', 'date': f'{this_month}-02', 'checkInAt': f'{this_month}-02T09:00:00+00:00'},
            {'id': 'a2', 'clientId': 'c1', 'date': '2026-01-15', 'checkInAt': '2026-01-15T09:00:00+00:00'},
        ]
        client = make_client(mock)

        response = client.get('/api/attendance/client/c1', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()
        assert data['stats']['total'] == 2
        assert data['stats']['thisMonth'] == 1
        assert data['stats']['lastVisit'].startswith(this_month)

    def test_client_not_found_returns_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = None
        client = make_client(mock)

        response = client.get('/api/attendance/client/ghost', headers=auth_header)

        assert response.status_code == 404

    def test_cross_business_client_returns_403(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-2')
        mock.get_document.return_value = {'id': 'c1', 'name': 'X', 'businessId': 'biz-1',
                                          'branchId': 'branch-1'}
        client = make_client(mock)

        response = client.get('/api/attendance/client/c1', headers=auth_header)

        assert response.status_code == 403
