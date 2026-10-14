"""
Tests para las rutas de Egresos (/api/expenses)

Patrón de mock (idéntico a test_machines.py / test_attendance.py): las rutas
importan `FirebaseService` a nivel de módulo, por lo que se parchea el símbolo en
`routes.expenses` y en `middleware.auth_middleware`, además del módulo
`services.firebase_service` que usa `app.py` al inicializar. Cada request se
ejecuta DENTRO de los patches para que cada test use SU mock y no dependa del
orden de ejecución entre archivos.

Cubre: CRUD, validación (amountCents/category/date), soft-delete + auditoría,
scope (business/branch), resumen (hoy/7d/30d + byCategory con UNA query) y la
matriz de permisos (admin+ permitido; cashier/trainer 403; sin auth 401).
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
    mock.create_document.return_value = {'id': 'new-doc-id'}
    mock.update_document.return_value = True
    return mock


def _today():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _date_minus(days):
    return (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()


EXPENSE = {
    'id': 'e1', 'category': 'rent', 'amountCents': 50000, 'description': 'Alquiler',
    'date': '2026-10-10', 'businessId': 'biz-1', 'branchId': 'branch-1',
    'registeredBy': 'user-123', 'registeredByName': 'Admin Test',
    'createdAt': '2026-10-10T10:00:00+00:00', 'isDeleted': False,
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
        ctx2 = patch('routes.expenses.FirebaseService', return_value=mock)
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
# GET /api/expenses  (list)
# ============================================================================

class TestListExpenses:

    def _expenses(self):
        return [
            {'id': 'e1', 'category': 'rent', 'amountCents': 50000, 'description': 'Alquiler octubre',
             'date': '2026-10-10', 'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            {'id': 'e2', 'category': 'supplies', 'amountCents': 2000, 'description': 'Toallas',
             'date': '2026-10-05', 'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            {'id': 'e3', 'category': 'services', 'amountCents': 1500, 'description': 'Internet',
             'date': '2026-09-01', 'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            {'id': 'e4', 'category': 'rent', 'amountCents': 9999, 'description': 'Borrado',
             'date': '2026-10-11', 'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': True},
        ]

    def test_list_filters_category_and_range_and_meta(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.return_value = self._expenses()
        client = make_client(mock)

        response = client.get(
            '/api/expenses?category=rent&startDate=2026-10-01&endDate=2026-10-31&page=1&limit=20',
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.get_json()
        ids = [e['id'] for e in data['data']]
        assert ids == ['e1']  # e4 borrado, e2 otra categoría, e3 fuera de rango
        assert data['meta'] == {'total': 1, 'page': 1, 'limit': 20, 'pages': 1}
        # Solo igualdad de businessId en Firestore (máximo 1 filtro)
        filters = mock.query_firestore.call_args[1]['filters']
        assert filters == [{'field': 'businessId', 'operator': '==', 'value': 'biz-1'}]

    def test_list_excludes_deleted_and_sorts_date_desc(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = self._expenses()
        client = make_client(mock)

        response = client.get('/api/expenses', headers=auth_header)

        ids = [e['id'] for e in response.get_json()['data']]
        assert 'e4' not in ids            # isDeleted → excluido
        assert ids == ['e1', 'e2', 'e3']  # date DESC

    def test_list_search_by_description(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = self._expenses()
        client = make_client(mock)

        response = client.get('/api/expenses?search=toalla', headers=auth_header)

        assert [e['id'] for e in response.get_json()['data']] == ['e2']

    def test_list_pagination(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = [
            {'id': f'e{i}', 'category': 'other', 'amountCents': 100, 'date': f'2026-10-{i + 1:02d}',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False}
            for i in range(5)
        ]
        client = make_client(mock)

        response = client.get('/api/expenses?page=2&limit=2', headers=auth_header)

        data = response.get_json()
        assert len(data['data']) == 2
        assert data['meta'] == {'total': 5, 'page': 2, 'limit': 2, 'pages': 3}

    def test_branch_scoped_user_filters_own_branch(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-1')
        mock.query_firestore.return_value = [
            {'id': 'a', 'category': 'rent', 'amountCents': 1, 'date': '2026-10-01',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            {'id': 'b', 'category': 'rent', 'amountCents': 1, 'date': '2026-10-01',
             'businessId': 'biz-1', 'branchId': 'branch-2', 'isDeleted': False},
        ]
        client = make_client(mock)

        response = client.get('/api/expenses', headers=auth_header)

        assert [e['id'] for e in response.get_json()['data']] == ['a']


# ============================================================================
# POST /api/expenses
# ============================================================================

class TestCreateExpense:

    def test_create_valid_201(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.create_document.return_value = {'id': 'new-1', 'category': 'supplies'}
        client = make_client(mock)

        response = client.post(
            '/api/expenses',
            json={'category': 'supplies', 'amountCents': 2500, 'date': '2026-10-12',
                  'description': 'Toallas', 'branchId': 'branch-1'},
            headers=auth_header,
        )

        assert response.status_code == 201
        assert response.get_json()['success'] is True
        collection, record = mock.create_document.call_args[0]
        assert collection == 'expenses'
        assert record['category'] == 'supplies'
        assert record['amountCents'] == 2500
        assert record['businessId'] == 'biz-1'
        assert record['branchId'] == 'branch-1'
        assert record['isDeleted'] is False
        assert record['registeredBy'] == 'user-123'
        assert {
            'category', 'amountCents', 'description', 'date', 'businessId', 'branchId',
            'registeredBy', 'registeredByName', 'createdAt', 'isDeleted',
        } <= set(record)

    def test_create_description_optional(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.post(
            '/api/expenses',
            json={'category': 'other', 'amountCents': 100, 'date': '2026-10-12'},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert record['description'] is None

    def test_create_with_method_and_payment_account(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.post(
            '/api/expenses',
            json={'category': 'rent', 'amountCents': 50000, 'date': '2026-10-12',
                  'method': 'zelle', 'paymentAccountId': 'acc-zelle-1'},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert record['method'] == 'zelle'
        assert record['paymentAccountId'] == 'acc-zelle-1'

    def test_create_default_method_cash(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.post(
            '/api/expenses',
            json={'category': 'other', 'amountCents': 100, 'date': '2026-10-12'},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert record['method'] == 'cash'
        assert record['paymentAccountId'] is None

    def test_create_invalid_method_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post(
            '/api/expenses',
            json={'category': 'rent', 'amountCents': 100, 'date': '2026-10-12',
                  'method': 'bitcoin'},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    @pytest.mark.parametrize('amount', [0, -100, '500', 12.5, True])
    def test_create_invalid_amount_cents_400(self, make_client, auth_header, amount):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post(
            '/api/expenses',
            json={'category': 'rent', 'amountCents': amount, 'date': '2026-10-12'},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_create_invalid_category_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post(
            '/api/expenses',
            json={'category': 'travel', 'amountCents': 100, 'date': '2026-10-12'},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_create_invalid_date_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post(
            '/api/expenses',
            json={'category': 'rent', 'amountCents': 100, 'date': '01-2026'},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_create_cross_branch_403(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-1')
        client = make_client(mock)

        response = client.post(
            '/api/expenses',
            json={'category': 'rent', 'amountCents': 100, 'date': '2026-10-12',
                  'branchId': 'branch-2'},
            headers=auth_header,
        )

        assert response.status_code == 403
        mock.create_document.assert_not_called()


# ============================================================================
# PUT / DELETE /api/expenses/<id>
# ============================================================================

class TestUpdateAndDeleteExpense:

    def test_update_fields_200(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(EXPENSE)
        client = make_client(mock)

        response = client.put(
            '/api/expenses/e1',
            json={'amountCents': 55000, 'description': 'Alquiler ajustado'},
            headers=auth_header,
        )

        assert response.status_code == 200
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'expenses'
        assert doc_id == 'e1'
        assert update == {'amountCents': 55000, 'description': 'Alquiler ajustado'}

    def test_update_invalid_amount_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(EXPENSE)
        client = make_client(mock)

        response = client.put('/api/expenses/e1', json={'amountCents': 0}, headers=auth_header)

        assert response.status_code == 400
        mock.update_document.assert_not_called()

    def test_update_method_and_payment_account(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(EXPENSE)
        client = make_client(mock)

        response = client.put(
            '/api/expenses/e1',
            json={'method': 'binance', 'paymentAccountId': 'acc-binance-1'},
            headers=auth_header,
        )

        assert response.status_code == 200
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'expenses'
        assert doc_id == 'e1'
        assert update == {'method': 'binance', 'paymentAccountId': 'acc-binance-1'}

    def test_update_missing_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = None
        client = make_client(mock)

        response = client.put('/api/expenses/ghost', json={'amountCents': 100}, headers=auth_header)

        assert response.status_code == 404
        mock.update_document.assert_not_called()

    def test_update_deleted_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        deleted = dict(EXPENSE)
        deleted['isDeleted'] = True
        mock.get_document.return_value = deleted
        client = make_client(mock)

        response = client.put('/api/expenses/e1', json={'amountCents': 100}, headers=auth_header)

        assert response.status_code == 404
        mock.update_document.assert_not_called()

    def test_update_cross_branch_403(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-2')
        mock.get_document.return_value = dict(EXPENSE)  # branch-1
        client = make_client(mock)

        response = client.put('/api/expenses/e1', json={'amountCents': 100}, headers=auth_header)

        assert response.status_code == 403
        mock.update_document.assert_not_called()

    def test_soft_delete_audit_preserved(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = dict(EXPENSE)
        client = make_client(mock)

        response = client.delete('/api/expenses/e1', headers=auth_header)

        assert response.status_code == 200
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'expenses'
        assert doc_id == 'e1'
        assert update['isDeleted'] is True
        assert update['deletedBy'] == 'user-123'
        assert update['deletedAt']
        mock.delete_document.assert_not_called()

    def test_delete_missing_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = None
        client = make_client(mock)

        assert client.delete('/api/expenses/ghost', headers=auth_header).status_code == 404

    def test_deleted_expense_excluded_from_list_and_summary(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = [
            {'id': 'e1', 'category': 'rent', 'amountCents': 50000, 'date': _today(),
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            {'id': 'e2', 'category': 'rent', 'amountCents': 99999, 'date': _today(),
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': True},
        ]
        client = make_client(mock)

        listed = client.get('/api/expenses', headers=auth_header).get_json()['data']
        summary = client.get('/api/expenses/summary', headers=auth_header).get_json()['data']

        assert [e['id'] for e in listed] == ['e1']
        assert summary['today'] == 50000
        assert summary['byCategory']['rent'] == 50000


# ============================================================================
# GET /api/expenses/summary
# ============================================================================

class TestExpensesSummary:

    def test_summary_windows_and_by_category_one_query(self, make_client, auth_header):
        mock = create_mock_service(role='admin')

        docs = [
            # hoy
            {'id': 't1', 'category': 'supplies', 'amountCents': 1000, 'date': _today(),
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            # hace 3 dias (dentro de 7d y 30d)
            {'id': 'w1', 'category': 'services', 'amountCents': 2000, 'date': _date_minus(3),
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            # hace 20 dias (solo 30d)
            {'id': 'm1', 'category': 'rent', 'amountCents': 4000, 'date': _date_minus(20),
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            # hace 60 dias (fuera de toda ventana)
            {'id': 'o1', 'category': 'payroll', 'amountCents': 8000, 'date': _date_minus(60),
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            # borrado
            {'id': 'd1', 'category': 'rent', 'amountCents': 99999, 'date': _today(),
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': True},
        ]
        mock.query_firestore.return_value = docs
        client = make_client(mock)

        response = client.get('/api/expenses/summary', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['today'] == 1000
        assert data['week'] == 1000 + 2000
        assert data['month'] == 1000 + 2000 + 4000
        assert data['byCategory'] == {
            'payroll': 8000, 'supplies': 1000, 'services': 2000,
            'rent': 4000, 'maintenance': 0, 'other': 0,
        }

        # UNA sola query scoped a expenses
        calls = mock.query_firestore.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == 'expenses'
        assert calls[0][1]['filters'] == [
            {'field': 'businessId', 'operator': '==', 'value': 'biz-1'}
        ]

    def test_summary_empty_returns_zeroes(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = []
        client = make_client(mock)

        data = client.get('/api/expenses/summary', headers=auth_header).get_json()['data']

        assert data['today'] == 0
        assert data['week'] == 0
        assert data['month'] == 0
        assert data['byCategory']['rent'] == 0


# ============================================================================
# GET /api/expenses/report
# ============================================================================

class TestExpensesReport:

    def test_report_totals_count_by_category_and_daily(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.return_value = [
            {'id': 'e1', 'category': 'rent', 'amountCents': 50000, 'date': '2026-10-01',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            {'id': 'e2', 'category': 'services', 'amountCents': 1500, 'date': '2026-10-01',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            {'id': 'e3', 'category': 'rent', 'amountCents': 2000, 'date': '2026-10-02',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            # fuera de rango → excluido
            {'id': 'e4', 'category': 'payroll', 'amountCents': 8000, 'date': '2026-09-01',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            # borrado → excluido
            {'id': 'e5', 'category': 'other', 'amountCents': 99999, 'date': '2026-10-02',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': True},
        ]
        client = make_client(mock)

        response = client.get(
            '/api/expenses/report?startDate=2026-10-01&endDate=2026-10-31',
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['totalCents'] == 50000 + 1500 + 2000
        assert data['count'] == 3
        assert data['byCategory'] == {
            'payroll': 0, 'supplies': 0, 'services': 1500,
            'rent': 52000, 'maintenance': 0, 'other': 0,
        }
        assert data['daily'] == [
            {'date': '2026-10-01', 'totalCents': 50000 + 1500},
            {'date': '2026-10-02', 'totalCents': 2000},
        ]
        # UNA sola query scoped a expenses
        calls = mock.query_firestore.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == 'expenses'
        assert calls[0][1]['filters'] == [
            {'field': 'businessId', 'operator': '==', 'value': 'biz-1'}
        ]

    def test_report_empty_returns_zeroes(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.return_value = []
        client = make_client(mock)

        data = client.get('/api/expenses/report', headers=auth_header).get_json()['data']

        assert data['totalCents'] == 0
        assert data['count'] == 0
        assert data['byCategory']['rent'] == 0
        assert data['daily'] == []

    def test_report_invalid_date_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.get('/api/expenses/report?startDate=01-2026', headers=auth_header)

        assert response.status_code == 400
        mock.query_firestore.assert_not_called()

    def test_report_branch_scoped_user_filters_own_branch(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-1')
        mock.query_firestore.return_value = [
            {'id': 'a', 'category': 'rent', 'amountCents': 1000, 'date': '2026-10-01',
             'businessId': 'biz-1', 'branchId': 'branch-1', 'isDeleted': False},
            {'id': 'b', 'category': 'rent', 'amountCents': 99999, 'date': '2026-10-01',
             'businessId': 'biz-1', 'branchId': 'branch-2', 'isDeleted': False},
        ]
        client = make_client(mock)

        data = client.get('/api/expenses/report', headers=auth_header).get_json()['data']

        assert data['totalCents'] == 1000
        assert data['count'] == 1


# ============================================================================
# Permisos (admin+; cashier/trainer 403; sin auth 401)
# ============================================================================

class TestPermissions:

    @pytest.mark.parametrize('method,path', [
        ('get', '/api/expenses'),
        ('post', '/api/expenses'),
        ('get', '/api/expenses/summary'),
        ('get', '/api/expenses/report'),
        ('put', '/api/expenses/e1'),
        ('delete', '/api/expenses/e1'),
    ])
    @pytest.mark.parametrize('role', ['cashier', 'trainer'])
    def test_non_admin_roles_forbidden_403(self, make_client, auth_header, method, path, role):
        mock = create_mock_service(role=role)
        client = make_client(mock)

        response = getattr(client, method)(path, headers=auth_header, json={})

        assert response.status_code == 403
        assert response.get_json()['success'] is False

    @pytest.mark.parametrize('method,path', [
        ('get', '/api/expenses'),
        ('post', '/api/expenses'),
        ('get', '/api/expenses/summary'),
        ('get', '/api/expenses/report'),
        ('put', '/api/expenses/e1'),
        ('delete', '/api/expenses/e1'),
    ])
    def test_unauth_returns_401(self, make_client, method, path):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = getattr(client, method)(path, json={})

        assert response.status_code == 401

    @pytest.mark.parametrize('role', ['super_admin', 'admin', 'branch_admin'])
    def test_admin_roles_can_list_200(self, make_client, auth_header, role):
        mock = create_mock_service(role=role, business_id='biz-1')
        mock.query_firestore.return_value = []
        client = make_client(mock)

        assert client.get('/api/expenses', headers=auth_header).status_code == 200
