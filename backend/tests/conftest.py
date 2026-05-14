"""
Pytest configuration and shared fixtures for GymManager tests
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture
def app():
    """Application fixture for tests"""
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Test client fixture"""
    return app.test_client()


@pytest.fixture
def mock_firebase(mocker):
    """Mock Firebase service for unit tests"""
    mock_fs = mocker.patch('services.firebase_service.FirebaseService')
    return mock_fs


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