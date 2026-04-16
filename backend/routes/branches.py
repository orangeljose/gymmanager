"""
Rutas de gestión de sedes y negocios para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from flask_cors import cross_origin
from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

branches_bp = Blueprint('branches', __name__, url_prefix='/api')

@branches_bp.route('/businesses', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
def get_businesses():
    """
    Lista todos los negocios a los que el usuario tiene acceso
    
    Response (200):
    {
        "success": true,
        "data": [
            {
                "id": "gimnasio-central",
                "name": "Mi Gimnasio Central",
                "rubro": "gym",
                "logo": "https://storage.googleapis.com/...",
                "createdAt": "2026-01-15T10:00:00Z"
            }
        ]
    }
    """
    try:
        # Obtener información del usuario actual
        user_business_id = g.current_user.get('businessId')
        user_role = g.current_user.get('role')
        
        # Super admin puede ver todos los negocios (por ahora solo el suyo)
        # En una versión futura, podría ver múltiples negocios
        if user_role == 'super_admin':
            # Por ahora, super admin solo ve su propio negocio
            filters = [{'field': 'ownerId', 'operator': '==', 'value': g.current_user.get('uid')}]
        else:
            # Otros roles solo ven el negocio asignado
            filters = [{'field': 'id', 'operator': '==', 'value': user_business_id}]
        
        # Obtener negocios
        firebase_service = FirebaseService()
        businesses = firebase_service.query_firestore('businesses', filters=filters)
        
        logger.info(f"Listados {len(businesses)} negocios para usuario {g.current_user.get('uid')}")
        
        return jsonify({
            'success': True,
            'data': businesses
        }), 200
        
    except Exception as e:
        logger.error(f"Error listando negocios: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@branches_bp.route('/branches/<business_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
def get_branches(business_id):
    """
    Lista las sedes de un negocio
    
    Response (200):
    {
        "success": true,
        "data": [
            {
                "id": "sede-norte",
                "name": "Sede Norte",
                "address": "Av. Principal 123",
                "phone": "+1234567890",
                "isActive": true
            }
        ]
    }
    """
    try:
        # Validar acceso al negocio
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
        
        # Obtener sedes del negocio
        branches = firebase_service.query_firestore(
            'branches',
            filters=[{'field': 'businessId', 'operator': '==', 'value': business_id}]
        )
        
        logger.info(f"Listadas {len(branches)} sedes para negocio {business_id}")
        
        return jsonify({
            'success': True,
            'data': branches
        }), 200
        
    except Exception as e:
        logger.error(f"Error listando sedes del negocio {business_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@branches_bp.route('/branches', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'branch_admin'])
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
        
        # Para branch_admin, asignarlo como manager
        if user_role == 'branch_admin':
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
