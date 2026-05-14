"""
Rutas de gestión de Planes de Membresía para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from flask_cors import cross_origin
from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from models.plan import PlanCreateSchema, PlanUpdateSchema

logger = logging.getLogger(__name__)

plans_bp = Blueprint('plans', __name__, url_prefix='/api/plans')


def _get_plan_filters(business_id: str, active_only: bool = False):
    """Construye filtros comunes para queries de planes"""
    filters = [{'field': 'businessId', 'operator': '==', 'value': business_id}]
    if active_only:
        filters.append({'field': 'isActive', 'operator': '==', 'value': True})
    return filters


@plans_bp.route('', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'],
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
def get_plans():
    """
    Lista planes de membresía del negocio actual
    GET /api/plans?businessId=xxx&isActive=true
    """
    try:
        business_id = request.args.get('businessId') or g.current_user.get('businessId')
        active_only = request.args.get('isActive', 'false').lower() == 'true'

        firebase_service = FirebaseService()
        filters = _get_plan_filters(business_id, active_only)

        plans = firebase_service.query_firestore(
            'membership_plans',
            filters=filters,
            order_by='price',
            direction='ASC'
        )

        return jsonify({
            'success': True,
            'data': plans
        }), 200

    except Exception as e:
        logger.error(f"Error listando planes: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@plans_bp.route('/<plan_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'],
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
def get_plan(plan_id):
    """
    Obtiene un plan por ID
    """
    try:
        firebase_service = FirebaseService()
        plan = firebase_service.get_document('membership_plans', plan_id)

        if not plan:
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Plan no encontrado'}
            }), 404

        user_business_id = g.current_user.get('businessId')
        if plan.get('businessId') != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a este plan'}
            }), 403

        return jsonify({'success': True, 'data': plan}), 200

    except Exception as e:
        logger.error(f"Error obteniendo plan {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@plans_bp.route('', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'],
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'branch_admin'])
def create_plan():
    """
    Crea un nuevo plan de membresía
    POST /api/plans
    {
        "name": "Mensual",
        "price": 35000,
        "durationDays": 30,
        "businessId": "xxx",
        "description": "Acceso por 30 días",
        "benefits": ["Acceso total", "Clases grupales"]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'Se requieren datos'}
            }), 400

        schema = PlanCreateSchema(data)
        plan_data = schema.to_dict()

        user_business_id = g.current_user.get('businessId')
        plan_business_id = plan_data.get('businessId')

        if plan_business_id != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a este negocio'}
            }), 403

        firebase_service = FirebaseService()
        created_plan = firebase_service.create_document('membership_plans', plan_data)

        if created_plan:
            logger.info(f"Plan creado: {created_plan.get('id')}")
            return jsonify({'success': True, 'data': created_plan}), 201

        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error al crear plan'}
        }), 500

    except ValueError as e:
        errors = e.args[0].get('errors', ['Error de validación'])
        return jsonify({
            'success': False,
            'error': {'code': 400, 'message': '; '.join(errors)}
        }), 400
    except Exception as e:
        logger.error(f"Error creando plan: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@plans_bp.route('/<plan_id>', methods=['PUT', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'],
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['PUT', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'branch_admin'])
def update_plan(plan_id):
    """
    Actualiza un plan existente
    PUT /api/plans/:id
    """
    try:
        firebase_service = FirebaseService()
        plan = firebase_service.get_document('membership_plans', plan_id)

        if not plan:
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Plan no encontrado'}
            }), 404

        user_business_id = g.current_user.get('businessId')
        if plan.get('businessId') != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a este plan'}
            }), 403

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'Se requieren datos'}
            }), 400

        schema = PlanUpdateSchema(data)
        update_data = schema.to_dict()

        success = firebase_service.update_document('membership_plans', plan_id, update_data)

        if success:
            logger.info(f"Plan actualizado: {plan_id}")
            return jsonify({
                'success': True,
                'data': {'id': plan_id, **update_data}
            }), 200

        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error al actualizar plan'}
        }), 500

    except ValueError as e:
        errors = e.args[0].get('errors', ['Error de validación'])
        return jsonify({
            'success': False,
            'error': {'code': 400, 'message': '; '.join(errors)}
        }), 400
    except Exception as e:
        logger.error(f"Error actualizando plan {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@plans_bp.route('/<plan_id>', methods=['DELETE', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'],
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['DELETE', 'OPTIONS'])
@require_auth
@require_role(['super_admin'])
def delete_plan(plan_id):
    """
    Elimina un plan (soft delete: lo marca como inactivo)
    DELETE /api/plans/:id
    """
    try:
        firebase_service = FirebaseService()
        plan = firebase_service.get_document('membership_plans', plan_id)

        if not plan:
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Plan no encontrado'}
            }), 404

        user_business_id = g.current_user.get('businessId')
        if plan.get('businessId') != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a este plan'}
            }), 403

        success = firebase_service.update_document(
            'membership_plans', plan_id, {'isActive': False}
        )

        if success:
            logger.info(f"Plan desactivado: {plan_id}")
            return jsonify({'success': True, 'data': {'id': plan_id}}), 200

        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error al eliminar plan'}
        }), 500

    except Exception as e:
        logger.error(f"Error eliminando plan {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500