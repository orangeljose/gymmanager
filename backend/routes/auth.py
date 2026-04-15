"""
Rutas de autenticación para GymManager
"""
import logging
from flask import Blueprint, request, jsonify
from services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """
    Verifica un token de Firebase y retorna información del usuario
    
    Request Body:
    {
        "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
    }
    
    Response (200):
    {
        "success": true,
        "data": {
            "uid": "abc123def456",
            "email": "admin@gym.com",
            "name": "Admin Principal",
            "role": "super_admin",
            "businessId": "gimnasio-central"
        }
    }
    """
    try:
        # Obtener datos del request
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Se requieren datos en el cuerpo del request'
                }
            }), 400
        
        token = data.get('token')
        if not token:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'El campo "token" es requerido'
                }
            }), 400
        
        # Verificar token con Firebase
        firebase_service = FirebaseService()
        decoded_token = firebase_service.verify_token(token)
        
        # Obtener información completa del usuario desde Firestore
        uid = decoded_token.get('uid')
        user_data = firebase_service.get_user_by_uid(uid)
        
        if not user_data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Usuario no encontrado'
                }
            }), 404
        
        # Validar que el usuario esté activo
        if not user_data.get('isActive', False):
            return jsonify({
                'success': False,
                'error': {
                    'code': 401,
                    'message': 'Usuario inactivo'
                }
            }), 401
        
        # Preparar respuesta
        response_data = {
            'uid': user_data.get('id'),
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'role': user_data.get('role'),
            'businessId': user_data.get('businessId'),
            'branchId': user_data.get('branchId'),
            'permissions': user_data.get('permissions', [])
        }
        
        logger.info(f"Token verificado exitosamente para usuario: {uid}")
        
        return jsonify({
            'success': True,
            'data': response_data
        }), 200
        
    except ValueError as e:
        logger.warning(f"Error de verificación de token: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 401,
                'message': str(e)
            }
        }), 401
    except Exception as e:
        logger.error(f"Error en verificación de token: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500
