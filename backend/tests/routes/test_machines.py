"""
Tests para las rutas de Máquinas/Mantenimiento (/api/machines)

Patrón de mock (idéntico a test_attendance.py): las rutas importan
`FirebaseService` a nivel de módulo, por lo que se parchea el símbolo en
`routes.machines` y en `middleware.auth_middleware`, además del módulo
`services.firebase_service` que usa `app.py` al inicializar. Cada request se
ejecuta DENTRO de los patches para que cada test use SU mock y no dependa del
orden de ejecución entre archivos.

Cubre: CRUD + roles/scope, soft-delete, list (filtros/paginación/legacy),
transiciones de estado (repair→status, preventive→+90d, in_progress→maintenance),
summary (byStatus, ventana 7d, recentRepairs≤5, una query por colección),
historial DESC/paginado y 404s.
"""
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ============================================================================
# FACTORY
# ============================================================================

def create_mock_service(role='admin', uid='user-123', business_id='biz-1', branch_id='branch-1'):
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


def _today():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _date_plus(days):
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


MACHINE = {
    'id': 'm1', 'name': 'Cinta de correr', 'brand': 'Life', 'model': 'X1',
    'category': 'cardio', 'businessId': 'biz-1', 'branchId': 'branch-1',
    'status': 'operational', 'isActive': True,
}

ITEM = {
    'id': 'i1', 'kind': 'item', 'name': 'Mancuerna 10kg', 'category': 'free_weights',
    'businessId': 'biz-1', 'branchId': 'branch-1', 'status': 'operational',
    'isActive': True, 'quantity': 8, 'weightKg': 10,
}


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
    los archivos que no parchean su call-site. Se primea con un mock super_admin
    bien configurado para no romper require_role en los archivos siguientes.
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
    """Factory que arma el test_client con el mock dado, parchando los call-sites."""
    contexts = []

    def _factory(mock):
        ctx1 = patch('services.firebase_service.FirebaseService', return_value=mock)
        ctx1.start()
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        ctx2 = patch('routes.machines.FirebaseService', return_value=mock)
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
# GET /api/machines  (list)
# ============================================================================

