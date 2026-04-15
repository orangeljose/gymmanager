"""
Modelos y validaciones para Usuarios
"""
from typing import Optional, Dict, Any, List

class UserModel:
    """Modelo de usuario para Firestore"""
    
    # Roles válidos
    VALID_ROLES = ['super_admin', 'branch_admin', 'cashier', 'trainer']
    
    # Permisos por rol
    ROLE_PERMISSIONS = {
        'super_admin': ['*'],  # Todos los permisos
        'branch_admin': [
            'read_clients', 'write_clients', 
            'read_payments', 'write_payments', 
            'read_reports'
        ],
        'cashier': ['read_clients', 'write_payments'],
        'trainer': ['read_clients']
    }
    
    @staticmethod
    def validate_role(role: str) -> bool:
        """Valida si un rol es válido"""
        return role in UserModel.VALID_ROLES
    
    @staticmethod
    def get_permissions(role: str) -> List[str]:
        """Obtiene la lista de permisos para un rol"""
        return UserModel.ROLE_PERMISSIONS.get(role, [])
    
    @staticmethod
    def has_permission(user_role: str, required_permission: str) -> bool:
        """Verifica si un usuario tiene un permiso específico"""
        permissions = UserModel.get_permissions(user_role)
        return '*' in permissions or required_permission in permissions
    
    @staticmethod
    def can_access_business(user_business_id: str, target_business_id: str) -> bool:
        """Verifica si un usuario puede acceder a un negocio"""
        return user_business_id == target_business_id
    
    @staticmethod
    def can_access_branch(user_branch_id: Optional[str], target_branch_id: str, user_role: str) -> bool:
        """Verifica si un usuario puede acceder a una sede"""
        # Super admin puede acceder a todas las sedes
        if user_role == 'super_admin':
            return True
        
        # Otros roles solo pueden acceder a su sede
        return user_branch_id == target_branch_id
    
    @staticmethod
    def from_firestore(doc_data: Dict[str, Any], doc_id: str) -> Dict[str, Any]:
        """Convierte documento de Firestore a modelo de usuario"""
        user = doc_data.copy()
        user['id'] = doc_id
        
        # Convertir timestamps a strings si es necesario
        if 'createdAt' in user and hasattr(user['createdAt'], 'isoformat'):
            user['createdAt'] = user['createdAt'].isoformat()
        
        return user
    
    @staticmethod
    def to_firestore(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte modelo de usuario a formato Firestore"""
        firestore_data = data.copy()
        
        # Eliminar campos que no se guardan en Firestore
        firestore_data.pop('id', None)
        
        return firestore_data
