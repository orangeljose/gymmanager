"""
Rutas de gestión de negocios para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

businesses_bp = Blueprint('businesses', __name__, url_prefix='/api/businesses')


@businesses_bp.route('', methods=['GET', 'OPTIONS'])
@require_auth
def get_businesses():
    """
    Lista negocios según el rol:
    - super_admin: ve todos los negocios
    - admin y otros: ve solo su negocio

    Response (200):
    {
        "success": true,
        "data": [{ "id": "...", "name": "...", "rubro": "Gimnasio", ... }]
    }
    """
    try:
        user_role = g.current_user.get('role')
        user_business_id = g.current_user.get('businessId')
        firebase_service = FirebaseService()

        if user_role == 'super_admin':
            # Super admin ve todos los negocios
            businesses = firebase_service.query_firestore('businesses')
        else:
            # Los demás solo ven su propio negocio
            if not user_business_id:
                return jsonify({
                    'success': True,
                    'data': []
                }), 200
            businesses = firebase_service.query_firestore(
                'businesses',
                filters=[{'field': 'id', 'operator': '==', 'value': user_business_id}]
            )

        logger.info(f"Listados {len(businesses)} negocios para {user_role}")
        return jsonify({
            'success': True,
            'data': businesses
        }), 200

    except Exception as e:
        logger.error(f"Error listando negocios: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@businesses_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def create_business():
    """
    Crea un nuevo negocio.
    Solo super_admin y admin pueden crear negocios.

    Request Body:
    {
        "name": "Gimnasio Central",
        "rubro": "Gimnasio"
    }

    Response (201):
    {
        "success": true,
        "data": { "id": "...", "name": "Gimnasio Central", ... }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'Se requieren datos en el cuerpo del request'}
            }), 400

        name = data.get('name', '').strip()
        rubro = data.get('rubro', 'Gimnasio').strip()

        if not name:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'El nombre del negocio es requerido'}
            }), 400

        user_uid = g.current_user.get('uid')
        user_role = g.current_user.get('role')

        business_data = {
            'name': name,
            'rubro': rubro,
            'ownerId': user_uid,
            'createdBy': user_uid,
            'createdByRole': user_role
        }

        firebase_service = FirebaseService()
        created_business = firebase_service.create_document('businesses', business_data)

        if created_business:
            logger.info(f"Negocio creado: {name} (ID: {created_business.get('id')})")
            return jsonify({
                'success': True,
                'data': created_business
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': {'code': 500, 'message': 'Error al crear negocio'}
            }), 500

    except Exception as e:
        logger.error(f"Error creando negocio: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': f'Error interno al crear negocio: {str(e)}'}
        }), 500
