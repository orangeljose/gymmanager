"""
Middleware de GymManager
"""
from .auth_middleware import require_auth, require_role

__all__ = [
    'require_auth',
    'require_role'
]
