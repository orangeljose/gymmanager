"""
Rutas de gestión de pagos para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth, require_role, validate_branch_access
from services.firebase_service import FirebaseService
from services.payment_service import PaymentService
from models.payment import PaymentCreateSchema, PaymentSyncSchema
from utils.validators import validate_choice, validate_date_format

logger = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

@payments_bp.route('', methods=['POST'])
@require_auth
@require_role(['super_admin', 'branch_admin', 'cashier'])
def register_payment():
    """
    Registra un nuevo pago y actualiza automáticamente la membresía del cliente
    
    Request Body:
    {
        "clientId": "client-001",
        "amount": 35000,
        "method": "cash",
        "membershipPlanId": "plan-mensual",
        "branchId": "sede-norte",
        "methodDetails": {
            "cardLast4": null,
            "transactionId": null,
            "reference": "REF-12345"
        }
    }
    
    Response (201):
    {
        "success": true,
        "data": {
            "id": "payment-002",
            "receiptNumber": "P-20260414-002",
            "clientId": "client-001",
            "amount": 35000,
            "method": "cash",
            "startDate": "2026-04-14T00:00:00Z",
            "endDate": "2026-05-14T00:00:00Z",
            "registeredBy": "user-uid-123",
            "registeredByName": "Admin Principal",
            "createdAt": "2026-04-14T10:30:00Z"
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
        
        # Validar datos con el schema
        schema = PaymentCreateSchema(data)
        payment_data = schema.to_dict()
        
        # Validar método de pago
        method = payment_data.get('method')
        valid_methods = ['cash', 'card', 'transfer', 'other']
        if method not in valid_methods:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': f'Método de pago debe ser uno de: {", ".join(valid_methods)}'
                }
            }), 400
        
        # Validar acceso a la sede
        branch_id = payment_data.get('branchId')
        if g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            if branch_id != user_branch_id:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'No tienes acceso a esta sede'
                    }
                }), 403
        
        # Registrar pago usando el servicio
        payment_service = PaymentService()
        created_payment = payment_service.register_payment(payment_data, g.current_user)
        
        if created_payment:
            logger.info(f"Pago registrado exitosamente: {created_payment.get('receiptNumber')}")
            return jsonify({
                'success': True,
                'data': created_payment
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Error al registrar pago. Verifique los datos.'
                }
            }), 400
        
    except ValueError as e:
        logger.warning(f"Error de validación registrando pago: {str(e)}")
        errors = e.args[0].get('errors', ['Error de validación'])
        return jsonify({
            'success': False,
            'error': {
                'code': 400,
                'message': '; '.join(errors)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error registrando pago: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@payments_bp.route('/report', methods=['GET'])
@require_auth
@require_role(['super_admin', 'branch_admin'])
def get_payment_report():
    """
    Reporte de pagos con filtros
    
    Query Parameters:
        startDate: string (required) - Fecha inicio (YYYY-MM-DD)
        endDate: string (required) - Fecha fin (YYYY-MM-DD)
        branchId: string (optional) - Filtrar por sede
        method: string (optional) - cash, card, transfer, other
    
    Response (200):
    {
        "success": true,
        "data": {
            "summary": {
                "totalAmount": 245000,
                "totalPayments": 7,
                "averageAmount": 35000
            },
            "byMethod": {
                "cash": 140000,
                "card": 70000,
                "transfer": 35000
            },
            "payments": [...]
        }
    }
    """
    try:
        # Obtener parámetros de query
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        branch_id = request.args.get('branchId')
        method = request.args.get('method')
        
        # Validar parámetros requeridos
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'startDate y endDate son requeridos'
                }
            }), 400
        
        # Validar formato de fechas
        date_errors = []
        date_errors.extend(validate_date_format(start_date, 'startDate'))
        date_errors.extend(validate_date_format(end_date, 'endDate'))
        
        if date_errors:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': '; '.join(date_errors)
                }
            }), 400
        
        # Validar método de pago
        if method:
            valid_methods = ['cash', 'card', 'transfer', 'other']
            if method not in valid_methods:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 400,
                        'message': f'Método debe ser uno de: {", ".join(valid_methods)}'
                    }
                }), 400
        
        # Validar acceso a la sede (si no es super admin)
        if branch_id and g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            if branch_id != user_branch_id:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'No tienes acceso a esta sede'
                    }
                }), 403
        
        # Generar reporte usando el servicio
        payment_service = PaymentService()
        report_data = payment_service.get_payment_report(
            start_date, end_date, branch_id, method
        )
        
        if report_data:
            logger.info(f"Reporte generado: {report_data['summary']['totalPayments']} pagos")
            return jsonify({
                'success': True,
                'data': report_data
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error generando reporte'
                }
            }), 500
        
    except Exception as e:
        logger.error(f"Error generando reporte de pagos: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@payments_bp.route('/sync', methods=['POST'])
@require_auth
@require_role(['super_admin', 'branch_admin', 'cashier'])
def sync_offline_payments():
    """
    Sincroniza múltiples pagos registrados offline
    
    Request Body:
    {
        "payments": [
            {
                "clientId": "client-001",
                "amount": 35000,
                "method": "cash",
                "membershipPlanId": "plan-mensual",
                "branchId": "sede-norte",
                "registeredAt": "2026-04-14T09:00:00Z",
                "localId": "offline-001"
            },
            ...
        ]
    }
    
    Response (200):
    {
        "success": true,
        "data": {
            "synced": 2,
            "failed": 0,
            "results": [
                {
                    "localId": "offline-001",
                    "serverId": "payment-010",
                    "status": "success"
                },
                {
                    "localId": "offline-002",
                    "serverId": "payment-011",
                    "status": "success"
                }
            ]
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
        
        payments_list = data.get('payments', [])
        if not payments_list:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'La lista de pagos está vacía'
                }
            }), 400
        
        # Validar datos con el schema
        schema = PaymentSyncSchema(payments_list)
        validated_payments = schema.to_list()
        
        # Validar acceso a las sedes de los pagos
        if g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            for payment_data in validated_payments:
                branch_id = payment_data.get('branchId')
                if branch_id != user_branch_id:
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 403,
                            'message': f'No tienes acceso a la sede {branch_id}'
                        }
                    }), 403
        
        # Sincronizar pagos usando el servicio
        payment_service = PaymentService()
        sync_result = payment_service.sync_offline_payments(
            validated_payments, g.current_user
        )
        
        logger.info(f"Sincronización completada: {sync_result['synced']} exitosos, {sync_result['failed']} fallidos")
        
        return jsonify({
            'success': True,
            'data': sync_result
        }), 200
        
    except ValueError as e:
        logger.warning(f"Error de validación sincronizando pagos: {str(e)}")
        errors = e.args[0].get('errors', ['Error de validación'])
        return jsonify({
            'success': False,
            'error': {
                'code': 400,
                'message': '; '.join(errors)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error sincronizando pagos: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500
