"""
Pytest configuration and shared fixtures for GymManager tests

Este archivo configura el ambiente de testing con las siguientes características:

1. AISLAMIENTO DE TESTS - Usa scope='module' con fixture autouse para resetear
   el singleton de FirebaseService antes de cada archivo de test.

2. MOCK DE FIREBASE - Provee un mock simple que intercepta las llamadas a Firebase
   sin necesidad de credenciales reales.

3. FACTORY DE MOCKS - create_mock_service() crea mocks con usuario admin por defecto.

PATRÓN DE USO:
- reset_singleton (autouse, scope='module'): se ejecuta antes de cada archivo
- client fixture: crea app + client fresco para cada test
- create_mock_service(): factory para crear mocks frescos

El problema que resuelve: Flask cachea módulos Python entre archivos de test,
y el singleton FirebaseService mantiene estado. Con autouse(scope='module')
cada archivo de test empieza con estado limpio.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock


# ============================================================================
# FACTORY DE MOCKS - Crea mocks frescos para cada test
# ============================================================================

def create_mock_service(role='super_admin', uid='admin-123', business_id='biz-1'):
    """
    Factory para crear mocks de FirebaseService.

    Args:
        role: Rol del usuario ('super_admin', 'cashier', etc.)
        uid: UID del usuario
        business_id: ID del negocio

    Returns:
        MagicMock configurado con verify_token, get_user_by_uid, query_firestore, etc.
    """
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
# FIXTURES DE AISLAMIENTO
# ============================================================================

@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    """
    Resetea el singleton de FirebaseService ANTES de cada archivo de test.

    El scope='module' con autouse significa que se ejecuta una vez antes de
    cada archivo de test (módulo Python), no antes de cada test individual.

    Esto soluciona el problema de que Flask cachea los módulos y el singleton
    mantiene estado entre archivos de test.
    """
    from services import firebase_service
    firebase_service.FirebaseService._reset()
    yield
    # Cleanup al final si es necesario
    firebase_service.FirebaseService._reset()


# ============================================================================
# FIXTURES COMPARTIDOS
# ============================================================================

@pytest.fixture
def mock_admin():
    """Mock de FirebaseService con rol super_admin"""
    return create_mock_service(role='super_admin', uid='admin-123')


@pytest.fixture
def mock_cashier():
    """Mock de FirebaseService con rol cashier"""
    return create_mock_service(role='cashier', uid='cashier-123')


@pytest.fixture
def auth_header():
    """Header de autenticación básico para requests"""
    return {'Authorization': 'Bearer test-token'}


# ============================================================================
# SAMPLE DATA FIXTURES - Para tests de modelos
# ============================================================================

@pytest.fixture
def sample_plan_data():
    """Sample plan data for testing"""
    return {
        'name': 'Mensual',
        'price': 35000,
        'durationDays': 30,
        'businessId': 'test-business',
        'description': 'Acceso por 30 días',
        'benefits': ['Acceso total', 'Clases grupales']
    }


@pytest.fixture
def sample_payment_account_data():
    """Sample payment account data for testing"""
    return {
        'type': 'zelle',
        'identifier': 'test@example.com',
        'label': 'Cuenta de prueba',
        'businessId': 'test-business',
        'description': 'Cuenta para tests'
    }


@pytest.fixture
def sample_client_data():
    """Sample client data for testing"""
    return {
        'name': 'Juan Pérez',
        'email': 'juan@test.com',
        'phone': '+584141234567',
        'branchId': 'test-branch',
        'businessId': 'test-business',
        'membershipPlanId': 'test-plan'
    }


@pytest.fixture
def sample_payment_data():
    """Sample payment data for testing"""
    return {
        'clientId': 'test-client',
        'amount': 35000,
        'method': 'cash',
        'membershipPlanId': 'test-plan',
        'branchId': 'test-branch'
    }


@pytest.fixture
def clean_app():
    """
    Crea una app limpia con mock injectado.
    Útil para tests que necesitan una app sin el contexto de route tests.
    """
    from services import firebase_service
    firebase_service.FirebaseService._reset()

    mock = create_mock_service()

    with patch('services.firebase_service.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app