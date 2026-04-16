"""
Rutas de reportes para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from flask_cors import cross_origin
from middleware.auth_middleware import require_auth, require_role, validate_branch_access
from services.firebase_service import FirebaseService
from services.membership_service import MembershipService
from utils.validators import validate_date_format

logger = logging.getLogger(__name__)

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('/solvency', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'branch_admin'])
def get_solvency_report():
    """
    Lista clientes morosos (membresía vencida)
    
    Query Parameters:
        branchId: string (optional) - Filtrar por sede
        daysOverdue: integer (optional) - Días de vencimiento (default: 0)
    
    Response (200):
    {
        "success": true,
        "data": [
            {
                "id": "client-015",
                "name": "Carlos Ruiz",
                "phone": "+1234567899",
                "membershipPlanId": "plan-mensual",
                "membershipEnd": "2026-04-07T00:00:00Z",
                "daysOverdue": 7,
                "lastPaymentDate": "2026-03-07T10:00:00Z",
                "lastPaymentAmount": 35000
            }
        ],
        "meta": {
            "total": 12,
            "branchId": "sede-norte"
        }
    }
    """
    try:
        # Obtener parámetros de query
        branch_id = request.args.get('branchId')
        days_overdue = int(request.args.get('daysOverdue', 0))
        
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
        
        # Construir filtros
        filters = []
        
        # Filtro por negocio del usuario
        user_business_id = g.current_user.get('businessId')
        filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})
        
        # Filtro por sede
        if g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            filters.append({'field': 'branchId', 'operator': '==', 'value': user_branch_id})
        elif branch_id:
            filters.append({'field': 'branchId', 'operator': '==', 'value': branch_id})
        
        # Filtro por clientes vencidos
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days_overdue)
        filters.append({'field': 'membershipEnd', 'operator': '<', 'value': cutoff_date})
        
        # Solo clientes activos
        filters.append({'field': 'isActive', 'operator': '==', 'value': True})
        
        # Ejecutar query
        firebase_service = FirebaseService()
        overdue_clients = firebase_service.query_firestore(
            'clients',
            filters=filters,
            order_by='membershipEnd',
            direction='ASC'
        )
        
        # Enriquecer datos de los clientes
        enriched_clients = []
        for client in overdue_clients:
            client_id = client.get('id')
            
            # Calcular días de vencimiento
            membership_end_str = client.get('membershipEnd')
            if membership_end_str:
                if isinstance(membership_end_str, str):
                    membership_end = datetime.fromisoformat(membership_end_str.replace('Z', '+00:00'))
                else:
                    membership_end = membership_end_str
                
                days_over = (datetime.now() - membership_end).days
            else:
                days_over = 0
            
            # Obtener último pago
            payments = firebase_service.query_firestore(
                'payments',
                filters=[
                    {'field': 'clientId', 'operator': '==', 'value': client_id}
                ],
                order_by='createdAt',
                direction='DESC',
                limit=1
            )
            
            last_payment = payments[0] if payments else None
            
            enriched_client = client.copy()
            enriched_client['daysOverdue'] = days_over
            enriched_client['lastPaymentDate'] = last_payment.get('createdAt') if last_payment else None
            enriched_client['lastPaymentAmount'] = last_payment.get('amount') if last_payment else 0
            
            enriched_clients.append(enriched_client)
        
        # Ordenar por días de vencimiento (más vencidos primero)
        enriched_clients.sort(key=lambda x: x['daysOverdue'], reverse=True)
        
        logger.info(f"Reporte de morosos: {len(enriched_clients)} clientes")
        
        return jsonify({
            'success': True,
            'data': enriched_clients,
            'meta': {
                'total': len(enriched_clients),
                'branchId': branch_id or g.current_user.get('branchId')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error generando reporte de morosos: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@reports_bp.route('/income/daily', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'branch_admin'])
def get_daily_income_report():
    """
    Ingresos diarios en un rango de fechas
    
    Query Parameters:
        startDate: string (required) - YYYY-MM-DD
        endDate: string (required) - YYYY-MM-DD
        branchId: string (optional) - Filtrar por sede
    
    Response (200):
    {
        "success": true,
        "data": {
            "totalPeriod": 525000,
            "daily": [
                {
                    "date": "2026-04-01",
                    "amount": 105000,
                    "paymentsCount": 3
                },
                {
                    "date": "2026-04-02",
                    "amount": 70000,
                    "paymentsCount": 2
                }
            ]
        }
    }
    """
    try:
        # Obtener parámetros de query
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        branch_id = request.args.get('branchId')
        
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
        
        # Construir filtros
        filters = [
            {'field': 'createdAt', 'operator': '>=', 'value': start_date},
            {'field': 'createdAt', 'operator': '<=', 'value': end_date + 'T23:59:59'}
        ]
        
        # Filtro por negocio del usuario
        user_business_id = g.current_user.get('businessId')
        filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})
        
        # Filtro por sede
        if g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            filters.append({'field': 'branchId', 'operator': '==', 'value': user_branch_id})
        elif branch_id:
            filters.append({'field': 'branchId', 'operator': '==', 'value': branch_id})
        
        # Obtener pagos
        firebase_service = FirebaseService()
        payments = firebase_service.query_firestore(
            'payments',
            filters=filters,
            order_by='createdAt',
            direction='ASC'
        )
        
        # Agrupar por día
        from collections import defaultdict
        daily_data = defaultdict(lambda: {'amount': 0, 'count': 0})
        
        total_period = 0
        for payment in payments:
            # Extraer fecha sin hora
            created_at = payment.get('createdAt', '')
            if isinstance(created_at, str):
                date_part = created_at.split('T')[0]
            else:
                date_part = created_at.strftime('%Y-%m-%d') if created_at else ''
            
            amount = payment.get('amount', 0)
            
            daily_data[date_part]['amount'] += amount
            daily_data[date_part]['count'] += 1
            total_period += amount
        
        # Convertir a lista ordenada
        daily_list = []
        for date in sorted(daily_data.keys()):
            daily_list.append({
                'date': date,
                'amount': daily_data[date]['amount'],
                'paymentsCount': daily_data[date]['count']
            })
        
        logger.info(f"Reporte de ingresos diarios: {len(daily_list)} días, total ${total_period/100:.2f}")
        
        return jsonify({
            'success': True,
            'data': {
                'totalPeriod': total_period,
                'daily': daily_list
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error generando reporte de ingresos diarios: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@reports_bp.route('/income/by-method', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'branch_admin'])
def get_income_by_method_report():
    """
    Ingresos agrupados por método de pago
    
    Query Parameters:
        startDate: string (optional) - YYYY-MM-DD
        endDate: string (optional) - YYYY-MM-DD
        branchId: string (optional) - Filtrar por sede
    
    Response (200):
    {
        "success": true,
        "data": {
            "cash": {
                "amount": 245000,
                "percentage": 46.7,
                "count": 7
            },
            "card": {
                "amount": 175000,
                "percentage": 33.3,
                "count": 5
            },
            "transfer": {
                "amount": 105000,
                "percentage": 20.0,
                "count": 3
            }
        }
    }
    """
    try:
        # Obtener parámetros de query
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        branch_id = request.args.get('branchId')
        
        # Validar formato de fechas si se proporcionan
        date_errors = []
        if start_date:
            date_errors.extend(validate_date_format(start_date, 'startDate'))
        if end_date:
            date_errors.extend(validate_date_format(end_date, 'endDate'))
        
        if date_errors:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': '; '.join(date_errors)
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
        
        # Construir filtros
        filters = []
        
        # Filtro por negocio del usuario
        user_business_id = g.current_user.get('businessId')
        filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})
        
        # Filtro por sede
        if g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            filters.append({'field': 'branchId', 'operator': '==', 'value': user_branch_id})
        elif branch_id:
            filters.append({'field': 'branchId', 'operator': '==', 'value': branch_id})
        
        # Filtro por rango de fechas
        if start_date:
            filters.append({'field': 'createdAt', 'operator': '>=', 'value': start_date})
        if end_date:
            filters.append({'field': 'createdAt', 'operator': '<=', 'value': end_date + 'T23:59:59'})
        
        # Obtener pagos
        firebase_service = FirebaseService()
        payments = firebase_service.query_firestore(
            'payments',
            filters=filters,
            order_by='createdAt',
            direction='DESC'
        )
        
        # Agrupar por método
        from collections import defaultdict
        method_data = defaultdict(lambda: {'amount': 0, 'count': 0})
        
        total_amount = 0
        for payment in payments:
            method = payment.get('method', 'other')
            amount = payment.get('amount', 0)
            
            method_data[method]['amount'] += amount
            method_data[method]['count'] += 1
            total_amount += amount
        
        # Calcular porcentajes
        result = {}
        for method, data in method_data.items():
            percentage = (data['amount'] / total_amount * 100) if total_amount > 0 else 0
            result[method] = {
                'amount': data['amount'],
                'percentage': round(percentage, 1),
                'count': data['count']
            }
        
        logger.info(f"Reporte de ingresos por método: {len(result)} métodos")
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error generando reporte de ingresos por método: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500
