"""
Rutas de API de GymManager
"""
from .auth import auth_bp
from .clients import clients_bp
from .payments import payments_bp
from .reports import reports_bp
from .branches import branches_bp
from .plans import plans_bp
from .payment_accounts import payment_accounts_bp
from .users import users_bp
from .invitations import invitations_bp
from .businesses import businesses_bp

__all__ = [
    'auth_bp',
    'clients_bp',
    'payments_bp',
    'reports_bp',
    'branches_bp',
    'plans_bp',
    'payment_accounts_bp',
    'users_bp',
    'invitations_bp',
    'businesses_bp'
]
