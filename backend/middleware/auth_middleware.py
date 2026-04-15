"""
Middleware de autenticación y autorización para GymManager
"""
import logging
import functools
from flask import request, jsonify, g
from services.firebase_service import FirebaseService
from models.user import UserModel

logger = logging.getLogger(__name__)

def require_auth(f):
    """
    Decorador para requerir autenticación con Firebase
    
    Verifica el token JWT de Firebase, obtiene información del usuario
    y la inyecta en el contexto de la request
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Obtener token del header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                logger.warning("Request sin header Authorization")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 401,
                        'message': 'Se requiere token de autenticación'
                    }
                }), 401
            
            # Extraer token Bearer
            if not auth_header.startswith('Bearer '):
                logger.warning("Header Authorization no tiene formato Bearer")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 401,
                        'message': 'Formato de token inválido. Use: Bearer <token>'
                    }
                }), 401
            
            token = auth_header.split(' ')[1]
            
            # Verificar token con Firebase
            firebase_service = FirebaseService()
            decoded_token = firebase_service.verify_token(token)
            
            # Obtener información completa del usuario desde Firestore
            uid = decoded_token.get('uid')
            user_data = firebase_service.get_user_by_uid(uid)
            
            if not user_data:
                logger.warning(f"Usuario no encontrado en Firestore: {uid}")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 401,
                        'message': 'Usuario no encontrado'
                    }
                }), 401
            
            # Validar que el usuario esté activo
            if not user_data.get('isActive', False):
                logger.warning(f"Usuario inactivo: {uid}")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 401,
                        'message': 'Usuario inactivo'
                    }
                }), 401
            
            # Inyectar información del usuario en el contexto global
            g.current_user = {
                'uid': uid,
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'role': user_data.get('role'),
                'businessId': user_data.get('businessId'),
                'branchId': user_data.get('branchId'),
                'permissions': user_data.get('permissions', [])
            }
            
            logger.info(f"Usuario autenticado: {uid} ({user_data.get('role')})")
            return f(*args, **kwargs)
            
        except ValueError as e:
            logger.warning(f"Error de autenticación: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 401,
                    'message': str(e)
                }
            }), 401
        except Exception as e:
            logger.error(f"Error en middleware de autenticación: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error interno de autenticación'
                }
            }), 500
    
    return decorated_function

def require_role(allowed_roles):
    """
    Decorador para requerir roles específicos
    
    Args:
        allowed_roles: Lista de roles permitidos
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Verificar que el usuario esté autenticado
                if not hasattr(g, 'current_user'):
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 401,
                            'message': 'Se requiere autenticación'
                        }
                    }), 401
                
                current_role = g.current_user.get('role')
                
                # Validar rol
                if current_role not in allowed_roles:
                    logger.warning(
                        f"Acceso denegado: rol {current_role} no en {allowed_roles}"
                    )
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 403,
                            'message': 'No tienes permisos para realizar esta acción'
                        }
                    }), 403
                
                logger.info(f"Acceso permitido: rol {current_role}")
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error en middleware de roles: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 500,
                        'message': 'Error interno de autorización'
                    }
                }), 500
        
        return decorated_function
    
    return decorator

def require_permission(permission):
    """
    Decorador para requerir permisos específicos
    
    Args:
        permission: Permiso requerido
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Verificar que el usuario esté autenticado
                if not hasattr(g, 'current_user'):
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 401,
                            'message': 'Se requiere autenticación'
                        }
                    }), 401
                
                current_role = g.current_user.get('role')
                current_permissions = g.current_user.get('permissions', [])
                
                # Super admin tiene todos los permisos
                if current_role == 'super_admin' or '*' in current_permissions:
                    return f(*args, **kwargs)
                
                # Validar permiso específico
                if permission not in current_permissions:
                    logger.warning(
                        f"Permiso denegado: {permission} no en {current_permissions}"
                    )
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 403,
                            'message': 'No tienes permisos para realizar esta acción'
                        }
                    }), 403
                
                logger.info(f"Permiso concedido: {permission}")
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error en middleware de permisos: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 500,
                        'message': 'Error interno de autorización'
                    }
                }), 500
        
        return decorated_function
    
    return decorator

def validate_business_access(target_business_id):
    """
    Decorador para validar acceso a un negocio específico
    
    Args:
        target_business_id: ID del negocio a validar
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                if not hasattr(g, 'current_user'):
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 401,
                            'message': 'Se requiere autenticación'
                        }
                    }), 401
                
                user_business_id = g.current_user.get('businessId')
                
                # Super admin puede acceder a todos (por ahora)
                if g.current_user.get('role') != 'super_admin':
                    if user_business_id != target_business_id:
                        logger.warning(
                            f"Acceso denegado al negocio {target_business_id}"
                        )
                        return jsonify({
                            'success': False,
                            'error': {
                                'code': 403,
                                'message': 'No tienes acceso a este negocio'
                            }
                        }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error validando acceso a negocio: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 500,
                        'message': 'Error interno de validación'
                    }
                }), 500
        
        return decorated_function
    
    return decorator

def validate_branch_access(target_branch_id):
    """
    Decorador para validar acceso a una sede específica
    
    Args:
        target_branch_id: ID de la sede a validar
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                if not hasattr(g, 'current_user'):
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 401,
                            'message': 'Se requiere autenticación'
                        }
                    }), 401
                
                current_role = g.current_user.get('role')
                user_branch_id = g.current_user.get('branchId')
                
                # Super admin puede acceder a todas las sedes
                if current_role != 'super_admin':
                    if user_branch_id != target_branch_id:
                        logger.warning(
                            f"Acceso denegado a la sede {target_branch_id}"
                        )
                        return jsonify({
                            'success': False,
                            'error': {
                                'code': 403,
                                'message': 'No tienes acceso a esta sede'
                            }
                        }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error validando acceso a sede: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 500,
                        'message': 'Error interno de validación'
                    }
                }), 500
        
        return decorated_function
    
    return decorator
