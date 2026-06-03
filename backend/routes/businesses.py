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
    """Lista negocios segun el rol."""
    try:
        user_role = g.current_user.get('role')
        user_business_id = g.current_user.get('businessId')
        firebase_service = FirebaseService()

        if user_role == 'super_admin':
            businesses = firebase_service.query_firestore('businesses')
        else:
            if not user_business_id:
                return jsonify({'success': True, 'data': []}), 200
            businesses = firebase_service.query_firestore(
                'businesses',
                filters=[{'field': 'id', 'operator': '==', 'value': user_business_id}]
            )

        logger.info(f"Listados {len(businesses)} negocios para {user_role}")
        return jsonify({'success': True, 'data': businesses}), 200

    except Exception as e:
        logger.error(f"Error listando negocios: {str(e)}")
        return jsonify({'success': False, 'error': {'code': 500, 'message': 'Error interno del servidor'}}), 500


@businesses_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def create_business():
    """Crea un nuevo negocio."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': {'code': 400, 'message': 'Se requieren datos en el cuerpo del request'}}), 400

        name = data.get('name', '').strip()

        if not name:
            return jsonify({'success': False, 'error': {'code': 400, 'message': 'El nombre del negocio es requerido'}}), 400

        firebase_service = FirebaseService()

        existing = firebase_service.query_firestore(
            'businesses',
            filters=[{'field': 'name', 'operator': '==', 'value': name}]
        )
        if existing:
            return jsonify({'success': False, 'error': {'code': 409, 'message': f'Ya existe un negocio con el nombre "{name}"'}}), 409

        user_uid = g.current_user.get('uid')
        user_role = g.current_user.get('role')

        business_data = {
            'name': name,
            'rubro': 'Gimnasio',
            'ownerId': user_uid,
            'createdBy': user_uid,
            'createdByRole': user_role
        }

        created_business = firebase_service.create_document('businesses', business_data)

        if created_business:
            logger.info(f"Negocio creado: {name} (ID: {created_business.get('id')})")
            return jsonify({'success': True, 'data': created_business}), 201

        return jsonify({'success': False, 'error': {'code': 500, 'message': 'Error al crear negocio'}}), 500

    except Exception as e:
        logger.error(f"Error creando negocio: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': {'code': 500, 'message': f'Error interno al crear negocio: {str(e)}'}}), 500


@businesses_bp.route('/<business_id>', methods=['DELETE', 'OPTIONS'])
@require_auth
@require_role(['super_admin'])
def delete_business(business_id):
    """Elimina un negocio (soft delete)."""
    try:
        firebase_service = FirebaseService()
        business = firebase_service.get_document('businesses', business_id)

        if not business:
            return jsonify({'success': False, 'error': {'code': 404, 'message': 'Negocio no encontrado'}}), 404

        success = firebase_service.update_document(
            'businesses', business_id, {'isActive': False}
        )

        if success:
            logger.info(f"Negocio desactivado: {business_id}")
            return jsonify({'success': True, 'data': {'id': business_id}}), 200

        return jsonify({'success': False, 'error': {'code': 500, 'message': 'Error al eliminar negocio'}}), 500

    except Exception as e:
        logger.error(f"Error eliminando negocio {business_id}: {str(e)}")
        return jsonify({'success': False, 'error': {'code': 500, 'message': 'Error interno del servidor'}}), 500


@businesses_bp.route('/<business_id>', methods=['PUT', 'OPTIONS'])
@require_auth
def update_business(business_id):
    """Actualiza un negocio (solo nombre por ahora)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': {'code': 400, 'message': 'Se requieren datos'}}), 400

        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': {'code': 400, 'message': 'El nombre es requerido'}}), 400

        firebase_service = FirebaseService()

        business = firebase_service.get_document('businesses', business_id)
        if not business:
            return jsonify({'success': False, 'error': {'code': 404, 'message': 'Negocio no encontrado'}}), 404

        user_role = g.current_user.get('role')
        user_business_id = g.current_user.get('businessId')

        if user_role != 'super_admin' and user_business_id != business_id:
            return jsonify({'success': False, 'error': {'code': 403, 'message': 'No tienes acceso a este negocio'}}), 403

        success = firebase_service.update_document('businesses', business_id, {'name': name})

        if success:
            logger.info(f"Negocio actualizado: {business_id}")
            return jsonify({'success': True, 'data': {'id': business_id, 'name': name}}), 200

        return jsonify({'success': False, 'error': {'code': 500, 'message': 'Error al actualizar negocio'}}), 500

    except Exception as e:
        logger.error(f"Error actualizando negocio {business_id}: {str(e)}")
        return jsonify({'success': False, 'error': {'code': 500, 'message': 'Error interno del servidor'}}), 500