class TestListMachines:

    def _machines(self):
        return [
            {'id': 'm1', 'name': 'Cinta', 'category': 'cardio', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True},
            {'id': 'm2', 'name': 'Prensa', 'category': 'strength', 'status': 'maintenance',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True},
            # legacy sin isActive → se trata como activa
            {'id': 'm3', 'name': 'Remo', 'category': 'cardio', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1'},
            # soft-deleted → excluida
            {'id': 'm4', 'name': 'Borrada', 'category': 'cardio', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': False},
        ]

    def test_list_filters_and_meta(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.return_value = self._machines()
        client = make_client(mock)

        response = client.get('/api/machines?category=cardio&status=operational', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()
        ids = [m['id'] for m in data['data']]
        assert ids == ['m1', 'm3']  # m4 borrada, m2 otro status
        assert data['meta']['total'] == 2
        assert data['meta']['page'] == 1
        assert data['meta']['limit'] == 20
        assert data['meta']['pages'] == 1
        # Solo igualdad de businessId en Firestore (máximo 1 filtro)
        filters = mock.query_firestore.call_args[1]['filters']
        assert filters == [{'field': 'businessId', 'operator': '==', 'value': 'biz-1'}]

    def test_list_legacy_active_included_and_deleted_excluded(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = self._machines()
        client = make_client(mock)

        response = client.get('/api/machines', headers=auth_header)

        ids = [m['id'] for m in response.get_json()['data']]
        assert 'm3' in ids   # legacy sin isActive → incluida
        assert 'm4' not in ids  # isActive:false → excluida

    def test_list_pagination(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = [
            {'id': f'm{i}', 'name': f'M{i}', 'category': 'cardio', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True}
            for i in range(5)
        ]
        client = make_client(mock)

        response = client.get('/api/machines?page=2&limit=2', headers=auth_header)

        data = response.get_json()
        assert len(data['data']) == 2
        assert data['meta'] == {'total': 5, 'page': 2, 'limit': 2, 'pages': 3}

    def test_branch_scoped_user_filters_own_branch(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-1')
        mock.query_firestore.return_value = [
            {'id': 'a', 'name': 'A', 'category': 'cardio', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1'},
            {'id': 'b', 'name': 'B', 'category': 'cardio', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-2'},
        ]
        client = make_client(mock)

        response = client.get('/api/machines', headers=auth_header)

        ids = [m['id'] for m in response.get_json()['data']]
        assert ids == ['a']


# ============================================================================
# GET /api/machines/<id>
# ============================================================================

class TestGetMachine:

    def test_get_detail_200(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(MACHINE)
        client = make_client(mock)

        response = client.get('/api/machines/m1', headers=auth_header)

        assert response.status_code == 200
        assert response.get_json()['data']['id'] == 'm1'

    def test_get_missing_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = None
        client = make_client(mock)

        assert client.get('/api/machines/ghost', headers=auth_header).status_code == 404

    def test_get_deleted_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        deleted = dict(MACHINE)
        deleted['isActive'] = False
        mock.get_document.return_value = deleted
        client = make_client(mock)

        assert client.get('/api/machines/m1', headers=auth_header).status_code == 404

    def test_get_cross_business_403(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-2')
        mock.get_document.return_value = dict(MACHINE)  # biz-1
        client = make_client(mock)

        assert client.get('/api/machines/m1', headers=auth_header).status_code == 403


# ============================================================================
# POST /api/machines
# ============================================================================

class TestCreateMachine:

    def test_create_valid_201_with_defaults(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.create_document.return_value = {'id': 'new-1', 'name': 'Bici', 'isActive': True}
        client = make_client(mock)

        response = client.post('/api/machines',
                               json={'name': 'Bici', 'category': 'cardio', 'branchId': 'branch-1'},
                               headers=auth_header)

        assert response.status_code == 201
        assert response.get_json()['success'] is True
        collection, record = mock.create_document.call_args[0]
        assert collection == 'machines'
        assert record['status'] == 'operational'
        assert record['isActive'] is True
        assert record['businessId'] == 'biz-1'
        # Campos del modelo presentes (id lo inyecta create_document)
        assert {'name', 'brand', 'model', 'category', 'purchaseDate', 'warrantyUntil',
                'businessId', 'branchId', 'status', 'nextMaintenanceDate', 'isActive'} <= set(record)

    def test_create_empty_name_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post('/api/machines',
                               json={'name': '  ', 'category': 'cardio'}, headers=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_create_invalid_category_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post('/api/machines',
                               json={'name': 'X', 'category': 'cardio2'}, headers=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_create_cross_branch_403(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-1')
        client = make_client(mock)

        response = client.post('/api/machines',
                               json={'name': 'X', 'category': 'cardio', 'branchId': 'branch-2'},
                               headers=auth_header)

        assert response.status_code == 403
        mock.create_document.assert_not_called()

    def test_trainer_cannot_create_403(self, make_client, auth_header):
        mock = create_mock_service(role='trainer')
        client = make_client(mock)

        response = client.post('/api/machines',
                               json={'name': 'X', 'category': 'cardio'}, headers=auth_header)

        assert response.status_code == 403
        mock.create_document.assert_not_called()


# ============================================================================
# PUT / DELETE /api/machines/<id>
# ============================================================================

class TestUpdateAndDeleteMachine:

    def test_update_status_200(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(MACHINE)
        client = make_client(mock)

        response = client.put('/api/machines/m1', json={'status': 'maintenance'}, headers=auth_header)

        assert response.status_code == 200
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'machines'
        assert doc_id == 'm1'
        assert update['status'] == 'maintenance'

    def test_update_missing_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = None
        client = make_client(mock)

        response = client.put('/api/machines/ghost', json={'status': 'maintenance'}, headers=auth_header)

        assert response.status_code == 404
        mock.update_document.assert_not_called()

    def test_update_invalid_status_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(MACHINE)
        client = make_client(mock)

        response = client.put('/api/machines/m1', json={'status': 'broken'}, headers=auth_header)

        assert response.status_code == 400
        mock.update_document.assert_not_called()

    def test_soft_delete_preserves_document(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(MACHINE)
        client = make_client(mock)

        response = client.delete('/api/machines/m1', headers=auth_header)

        assert response.status_code == 200
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'machines'
        assert update['isActive'] is False
        assert update['deletedBy'] == 'user-123'
        assert update['deletedAt']
        # NO se elimina físicamente
        mock.delete_document.assert_not_called()

    def test_delete_missing_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = None
        client = make_client(mock)

        assert client.delete('/api/machines/ghost', headers=auth_header).status_code == 404


# ============================================================================
# Permisos
# ============================================================================

class TestPermissions:

    def test_cashier_can_read_200(self, make_client, auth_header):
        mock = create_mock_service(role='cashier')
        client = make_client(mock)

        assert client.get('/api/machines', headers=auth_header).status_code == 200

    def test_unauth_returns_401(self, make_client):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        assert client.get('/api/machines').status_code == 401

    def test_cashier_cannot_delete_403(self, make_client, auth_header):
        mock = create_mock_service(role='cashier')
        client = make_client(mock)

        assert client.delete('/api/machines/m1', headers=auth_header).status_code == 403


# ============================================================================
# POST /api/machines/<id>/maintenance (transiciones)
# ============================================================================

_UNSET = object()


class TestMaintenanceTransitions:

    def _post(self, make_client, mock, payload, machine=_UNSET, auth_header=None):
        mock.get_document.return_value = dict(MACHINE) if machine is _UNSET else machine
        mock.create_document.return_value = {'id': 'rec-1', **payload}
        client = make_client(mock)
        return client.post('/api/machines/m1/maintenance', json=payload, headers=auth_header)

    def _machine_update(self, mock):
        calls = [c for c in mock.update_document.call_args_list if c[0][0] == 'machines']
        assert len(calls) == 1
        return calls[0][0][2]

    def test_repair_completed_sets_resolved_status(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        payload = {'type': 'repair', 'status': 'completed', 'resolvedStatus': 'out_of_service',
                   'date': '2026-10-13', 'description': 'Motor'}

        response = self._post(make_client, mock, payload, machine=dict(MACHINE), auth_header=auth_header)

        assert response.status_code == 201
        assert self._machine_update(mock)['status'] == 'out_of_service'

    def test_repair_completed_without_resolved_status_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        payload = {'type': 'repair', 'status': 'completed', 'date': '2026-10-13'}

        response = self._post(make_client, mock, payload, auth_header=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()
        mock.update_document.assert_not_called()

    def test_preventive_completed_sets_plus_90_days(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        payload = {'type': 'preventive', 'status': 'completed', 'date': '2026-10-13'}
        machine = dict(MACHINE)
        machine['status'] = 'maintenance'

        response = self._post(make_client, mock, payload, machine=machine, auth_header=auth_header)

        assert response.status_code == 201
        update = self._machine_update(mock)
        assert update['nextMaintenanceDate'] == '2027-01-11'
        # estaba en maintenance → vuelve a operational
        assert update['status'] == 'operational'

    def test_preventive_does_not_resurrect_out_of_service(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        payload = {'type': 'preventive', 'status': 'completed', 'date': '2026-10-13'}
        machine = dict(MACHINE)
        machine['status'] = 'out_of_service'

        self._post(make_client, mock, payload, machine=machine, auth_header=auth_header)

        update = self._machine_update(mock)
        assert update['nextMaintenanceDate'] == '2027-01-11'
        assert 'status' not in update

    def test_preventive_explicit_override(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        payload = {'type': 'preventive', 'status': 'completed', 'date': '2026-10-13',
                   'nextMaintenanceDate': '2026-11-01'}

        self._post(make_client, mock, payload, auth_header=auth_header)

        assert self._machine_update(mock)['nextMaintenanceDate'] == '2026-11-01'

    @pytest.mark.parametrize('status', ['scheduled', 'in_progress'])
    def test_pending_maintenance_sets_machine_to_maintenance(self, make_client, auth_header, status):
        mock = create_mock_service(role='admin')
        payload = {'type': 'repair', 'status': status, 'date': '2026-10-13'}

        response = self._post(make_client, mock, payload, auth_header=auth_header)

        assert response.status_code == 201
        assert self._machine_update(mock)['status'] == 'maintenance'

    def test_record_contains_all_model_fields(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(MACHINE)
        payload = {'type': 'repair', 'status': 'completed', 'resolvedStatus': 'operational',
                   'date': '2026-10-13', 'description': 'Cambio de banda', 'costCents': 1500,
                   'technician': 'Técnico 1'}
        mock.create_document.return_value = {'id': 'rec-1'}
        client = make_client(mock)

        response = client.post('/api/machines/m1/maintenance', json=payload, headers=auth_header)

        assert response.status_code == 201
        collection, record = mock.create_document.call_args[0]
        assert collection == 'machine_maintenance'
        assert record['machineName'] == 'Cinta de correr'
        assert record['costCents'] == 1500
        assert record['registeredBy'] == 'user-123'
        assert {
            'machineId', 'machineName', 'type', 'description', 'date', 'costCents',
            'technician', 'status', 'resolvedStatus', 'businessId', 'branchId',
            'registeredBy', 'registeredByName', 'createdAt',
        } == set(record)

    def test_invalid_type_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        payload = {'type': 'inspection', 'date': '2026-10-13'}

        response = self._post(make_client, mock, payload, auth_header=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_unknown_machine_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        payload = {'type': 'preventive', 'date': '2026-10-13'}

        response = self._post(make_client, mock, payload, machine=None, auth_header=auth_header)

        assert response.status_code == 404
        mock.create_document.assert_not_called()

    def test_trainer_cannot_log_403(self, make_client, auth_header):
        mock = create_mock_service(role='trainer')
        payload = {'type': 'preventive', 'date': '2026-10-13'}

        response = self._post(make_client, mock, payload, auth_header=auth_header)

        assert response.status_code == 403
        mock.create_document.assert_not_called()


# ============================================================================
# GET /api/machines/<id>/maintenance (historial)
# ============================================================================

class TestMaintenanceHistory:

    def test_history_order_and_pagination(self, make_client, auth_header):
        mock = create_mock_service(role='trainer')  # trainer puede leer
        mock.get_document.return_value = dict(MACHINE)
        mock.query_firestore.return_value = [
            {'id': 'r1', 'machineId': 'm1', 'date': '2026-01-10', 'type': 'preventive'},
            {'id': 'r2', 'machineId': 'm1', 'date': '2026-09-20', 'type': 'repair'},
            {'id': 'r3', 'machineId': 'm1', 'date': '2026-05-01', 'type': 'preventive'},
        ]
        client = make_client(mock)

        response = client.get('/api/machines/m1/maintenance?page=1&limit=2', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()
        assert [r['id'] for r in data['data']] == ['r2', 'r3']  # DESC por date
        assert data['meta'] == {'total': 3, 'page': 1, 'limit': 2, 'pages': 2}

    def test_history_missing_machine_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = None
        client = make_client(mock)

        assert client.get('/api/machines/ghost/maintenance', headers=auth_header).status_code == 404

    def test_history_cross_business_403(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-2')
        mock.get_document.return_value = dict(MACHINE)  # biz-1
        client = make_client(mock)

        response = client.get('/api/machines/m1/maintenance', headers=auth_header)

        assert response.status_code == 403
        mock.query_firestore.assert_not_called()


# ============================================================================
# GET /api/machines/summary
# ============================================================================

class TestMachinesSummary:

    def test_summary_counts_window_and_recent(self, make_client, auth_header):
        mock = create_mock_service(role='admin')

        machines = [
            {'id': 'a', 'name': 'A', 'category': 'cardio', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True,
             'nextMaintenanceDate': _date_plus(3)},
            {'id': 'b', 'name': 'B', 'category': 'strength', 'status': 'maintenance',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True,
             'nextMaintenanceDate': _date_plus(10)},  # fuera de la ventana
            {'id': 'c', 'name': 'C', 'category': 'strength', 'status': 'out_of_service',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True},
            {'id': 'd', 'name': 'D', 'status': 'operational', 'businessId': 'biz-1',
             'branchId': 'branch-1', 'isActive': False},  # borrada
        ]
        recent = [
            {'id': f'r{i}', 'machineId': 'a', 'type': 'repair', 'date': f'2026-09-{10 + i:02d}',
             'businessId': 'biz-1', 'branchId': 'branch-1'}
            for i in range(6)
        ]

        def query(collection, **kwargs):
            if collection == 'machines':
                return machines
            if collection == 'machine_maintenance':
                return recent
            return []

        mock.query_firestore.side_effect = query
        client = make_client(mock)

        response = client.get('/api/machines/summary', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['total'] == 3  # excluye la borrada
        assert data['byStatus'] == {'operational': 1, 'maintenance': 1, 'out_of_service': 1}
        assert [m['id'] for m in data['upcomingMaintenance']] == ['a']  # solo dentro de 7d
        assert len(data['recentRepairs']) == 5  # tope 5
        assert data['recentRepairs'][0]['date'] == '2026-09-15'  # DESC

        # Una query por colección
        calls = mock.query_firestore.call_args_list
        machine_calls = [c for c in calls if c[0][0] == 'machines']
        maint_calls = [c for c in calls if c[0][0] == 'machine_maintenance']
        assert len(machine_calls) == 1
        assert len(maint_calls) == 1
        assert maint_calls[0][1]['order_by'] == 'date'
        assert maint_calls[0][1]['direction'] == 'DESC'
        assert maint_calls[0][1]['limit'] == 5

    def test_summary_no_upcoming_empty(self, make_client, auth_header):
        mock = create_mock_service(role='cashier')  # cashier puede leer summary
        mock.query_firestore.side_effect = lambda collection, **kw: (
            [{'id': 'a', 'status': 'operational', 'businessId': 'biz-1',
              'branchId': 'branch-1', 'nextMaintenanceDate': _date_plus(30)}]
            if collection == 'machines' else []
        )
        client = make_client(mock)

        response = client.get('/api/machines/summary', headers=auth_header)

        assert response.status_code == 200
        assert response.get_json()['data']['upcomingMaintenance'] == []


# ============================================================================
# POST /api/machines — kind='item' (validación condicional)
# ============================================================================

class TestCreateItem:

    def test_item_create_201_stores_fields(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.post('/api/machines', json={
            'kind': 'item', 'name': 'Mancuerna 10kg', 'category': 'free_weights',
            'quantity': 8, 'weightKg': 10,
        }, headers=auth_header)

        assert response.status_code == 201
        collection, record = mock.create_document.call_args[0]
        assert collection == 'machines'
        assert record['kind'] == 'item'
        assert record['quantity'] == 8
        assert record['weightKg'] == 10
        assert record['status'] == 'operational'
        assert record['nextMaintenanceDate'] is None
        assert record['isActive'] is True
        assert {'kind', 'name', 'quantity', 'weightKg', 'category', 'businessId'} <= set(record)

    def test_item_quantity_defaults_to_one(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.post('/api/machines', json={
            'kind': 'item', 'name': 'Cuerda', 'category': 'accessory',
        }, headers=auth_header)

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert record['quantity'] == 1
        assert record['weightKg'] is None

    @pytest.mark.parametrize('quantity', [0, -1, 'x', 2.5, True])
    def test_item_invalid_quantity_400(self, make_client, auth_header, quantity):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post('/api/machines', json={
            'kind': 'item', 'name': 'X', 'category': 'free_weights', 'quantity': quantity,
        }, headers=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_item_invalid_weight_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post('/api/machines', json={
            'kind': 'item', 'name': 'X', 'category': 'free_weights', 'weightKg': -1,
        }, headers=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_item_accepts_null_weight(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.post('/api/machines', json={
            'kind': 'item', 'name': 'X', 'category': 'other', 'weightKg': None,
        }, headers=auth_header)

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert record['weightKg'] is None

    def test_item_machine_category_rejected_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post('/api/machines', json={
            'kind': 'item', 'name': 'X', 'category': 'cardio',
        }, headers=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_unknown_kind_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post('/api/machines', json={
            'kind': 'gadget', 'name': 'X', 'category': 'cardio',
        }, headers=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_machine_kind_explicit_stored(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.post('/api/machines', json={
            'name': 'Bici', 'category': 'cardio', 'kind': 'machine',
        }, headers=auth_header)

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert record['kind'] == 'machine'
        assert record['status'] == 'operational'


# ============================================================================
# GET /api/machines?kind=  (filtro por tipo)
# ============================================================================

class TestListKindFilter:

    def _docs(self):
        return [
            {'id': 'm1', 'name': 'Cinta', 'category': 'cardio', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True, 'kind': 'machine'},
            {'id': 'i1', 'name': 'Mancuerna', 'category': 'free_weights', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True, 'kind': 'item',
             'quantity': 3},
            # legacy sin kind → machine
            {'id': 'l1', 'name': 'Remo', 'category': 'strength', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1'},
        ]

    def test_filter_item_only(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = self._docs()
        client = make_client(mock)

        response = client.get('/api/machines?kind=item', headers=auth_header)

        assert [m['id'] for m in response.get_json()['data']] == ['i1']
        # Sigue siendo UNA query scoped sólo por businessId (sin índice nuevo)
        assert mock.query_firestore.call_args[1]['filters'] == [
            {'field': 'businessId', 'operator': '==', 'value': 'biz-1'}
        ]

    def test_filter_machine_includes_legacy(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = self._docs()
        client = make_client(mock)

        response = client.get('/api/machines?kind=machine', headers=auth_header)

        # Orden estable por nombre: Cinta, Remo
        assert [m['id'] for m in response.get_json()['data']] == ['m1', 'l1']

    def test_no_filter_returns_all(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = self._docs()
        client = make_client(mock)

        response = client.get('/api/machines', headers=auth_header)

        assert {m['id'] for m in response.get_json()['data']} == {'m1', 'i1', 'l1'}


# ============================================================================
# GET /api/machines/summary — split máquinas / ítems
# ============================================================================

class TestSummaryKindSplit:

    def test_summary_split_machines_and_items(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        docs = [
            {'id': 'm1', 'kind': 'machine', 'status': 'operational',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True},
            {'id': 'm2', 'kind': 'machine', 'status': 'maintenance',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True},
            # Ítem con fecha de mantenimiento: NO debe entrar en upcomingMaintenance
            {'id': 'i1', 'kind': 'item', 'quantity': 5, 'nextMaintenanceDate': _date_plus(2),
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True},
            {'id': 'i2', 'kind': 'item', 'quantity': 2,
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True},
            {'id': 'i3', 'kind': 'item', 'quantity': 1,
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True},
        ]
        mock.query_firestore.side_effect = lambda collection, **kw: (
            docs if collection == 'machines' else []
        )
        client = make_client(mock)

        response = client.get('/api/machines/summary', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['total'] == 2
        assert data['byStatus'] == {'operational': 1, 'maintenance': 1, 'out_of_service': 0}
        assert data['upcomingMaintenance'] == []
        assert data['items'] == {'itemTypes': 3, 'totalUnits': 8}

    def test_items_only_business(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        docs = [
            {'id': 'i1', 'kind': 'item', 'quantity': 4,
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isActive': True},
        ]
        mock.query_firestore.side_effect = lambda collection, **kw: (
            docs if collection == 'machines' else []
        )
        client = make_client(mock)

        data = client.get('/api/machines/summary', headers=auth_header).get_json()['data']

        assert data['total'] == 0
        assert data['byStatus'] == {'operational': 0, 'maintenance': 0, 'out_of_service': 0}
        assert data['items'] == {'itemTypes': 1, 'totalUnits': 4}


# ============================================================================
# POST /api/machines/<id>/maintenance en un ítem
# ============================================================================

class TestMaintenanceOnItem:

    def test_maintenance_on_item_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(ITEM)
        client = make_client(mock)

        response = client.post('/api/machines/i1/maintenance',
                               json={'type': 'repair', 'status': 'completed',
                                     'resolvedStatus': 'operational', 'date': '2026-10-13'},
                               headers=auth_header)

        assert response.status_code == 400
        assert 'accesorios' in response.get_json()['error']['message'].lower()
        mock.create_document.assert_not_called()
        mock.update_document.assert_not_called()

    def test_legacy_doc_maintenance_still_201(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(MACHINE)  # sin kind → machine
        mock.create_document.return_value = {'id': 'rec-1'}
        client = make_client(mock)

        response = client.post('/api/machines/m1/maintenance',
                               json={'type': 'preventive', 'status': 'completed',
                                     'date': '2026-10-13'},
                               headers=auth_header)

        assert response.status_code == 201
        mock.create_document.assert_called_once()


# ============================================================================
# PUT /api/machines/<id> en un ítem
# ============================================================================

class TestUpdateItem:

    def test_update_item_quantity_200(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(ITEM)
        client = make_client(mock)

        response = client.put('/api/machines/i1', json={'quantity': 12}, headers=auth_header)

        assert response.status_code == 200
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'machines'
        assert doc_id == 'i1'
        assert update == {'quantity': 12}

    @pytest.mark.parametrize('quantity', [-3, 0, 'x'])
    def test_update_item_invalid_quantity_400(self, make_client, auth_header, quantity):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(ITEM)
        client = make_client(mock)

        response = client.put('/api/machines/i1', json={'quantity': quantity}, headers=auth_header)

        assert response.status_code == 400
        mock.update_document.assert_not_called()

    def test_update_item_fields_200(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(ITEM)
        client = make_client(mock)

        response = client.put('/api/machines/i1',
                              json={'weightKg': 12.5, 'category': 'accessory',
                                    'name': 'Mancuerna 12kg'},
                              headers=auth_header)

        assert response.status_code == 200
        _, _, update = mock.update_document.call_args[0]
        assert update['weightKg'] == 12.5
        assert update['category'] == 'accessory'
        assert update['name'] == 'Mancuerna 12kg'

    def test_update_item_invalid_weight_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(ITEM)
        client = make_client(mock)

        response = client.put('/api/machines/i1', json={'weightKg': -2}, headers=auth_header)

        assert response.status_code == 400
        mock.update_document.assert_not_called()

    def test_update_item_rejects_machine_category_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(ITEM)
        client = make_client(mock)

        response = client.put('/api/machines/i1', json={'category': 'cardio'}, headers=auth_header)

        assert response.status_code == 400
        mock.update_document.assert_not_called()
