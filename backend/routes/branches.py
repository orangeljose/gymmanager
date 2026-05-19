"""
Rutas de gestión de sedes y negocios para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

branches_bp = Blueprint('branches', __name__, url_prefix='/api')

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
        
    except Exception as e:
        logger.error(f"Error creando sede: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500
