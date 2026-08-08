"""
Rutas de gestión de sedes y negocios para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

branches_bp = Blueprint('branches', __name__, url_prefix='/api')

@branches_bp.route('/branches', methods=['GET', 'OPTIONS'])
@require_auth
def get_branches():
    """
    Lista sucursales del negocio seleccionado
    GET /api/branches?businessId=xxx
    """
    try:
        business_id = request.args.get('businessId')
        user_role = g.current_user.get('role')
        user_business_id = g.current_user.get('businessId')

        # super_admin puede pasar businessId por query, sino usa el suyo
        if not business_id and user_role != 'super_admin':
            business_id = user_business_id

        if not business_id:
            return jsonify({'success': True, 'data': []}), 200

        firebase_service = FirebaseService()
        branches = firebase_service.query_firestore('branches', filters=[
            {'field': 'businessId', 'operator': '==', 'value': business_id},
            {'field': 'isActive', 'operator': '==', 'value': True}
        ])

        return jsonify({'success': True, 'data': branches}), 200

    except Exception as e:
        logger.error(f"Error listando sucursales: {str(e)}")
        return jsonify({'success': False, 'error': {'code': 500, 'message': 'Error interno del servidor'}}), 500


@branches_bp.route('/branches', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin', 'branch_admin'])
def create_branch():
    """
    Crea una nueva sede
    
    Request Body:
    {
        "name": "Sede Sur",
        "address": "Calle Secundaria 456",
        "phone": "+1234567891",
        "businessId": "gimnasio-central"
    }
    
    Response (201):
    {
        "success": true,
        "data": {
            "id": "sede-sur",
            "name": "Sede Sur",
            "address": "Calle Secundaria 456",
            "phone": "+1234567891",
            "businessId": "gimnasio-central",
            "isActive": true,
            "createdAt": "2026-04-14T10:00:00Z"
        }
    }
    """
    try:
        # Obtener y validar datos
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Se requieren datos en el cuerpo del request'
                }
            }), 400
        
        # Validar campos requeridos
        required_fields = ['name', 'address', 'phone', 'businessId']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': f'Campos requeridos faltantes: {", ".join(missing_fields)}'
                }
            }), 400
        
        # Validar acceso al negocio
        business_id = data.get('businessId')
        user_business_id = g.current_user.get('businessId')
        user_role = g.current_user.get('role')
        
        if user_role != 'super_admin' and user_business_id != business_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'No tienes acceso a este negocio'
                }
            }), 403
        
        # Verificar que el negocio exista
        firebase_service = FirebaseService()
        business = firebase_service.get_document('businesses', business_id)
        if not business:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Negocio no encontrado'
                }
            }), 404
        
        # Preparar datos de la sede
        branch_data = {
            'name': data.get('name').strip(),
            'address': data.get('address').strip(),
            'phone': data.get('phone').strip(),
            'businessId': business_id,
            'isActive': True
        }
        
        # Para admin, asignarlo como manager
        if user_role == 'admin':
            branch_data['managerId'] = g.current_user.get('uid')
        
        # Crear sede
        created_branch = firebase_service.create_document('branches', branch_data)
        
        if created_branch:
            logger.info(f"Sede creada exitosamente: {created_branch.get('id')}")
            return jsonify({
                'success': True,
                'data': created_branch
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error al crear sede'
                }
}), 500


@branches_bp.route('/branches/<branch_id>', methods=['DELETE', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def delete_branch(branch_id):
    """Elimina una sucursal (soft delete)"""
    try:
        firebase_service = FirebaseService()
        branch = firebase_service.get_document('branches', branch_id)

        if not branch:
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Sucursal no encontrada'}
            }), 404

        user_role = g.current_user.get('role')
        user_business_id = g.current_user.get('businessId')

        if user_role != 'super_admin' and branch.get('businessId') != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a esta sucursal'}
            }), 403

        success = firebase_service.update_document('branches', branch_id, {'isActive': False})

        if success:
            logger.info(f"Sucursal desactivada: {branch_id}")
            return jsonify({'success': True, 'data': {'id': branch_id}}), 200

        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error al eliminar sucursal'}
        }), 500

    except Exception as e:
        logger.error(f"Error eliminando sucursal {branch_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500

    except Exception as e:
        logger.error(f"Error creando sede: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500


@branches_bp.route('/branches/<branch_id>', methods=['PUT', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin', 'branch_admin'])
def update_branch(branch_id):
    """
    Actualiza una sucursal
    PUT /api/branches/:id
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'Se requieren datos'}
            }), 400

        firebase_service = FirebaseService()
        branch = firebase_service.get_document('branches', branch_id)

        if not branch:
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Sucursal no encontrada'}
            }), 404

        # Verificar acceso
        user_role = g.current_user.get('role')
        user_business_id = g.current_user.get('businessId')

        if user_role != 'super_admin' and branch.get('businessId') != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a esta sucursal'}
            }), 403

        # Campos permitidos para actualizar
        update_data = {}
        if 'name' in data and data['name']:
            update_data['name'] = data['name'].strip()
        if 'address' in data:
            update_data['address'] = data['address'].strip() if data['address'] else ''
        if 'phone' in data:
            update_data['phone'] = data['phone'].strip() if data['phone'] else ''

        if not update_data:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'No hay datos para actualizar'}
            }), 400

        success = firebase_service.update_document('branches', branch_id, update_data)

        if success:
            logger.info(f"Sucursal actualizada: {branch_id}")
            return jsonify({
                'success': True,
                'data': {'id': branch_id, **update_data}
            }), 200

        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error al actualizar sucursal'}
        }), 500

    except Exception as e:
        logger.error(f"Error actualizando sucursal {branch_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500
