"""
Rutas de gestión de Cuentas de Pago Destino para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from models.payment_account import PaymentAccountCreateSchema, PaymentAccountUpdateSchema

logger = logging.getLogger(__name__)

payment_accounts_bp = Blueprint('payment_accounts', __name__, url_prefix='/api/payment-accounts')


@payment_accounts_bp.route('', methods=['GET', 'OPTIONS'])
@require_auth
def get_payment_accounts():
    """
    Lista cuentas de pago destino
    GET /api/payment-accounts?businessId=xxx&type=zelle&isActive=true
    """
    try:
        business_id = request.args.get('businessId') or g.current_user.get('businessId')
        acct_type = request.args.get('type')
        active_only = request.args.get('isActive', 'true').lower() == 'true'

        firebase_service = FirebaseService()
        filters = [{'field': 'businessId', 'operator': '==', 'value': business_id}]

        if active_only:
            filters.append({'field': 'isActive', 'operator': '==', 'value': True})

        if acct_type and acct_type in ['zelle', 'pago_movil', 'bank']:
            filters.append({'field': 'type', 'operator': '==', 'value': acct_type})

        accounts = firebase_service.query_firestore(
            'payment_accounts',
            filters=filters,
            order_by='type'
        )

        return jsonify({'success': True, 'data': accounts}), 200

    except Exception as e:
        logger.error(f"Error listando cuentas de pago: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@payment_accounts_bp.route('/<account_id>', methods=['GET', 'OPTIONS'])
@require_auth
def get_payment_account(account_id):
    """
    Obtiene una cuenta de pago por ID
    """
    try:
        firebase_service = FirebaseService()
        account = firebase_service.get_document('payment_accounts', account_id)

        if not account:
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Cuenta no encontrada'}
            }), 404

        user_business_id = g.current_user.get('businessId')
        if account.get('businessId') != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a esta cuenta'}
            }), 403

        return jsonify({'success': True, 'data': account}), 200

    except Exception as e:
        logger.error(f"Error obteniendo cuenta {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@payment_accounts_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin', 'branch_admin'])
def create_payment_account():
    """
    Crea una nueva cuenta de pago destino
    POST /api/payment-accounts
    {
        "type": "zelle",
        "identifier": "correo@ejemplo.com",
        "label": "Zelle principal",
        "businessId": "xxx",
        "description": "Cuenta de Zelle del gimnasio"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'Se requieren datos'}
            }), 400

        schema = PaymentAccountCreateSchema(data)
        account_data = schema.to_dict()

        user_business_id = g.current_user.get('businessId')
        acct_business_id = account_data.get('businessId')

        if acct_business_id != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a este negocio'}
            }), 403

        firebase_service = FirebaseService()
        created_account = firebase_service.create_document('payment_accounts', account_data)

        if created_account:
            logger.info(f"Cuenta de pago creada: {created_account.get('id')}")
            return jsonify({'success': True, 'data': created_account}), 201

        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error al crear cuenta'}
        }), 500

    except ValueError as e:
        errors = e.args[0].get('errors', ['Error de validación'])
        return jsonify({
            'success': False,
            'error': {'code': 400, 'message': '; '.join(errors)}
        }), 400
    except Exception as e:
        logger.error(f"Error creando cuenta de pago: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@payment_accounts_bp.route('/<account_id>', methods=['PUT', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin', 'branch_admin'])
def update_payment_account(account_id):
    """
    Actualiza una cuenta de pago existente
    PUT /api/payment-accounts/:id
    """
    try:
        firebase_service = FirebaseService()
        account = firebase_service.get_document('payment_accounts', account_id)

        if not account:
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Cuenta no encontrada'}
            }), 404

        user_business_id = g.current_user.get('businessId')
        if account.get('businessId') != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a esta cuenta'}
            }), 403

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'Se requieren datos'}
            }), 400

        schema = PaymentAccountUpdateSchema(data)
        update_data = schema.to_dict()

        success = firebase_service.update_document('payment_accounts', account_id, update_data)

        if success:
            logger.info(f"Cuenta de pago actualizada: {account_id}")
            return jsonify({
                'success': True,
                'data': {'id': account_id, **update_data}
            }), 200

        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error al actualizar cuenta'}
        }), 500

    except ValueError as e:
        errors = e.args[0].get('errors', ['Error de validación'])
        return jsonify({
            'success': False,
            'error': {'code': 400, 'message': '; '.join(errors)}
        }), 400
    except Exception as e:
        logger.error(f"Error actualizando cuenta {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@payment_accounts_bp.route('/<account_id>', methods=['DELETE', 'OPTIONS'])
@require_auth
@require_role(['super_admin'])
def delete_payment_account(account_id):
    """
    Elimina una cuenta de pago (soft delete)
    DELETE /api/payment-accounts/:id
    """
    try:
        firebase_service = FirebaseService()
        account = firebase_service.get_document('payment_accounts', account_id)

        if not account:
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Cuenta no encontrada'}
            }), 404

        user_business_id = g.current_user.get('businessId')
        if account.get('businessId') != user_business_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a esta cuenta'}
            }), 403

        success = firebase_service.update_document(
            'payment_accounts', account_id, {'isActive': False}
        )

        if success:
            logger.info(f"Cuenta de pago desactivada: {account_id}")
            return jsonify({'success': True, 'data': {'id': account_id}}), 200

        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error al eliminar cuenta'}
        }), 500

    except Exception as e:
        logger.error(f"Error eliminando cuenta {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500