"""
Rutas de gestión de usuarios para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from models.user import UserModel

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__, url_prefix='/api')

@users_bp.route('/users', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def get_users():
    """
    Lista todos los usuarios del negocio
    Solo super_admin puede listar usuarios

    Query params:
        - isActive (optional): filtrar por estado activo/inactivo

    Response (200):
    {
        "success": true,
        "data": [
            {
                "id": "user-uid-123",
                "email": "user@example.com",
                "name": "Juan Pérez",
                "role": "cashier",
                "branchId": "branch-123",
                "businessId": "business-123",
                "isActive": true,
                "permissions": ["read_clients", "write_payments"],
                "createdAt": "2026-01-15T10:00:00Z"
            }
        ]
    }
    """
    try:
        user_business_id = g.current_user.get('businessId')
        user_role = g.current_user.get('role')
        user_branch_id = g.current_user.get('branchId')

        # Jerarquía de roles para ver usuarios:
        # super_admin > admin > branch_admin > cashier/trainer
        ROLE_HIERARCHY = {
            'super_admin': 4,
            'admin': 3,
            'branch_admin': 2,
            'cashier': 1,
            'trainer': 1
        }

        user_level = ROLE_HIERARCHY.get(user_role, 0)

        # Cashier y trainer no pueden ver usuarios
        if user_level <= 1:
            return jsonify({
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'No tienes permisos para ver usuarios'
                }
            }), 403

        # Construir filtros base
        filters = []

        # Super admin ve todos los negocios, pero no ve super_admins
        if user_role == 'super_admin':
            # Puede filtrar por businessId si lo pasa
            business_id = request.args.get('businessId')
            if business_id:
                filters.append({'field': 'businessId', 'operator': '==', 'value': business_id})
        elif user_role == 'admin':
            # Admin ve solo empleados de su negocio
            filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})
        else:
            # branch_admin ve solo empleados de su sede
            filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})
            if user_branch_id:
                filters.append({'field': 'branchId', 'operator': '==', 'value': user_branch_id})

        # Filtro opcional de isActive
        is_active_filter = request.args.get('isActive')
        if is_active_filter is not None:
            filters.append({
                'field': 'isActive',
                'operator': '==',
                'value': is_active_filter.lower() == 'true'
            })

        logger.info(f"[DEBUG get_users] role={user_role}, businessId={user_business_id}, branchId={user_branch_id}")
        logger.info(f"[DEBUG get_users] businessId from query: {request.args.get('businessId')}")
        logger.info(f"[DEBUG get_users] filters: {filters}")

        firebase_service = FirebaseService()
        users = firebase_service.query_firestore('users', filters=filters)

        logger.info(f"[DEBUG get_users] raw users count: {len(users)}")

        # Filtrar por rol: no puede ver roles de nivel superior o igual
        # Primero determinamos qué roles puede ver este usuario
        ROLES_CAN_SEE = {
            'super_admin': ['admin', 'branch_admin', 'cashier', 'trainer'],  # ve todos menos super_admin
            'admin': ['admin', 'branch_admin', 'cashier', 'trainer'],  # ve admins del negocio y subordinados
            'branch_admin': ['cashier', 'trainer']  # solo ve subordinados
        }

        can_see_roles = ROLES_CAN_SEE.get(user_role, [])
        users = [u for u in users if u.get('role') in can_see_roles]

        logger.info(f"[DEBUG get_users] filtered users count: {len(users)}, can_see_roles: {can_see_roles}")

        logger.info(f"Listados {len(users)} usuarios para negocio {user_business_id}")

        return jsonify({
            'success': True,
            'data': users
        }), 200

    except Exception as e:
        logger.error(f"Error listando usuarios: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@users_bp.route('/users/<user_id>', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def get_user(user_id):
    """
    Obtiene un usuario específico por ID

    Response (200):
    {
        "success": true,
        "data": {
            "id": "user-uid-123",
            "email": "user@example.com",
            "name": "Juan Pérez",
            "role": "cashier",
            "branchId": "branch-123",
            "businessId": "business-123",
            "isActive": true,
            "permissions": ["read_clients", "write_payments"],
            "createdAt": "2026-01-15T10:00:00Z"
        }
    }
    """
    try:
        user_role = g.current_user.get('role')

        if user_role != 'super_admin':
            return jsonify({
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'No tienes permisos para ver usuarios'
                }
            }), 403

        firebase_service = FirebaseService()
        user_data = firebase_service.get_document('users', user_id)

        if not user_data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Usuario no encontrado'
                }
            }), 404

        return jsonify({
            'success': True,
            'data': user_data
        }), 200

    except Exception as e:
        logger.error(f"Error obteniendo usuario {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@users_bp.route('/users', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def create_user():
    """
    Crea un nuevo usuario en Firestore
    Nota: El usuario debe existir primero en Firebase Auth

    Request Body:
    {
        "email": "user@example.com",
        "name": "Juan Pérez",
        "role": "cashier",
        "branchId": "branch-123" (opcional, null para super_admin)
    }

    Response (201):
    {
        "success": true,
        "data": {
            "id": "new-user-uid",
            "email": "user@example.com",
            "name": "Juan Pérez",
            "role": "cashier",
            "branchId": "branch-123",
            "businessId": "business-123",
            "isActive": true,
            "permissions": ["read_clients", "write_payments"],
            "createdAt": "2026-04-14T10:00:00Z"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Se requieren datos en el cuerpo del request'
                }
            }), 400

        required_fields = ['email', 'name', 'role']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]

        if missing_fields:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': f'Campos requeridos faltantes: {", ".join(missing_fields)}'
                }
            }), 400

        role = data.get('role')
        if not UserModel.validate_role(role):
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': f'Rol inválido: {role}. Roles válidos: {", ".join(UserModel.VALID_ROLES)}'
                }
            }), 400

        user_business_id = g.current_user.get('businessId')
        user_role = g.current_user.get('role')

        firebase_service = FirebaseService()

        permissions = UserModel.get_permissions(role)

        # Determinar el businessId del nuevo usuario
        # Super_admin puede especificar businessId en el request (del selector)
        # Admin/branch_admin usan su propio businessId
        if user_role == 'super_admin' and data.get('businessId'):
            new_user_business_id = data.get('businessId')
        elif user_role != 'super_admin':
            new_user_business_id = user_business_id
        else:
            # super_admin sin businessId en request - error
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'businessId es requerido para crear usuarios'
                }
            }), 400

        user_data = {
            'email': data.get('email').strip().lower(),
            'name': data.get('name').strip(),
            'role': role,
            'businessId': new_user_business_id,
            'branchId': data.get('branchId') or None,
            'isActive': True,
            'permissions': permissions
        }

        created_user = firebase_service.create_document('users', user_data)

        if created_user:
            logger.info(f"Usuario creado exitosamente: {created_user.get('id')}")
            return jsonify({
                'success': True,
                'data': created_user
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error al crear usuario'
                }
            }), 500

    except Exception as e:
        logger.error(f"Error creando usuario: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@users_bp.route('/users/<user_id>', methods=['PUT', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def update_user(user_id):
    """
    Actualiza un usuario existente

    Request Body (todos opcionales):
    {
        "name": "Juan Pérez Updated",
        "role": "admin",
        "branchId": "branch-456",
        "isActive": false
    }

    Response (200):
    {
        "success": true,
        "data": {
            "id": "user-uid-123",
            "email": "user@example.com",
            "name": "Juan Pérez Updated",
            "role": "admin",
            ...
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Se requieren datos en el cuerpo del request'
                }
            }), 400

        firebase_service = FirebaseService()

        existing_user = firebase_service.get_document('users', user_id)
        if not existing_user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Usuario no encontrado'
                }
            }), 404

        update_data = {}

        if 'name' in data and data['name']:
            update_data['name'] = data['name'].strip()

        if 'role' in data and data['role']:
            if not UserModel.validate_role(data['role']):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 400,
                        'message': f'Rol inválido: {data["role"]}'
                    }
                }), 400
            update_data['role'] = data['role']
            update_data['permissions'] = UserModel.get_permissions(data['role'])

        if 'branchId' in data:
            update_data['branchId'] = data['branchId'] or None

        if 'isActive' in data and isinstance(data['isActive'], bool):
            update_data['isActive'] = data['isActive']

        updated_user = firebase_service.update_document('users', user_id, update_data)

        if updated_user:
            logger.info(f"Usuario actualizado: {user_id}")
            return jsonify({
                'success': True,
                'data': updated_user
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error al actualizar usuario'
                }
            }), 500

    except Exception as e:
        logger.error(f"Error actualizando usuario {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@users_bp.route('/users/<user_id>', methods=['DELETE', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def delete_user(user_id):
    """
    Desactiva un usuario (soft delete - no se elimina de Firestore)

    Response (200):
    {
        "success": true,
        "data": {
            "id": "user-uid-123",
            "message": "Usuario desactivado correctamente"
        }
    }
    """
    try:
        firebase_service = FirebaseService()

        existing_user = firebase_service.get_document('users', user_id)
        if not existing_user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Usuario no encontrado'
                }
            }), 404

        updated_user = firebase_service.update_document('users', user_id, {'isActive': False})

        if updated_user:
            logger.info(f"Usuario desactivado: {user_id}")
            return jsonify({
                'success': True,
                'data': {
                    'id': user_id,
                    'message': 'Usuario desactivado correctamente'
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error al desactivar usuario'
                }
            }), 500

    except Exception as e:
        logger.error(f"Error desactivando usuario {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500