"""
Rutas de API de GymManager
"""
from .auth import auth_bp
from .clients import clients_bp
from .payments import payments_bp
from .reports import reports_bp
from .branches import branches_bp

__all__ = [
    'auth_bp',
    'clients_bp',
    'payments_bp', 
    'reports_bp',
    'branches_bp'
]
