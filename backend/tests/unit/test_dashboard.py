"""
Tests para GET /api/reports/dashboard

Patrón: reset singleton → create fresh mock → patch → test.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

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
# HELPERS - Crean datos de muestra
# ============================================================================

def make_client(client_id, name, is_active=True, membership_end=None, business_id='biz-1', branch_id='branch-1'):
    """Factory para crear datos de cliente de muestra"""
    return {
        'id': client_id,
        'name': name,
        'isActive': is_active,
        'membershipEnd': membership_end or _future_days(30),
        'businessId': business_id,
        'branchId': branch_id,
    }


def make_payment(client_id, client_name, amount, created_at=None, business_id='biz-1', branch_id='branch-1'):
    """Factory para crear datos de pago de muestra"""
    return {
        'id': f'pay-{client_id}',
        'clientId': client_id,
        'clientName': client_name,
        'amount': amount,
        'createdAt': created_at or datetime.now(),
        'businessId': business_id,
        'branchId': branch_id,
    }


def _future_days(n):
    return (datetime.now() + timedelta(days=n)).isoformat()


def _past_days(n):
    return (datetime.now() - timedelta(days=n)).isoformat()


# ============================================================================
# FIXTURES
# ============================================================================

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


def _make_client(mock):
    """Crea un Flask test client con mock injectado."""
    with patch('services.firebase_service.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app.test_client()


# ============================================================================
# TESTS
# ============================================================================

class TestDashboardStructure:
    """Verifica que el dashboard devuelva los 7 campos requeridos"""

    def test_dashboard_returns_all_seven_fields(self):
        """GET /api/reports/dashboard devuelve los 7 campos"""
        mock = create_mock_service()

        # query_firestore llamado 2 veces: clients (primero) y payments (segundo)
        mock.query_firestore.side_effect = [
            [],  # clients
            [],  # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        dashboard = data['data']
        assert 'activeClients' in dashboard
        assert 'todayIncome' in dashboard
        assert 'overdueClients' in dashboard
        assert 'expiringThisWeek' in dashboard
        assert 'incomeChart' in dashboard
        assert 'topPayingClients' in dashboard
        assert 'retentionRate' in dashboard

        # incomeChart debe tener 30 días
        assert len(dashboard['incomeChart']) == 30


class TestActiveClientsCount:
    """Verifica el conteo de clientes activos"""

    def test_counts_only_active_clients(self):
        """Solo clientes con isActive=True se cuentan como activos"""
        now = datetime.now()

        clients = [
            make_client('c1', 'Activo Juan', is_active=True, membership_end=_future_days(30)),
            make_client('c2', 'Activa Maria', is_active=True, membership_end=_future_days(15)),
            make_client('c3', 'Inactivo Pedro', is_active=False, membership_end=_past_days(5)),
        ]

        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            clients,  # clients query
            [],       # payments query
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        assert data['data']['activeClients'] == 2

    def test_zero_active_clients_when_all_inactive(self):
        """Todos los clientes inactivos → activeClients=0"""
        clients = [
            make_client('c1', 'Inactivo 1', is_active=False, membership_end=_future_days(30)),
            make_client('c2', 'Inactivo 2', is_active=False, membership_end=_past_days(5)),
        ]

        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            clients,  # clients
            [],       # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        assert data['data']['activeClients'] == 0


class TestOverdueClientsCount:
    """Verifica el conteo de clientes morosos"""

    def test_counts_clients_with_expired_membership(self):
        """Clientes con membershipEnd en el pasado se cuentan como morosos"""
        clients = [
            make_client('c1', 'Vencido Carlos', is_active=True, membership_end=_past_days(10)),
            make_client('c2', 'Activa Ana', is_active=True, membership_end=_future_days(15)),
        ]

        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            clients,  # clients
            [],       # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        assert data['data']['overdueClients'] == 1

    def test_zero_overdue_when_all_current(self):
        """Todos los clientes están al día → overdueClients=0"""
        clients = [
            make_client('c1', 'Al día 1', is_active=True, membership_end=_future_days(30)),
            make_client('c2', 'Al día 2', is_active=True, membership_end=_future_days(15)),
        ]

        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            clients,  # clients
            [],       # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        assert data['data']['overdueClients'] == 0

    def test_inactive_clients_not_counted_as_overdue(self):
        """Clientes inactivos vencidos NO cuentan como morosos"""
        clients = [
            make_client('c1', 'Inactivo vencido', is_active=False, membership_end=_past_days(10)),
            make_client('c2', 'Activo al día', is_active=True, membership_end=_future_days(15)),
        ]

        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            clients,  # clients
            [],       # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        assert data['data']['overdueClients'] == 0


class TestTodayIncome:
    """Verifica el cálculo de ingresos del día actual"""

    def test_sums_today_payments(self):
        """Suma de pagos creados hoy"""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_morning = today_start.replace(hour=10, minute=0)

        payments = [
            make_payment('c1', 'Juan', 35000, created_at=today_morning),
            make_payment('c2', 'Maria', 50000, created_at=today_morning),
        ]

        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            [],       # clients
            payments, # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        assert data['data']['todayIncome'] == 85000

    def test_excludes_past_payments_from_today_income(self):
        """Pagos de días anteriores NO cuentan para todayIncome"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        payments = [
            make_payment('c1', 'Juan', 35000, created_at=yesterday),
        ]

        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            [],       # clients
            payments, # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        assert data['data']['todayIncome'] == 0


