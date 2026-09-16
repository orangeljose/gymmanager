"""
Tests para reportes de ingresos con filtros empujados a Firestore.

Cubre:
- Filtros del query: businessId ==, branchId == (si aplica), createdAt >= / <=
- super_admin: businessId desde el query param
- Exclusión Python de pagos isDeleted y de clientes soft-deleted
- by-method: sin fechas no agrega ventana createdAt
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from services.firebase_service import FirebaseService


@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    FirebaseService._reset()
    yield
    FirebaseService._reset()


def create_mock_service(role='super_admin', uid='admin-123', business_id='biz-1'):
    """Factory para mocks de FirebaseService (mismo patrón que test_dashboard)."""
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


def _income_with(mock, url):
    """Request DETERMINISTA: se ejecuta DENTRO de los patches de los call-sites."""
    with patch('services.firebase_service.FirebaseService', return_value=mock), \
         patch('middleware.auth_middleware.FirebaseService', return_value=mock), \
         patch('routes.reports.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()
        return client.get(url, headers={'Authorization': 'Bearer test-token'})


def make_payment(payment_id, client_id, amount, created_at, method='cash',
                 business_id='biz-1', branch_id='branch-1', is_deleted=None,
                 payment_date=None):
    p = {
        'id': payment_id,
        'clientId': client_id,
        'amount': amount,
        'method': method,
        'createdAt': created_at,
        'businessId': business_id,
        'branchId': branch_id,
        'paymentDate': payment_date,
    }
    if is_deleted is not None:
        p['isDeleted'] = is_deleted
    return p


def _payment_filters_from(mock, index=0):
    """Extrae los filters del N-ésimo call a query_firestore (payments = 0, clients = 1)."""
    call = mock.query_firestore.call_args_list[index]
    assert call.args[0] == 'payments'
    return call.kwargs['filters']


START_DT = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DT = datetime(2026, 4, 30, 23, 59, 59, tzinfo=timezone.utc)


class TestDailyIncomeQuery:
    """get_daily_income_report: filtros empujados a Firestore"""

    def test_super_admin_business_id_from_param(self):
        """super_admin usa businessId del query param (no el del usuario)"""
        mock = create_mock_service(role='super_admin', business_id='biz-1')
        mock.query_firestore.side_effect = [[], []]  # payments, clients

        response = _income_with(
            mock,
            '/api/reports/income/daily?startDate=2026-04-01&endDate=2026-04-30&businessId=biz-9'
        )

        assert response.status_code == 200
        filters = _payment_filters_from(mock)
        assert {'field': 'businessId', 'operator': '==', 'value': 'biz-9'} in filters
        assert {'field': 'createdAt', 'operator': '>=', 'value': START_DT} in filters
        assert {'field': 'createdAt', 'operator': '<=', 'value': END_DT} in filters
        # Sin branchId param → sin filtro branchId
        assert all(f['field'] != 'branchId' for f in filters)

    def test_branch_admin_uses_own_branch(self):
        """branch_admin filtra por SU sede en Firestore"""
        mock = create_mock_service(role='branch_admin', business_id='biz-1')
        mock.query_firestore.side_effect = [[], []]

        response = _income_with(
            mock,
            '/api/reports/income/daily?startDate=2026-04-01&endDate=2026-04-30'
        )

        assert response.status_code == 200
        filters = _payment_filters_from(mock)
        assert {'field': 'branchId', 'operator': '==', 'value': 'branch-1'} in filters
        assert {'field': 'businessId', 'operator': '==', 'value': 'biz-1'} in filters

    def test_super_admin_with_branch_param(self):
        """super_admin con branchId param → filtro branchId en Firestore"""
        mock = create_mock_service(role='super_admin', business_id='biz-1')
        mock.query_firestore.side_effect = [[], []]

        response = _income_with(
            mock,
            '/api/reports/income/daily?startDate=2026-04-01&endDate=2026-04-30'
            '&businessId=biz-9&branchId=branch-2'
        )

        assert response.status_code == 200
        filters = _payment_filters_from(mock)
        assert {'field': 'branchId', 'operator': '==', 'value': 'branch-2'} in filters


class TestDailyIncomePythonExclusions:
    """isDeleted + deleted-client exclusion se mantienen en Python"""

    def test_excludes_deleted_payments_and_deleted_clients(self):
        """Pago isDeleted y pago de cliente soft-deleted se excluyen del total"""
        created = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
        payments = [
            make_payment('p1', 'c1', 1000, created),                                  # válido
            make_payment('p2', 'c2', 2000, created, is_deleted=True),                 # soft-deleted
            make_payment('p3', 'c3', 3000, created),                                  # cliente borrado
        ]
        clients = [
            {'id': 'c3', 'businessId': 'biz-1', 'isDeleted': True},
            {'id': 'c1', 'businessId': 'biz-1'},
        ]

        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.side_effect = [payments, clients]

        response = _income_with(
            mock,
            '/api/reports/income/daily?startDate=2026-04-01&endDate=2026-04-30'
        )

        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert data['totalPeriod'] == 1000
        assert data['daily'] == [{'date': '2026-04-15', 'amount': 1000, 'paymentsCount': 1}]

    def test_legacy_payment_without_is_deleted_counts(self):
        """Pago legacy sin campo isDeleted se trata como no eliminado"""
        created = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
        payments = [
            make_payment('p1', 'c1', 5000, created),  # sin isDeleted
        ]
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.side_effect = [payments, []]

        response = _income_with(
            mock,
            '/api/reports/income/daily?startDate=2026-04-01&endDate=2026-04-30'
        )

        data = json.loads(response.data)['data']
        assert data['totalPeriod'] == 5000


class TestByMethodQuery:
    """get_income_by_method_report: mismos filtros + ventana opcional"""

    def test_query_filters_mirror_daily(self):
        """by-method con fechas y branchId → filtros completos en Firestore"""
        mock = create_mock_service(role='super_admin', business_id='biz-1')
        mock.query_firestore.side_effect = [[], []]

        response = _income_with(
            mock,
            '/api/reports/income/by-method?startDate=2026-04-01&endDate=2026-04-30'
            '&businessId=biz-9&branchId=branch-2'
        )

        assert response.status_code == 200
        filters = _payment_filters_from(mock)
        assert {'field': 'businessId', 'operator': '==', 'value': 'biz-9'} in filters
        assert {'field': 'branchId', 'operator': '==', 'value': 'branch-2'} in filters
        assert {'field': 'createdAt', 'operator': '>=', 'value': START_DT} in filters
        assert {'field': 'createdAt', 'operator': '<=', 'value': END_DT} in filters

    def test_no_dates_means_no_window_filter(self):
        """Sin startDate/endDate → NO se agregan filtros createdAt"""
        mock = create_mock_service(role='super_admin', business_id='biz-1')
        mock.query_firestore.side_effect = [[], []]

        response = _income_with(
            mock,
            '/api/reports/income/by-method?businessId=biz-9'
        )

        assert response.status_code == 200
        filters = _payment_filters_from(mock)
        assert all(f['field'] != 'createdAt' for f in filters)
        assert {'field': 'businessId', 'operator': '==', 'value': 'biz-9'} in filters

    def test_excludes_deleted_payments_and_deleted_clients(self):
        """Exclusión Python: isDeleted + cliente soft-deleted fuera del resultado"""
        created = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
        payments = [
            make_payment('p1', 'c1', 1000, created, method='cash'),                   # válido
            make_payment('p2', 'c2', 2000, created, method='card', is_deleted=True),  # soft-deleted
            make_payment('p3', 'c3', 3000, created, method='transfer'),               # cliente borrado
        ]
        clients = [
            {'id': 'c3', 'businessId': 'biz-1', 'isDeleted': True},
            {'id': 'c1', 'businessId': 'biz-1'},
        ]

        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.side_effect = [payments, clients]

        response = _income_with(
            mock,
            '/api/reports/income/by-method?startDate=2026-04-01&endDate=2026-04-30'
        )

        assert response.status_code == 200
        result = json.loads(response.data)['data']
        assert result == {
            'cash': {'amount': 1000, 'percentage': 100.0, 'count': 1, 'accounts': {}}
        }