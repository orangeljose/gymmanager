"""
Tests del reporte de solvencia (morosos) — fix N+1.

Cubre:
- query_firestore se llama UNA sola vez para payments (antes: una por cliente)
- Enriquecimiento con el ÚLTIMO pago de cada cliente (createdAt DESC)
- Filtros del query de pagos: businessId/branchId según el alcance del rol
- Semántica preservada: si el pago más reciente está soft-deleted se trata
  como "sin pago" (mismo resultado que el query anterior con limit=1)
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


def create_mock_service(role='admin', uid='admin-123', business_id='biz-1'):
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


def _solvency_with(mock, url='/api/reports/solvency'):
    """Request DETERMINISTA: se ejecuta DENTRO de los patches de los call-sites."""
    with patch('services.firebase_service.FirebaseService', return_value=mock), \
         patch('middleware.auth_middleware.FirebaseService', return_value=mock), \
         patch('routes.reports.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()
        return client.get(url, headers={'Authorization': 'Bearer test-token'})


def make_client(cid, membership_end, branch_id='branch-1', business_id='biz-1'):
    return {
        'id': cid,
        'name': f'Client {cid}',
        'phone': f'+{cid}',
        'membershipPlanId': 'plan-1',
        'membershipEnd': membership_end,
        'isActive': True,
        'branchId': branch_id,
        'businessId': business_id,
    }


def make_payment(pid, client_id, amount, created_at, business_id='biz-1',
                 branch_id='branch-1', is_deleted=None):
    p = {
        'id': pid,
        'clientId': client_id,
        'amount': amount,
        'createdAt': created_at,
        'businessId': business_id,
        'branchId': branch_id,
    }
    if is_deleted is not None:
        p['isDeleted'] = is_deleted
    return p


def dt(y, m, d):
    return datetime(y, m, d, 12, 0, 0, tzinfo=timezone.utc)


def _payments_call(mock):
    """Devuelve el call a query_firestore de la colección payments (o None)."""
    for call in mock.query_firestore.call_args_list:
        if call.args[0] == 'payments':
            return call
    return None


class TestSolvencyEnrichesFromGroupedPayments:
    """Fix N+1: una sola query de payments agrupada por clientId."""

    def test_payments_queried_once_not_per_client(self):
        past = dt(2026, 1, 1)
        clients = [
            make_client('c1', past),
            make_client('c2', past),
        ]
        payments = [
            make_payment('p1', 'c1', 1000, dt(2026, 1, 1).isoformat()),
            make_payment('p2', 'c1', 2000, dt(2026, 1, 15).isoformat()),
            make_payment('p3', 'c2', 3000, dt(2026, 1, 20).isoformat()),
        ]
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.side_effect = [clients, payments]

        response = _solvency_with(mock)

        assert response.status_code == 200
        data = json.loads(response.data)['data']
        by_id = {c['id']: c for c in data}

        # Cada cliente enriquecido con SU último pago (createdAt DESC)
        assert by_id['c1']['lastPaymentAmount'] == 2000
        assert by_id['c1']['lastPaymentDate'] == dt(2026, 1, 15).isoformat()
        assert by_id['c2']['lastPaymentAmount'] == 3000
        assert by_id['c2']['lastPaymentDate'] == dt(2026, 1, 20).isoformat()

        # SOLO 2 llamadas totales: clients + payments (antes: 1 + N)
        assert mock.query_firestore.call_count == 2
        assert _payments_call(mock) is not None

    def test_branch_admin_payment_filters_include_business_and_branch(self):
        past = dt(2026, 1, 1)
        mock = create_mock_service(role='branch_admin', business_id='biz-1')
        mock.query_firestore.side_effect = [[make_client('c1', past)], []]

        response = _solvency_with(mock)

        assert response.status_code == 200
        pay_call = _payments_call(mock)
        assert pay_call is not None
        filters = pay_call.kwargs.get('filters') or []
        assert {'field': 'businessId', 'operator': '==', 'value': 'biz-1'} in filters
        assert {'field': 'branchId', 'operator': '==', 'value': 'branch-1'} in filters

    def test_super_admin_without_branch_has_no_scope_filters(self):
        past = dt(2026, 1, 1)
        mock = create_mock_service(role='super_admin', business_id='biz-1')
        mock.query_firestore.side_effect = [[make_client('c1', past)], []]

        response = _solvency_with(mock)

        assert response.status_code == 200
        pay_call = _payments_call(mock)
        assert pay_call is not None
        filters = pay_call.kwargs.get('filters') or []
        assert filters == []

    def test_latest_payment_soft_deleted_treated_as_no_payment(self):
        """Preserva el comportamiento del query anterior con limit=1: si el pago
        más reciente está soft-deleted no se muestra pago (no hace fallback
        a un pago anterior no eliminado)."""
        past = dt(2026, 1, 1)
        clients = [make_client('c1', past)]
        payments = [
            make_payment('p-old', 'c1', 1000, dt(2026, 1, 1).isoformat()),
            make_payment('p-new', 'c1', 2000, dt(2026, 1, 15).isoformat(), is_deleted=True),
        ]
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.side_effect = [clients, payments]

        response = _solvency_with(mock)

        assert response.status_code == 200
        c1 = json.loads(response.data)['data'][0]
        assert c1['lastPaymentAmount'] == 0
        assert c1['lastPaymentDate'] is None