class TestEmptyData:
    """Verifica manejo de estados vacíos"""

    def test_empty_dashboard_with_no_clients_no_payments(self):
        """Dashboard con 0 clientes y 0 pagos devuelve ceros"""
        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            [],  # clients
            [],  # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        assert response.status_code == 200
        data = json.loads(response.data)
        d = data['data']

        assert d['activeClients'] == 0
        assert d['todayIncome'] == 0
        assert d['overdueClients'] == 0
        assert d['expiringThisWeek'] == 0
        assert d['retentionRate'] == 0.0
        assert len(d['incomeChart']) == 30
        assert all(p['amount'] == 0 for p in d['incomeChart'])
        assert d['topPayingClients'] == []

    def test_retention_rate_with_no_clients(self):
        """Tasa de retención con 0 clientes totales es 0.0"""
        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            [],  # clients
            [],  # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        assert data['data']['retentionRate'] == 0.0


class TestExpiringThisWeek:
    """Verifica el conteo de clientes que vencen esta semana"""

    def test_counts_expiring_within_7_days(self):
        """Clientes activos con membershipEnd en [hoy, hoy+7]"""
        now = datetime.now()
        clients = [
            make_client('c1', 'Vence hoy', is_active=True,
                       membership_end=now.isoformat()),
            make_client('c2', 'Vence en 3 días', is_active=True,
                       membership_end=(now + timedelta(days=3)).isoformat()),
            make_client('c3', 'Vence en 7 días', is_active=True,
                       membership_end=(now + timedelta(days=7)).isoformat()),
            make_client('c4', 'Vence en 15 días', is_active=True,
                       membership_end=(now + timedelta(days=15)).isoformat()),
        ]

        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            clients,  # clients
            [],       # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        # c1 (hoy), c2 (3d), c3 (7d) → 3. c4 (15d) no.
        assert data['data']['expiringThisWeek'] == 3


class TestTopPayingClients:
    """Verifica el ranking de top clientes"""

    def test_top_clients_returned_in_response(self):
        """topPayingClients está presente en la respuesta"""
        mock = create_mock_service()
        mock.query_firestore.side_effect = [
            [],  # clients
            [],  # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})

        data = json.loads(response.data)
        assert 'topPayingClients' in data['data']
        assert isinstance(data['data']['topPayingClients'], list)


class TestAccessControl:
    """Verifica control de acceso"""

    def test_unauthorized_without_token(self):
        """Sin token → 401"""
        mock = create_mock_service()

        with patch('services.firebase_service.FirebaseService', return_value=mock):
            from app import create_app
            app = create_app()
            app.config['TESTING'] = True
            client = app.test_client()

        response = client.get('/api/reports/dashboard')
        assert response.status_code == 401

    def test_cashier_can_access(self):
        """Rol cashier tiene acceso al dashboard"""
        mock = create_mock_service(role='cashier', uid='cashier-123')
        mock.query_firestore.side_effect = [
            [],  # clients
            [],  # payments
        ]

        client = _make_client(mock)
        response = client.get('/api/reports/dashboard', headers={'Authorization': 'Bearer test-token'})
        assert response.status_code == 200
