"""
Rutas de reportes para GymManager
"""
import logging
from math import ceil
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth, require_role, validate_branch_access
from services.firebase_service import FirebaseService
from services.membership_service import MembershipService
from utils.validators import validate_date_format

logger = logging.getLogger(__name__)

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('/solvency', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin', 'branch_admin', 'cashier'])
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
        from datetime import timezone, datetime, timedelta
        now = datetime.now(timezone.utc)
        
        # Obtener parámetros de query
        branch_id = request.args.get('branchId')
        days_overdue = int(request.args.get('daysOverdue', 0))
        user_role = g.current_user.get('role')
        
        # Validar acceso a la sede (si no es super admin)
        if branch_id and user_role != 'super_admin':
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
        
        # Filtro por negocio
        user_business_id = g.current_user.get('businessId')
        if user_role != 'super_admin' and user_business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})
        
        # Filtro por sede
        if user_role != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            if user_branch_id:
                filters.append({'field': 'branchId', 'operator': '==', 'value': user_branch_id})
        elif branch_id:
            filters.append({'field': 'branchId', 'operator': '==', 'value': branch_id})
        
        # Filtro de vencimiento
        if days_overdue == -999:
            # Todos los clientes, sin filtro de fecha
            pass
        elif days_overdue > 0:
            # Clientes vencidos hace mas de X dias
            cutoff_date = now - timedelta(days=days_overdue)
            filters.append({'field': 'membershipEnd', 'operator': '<', 'value': cutoff_date})
        elif days_overdue == 0:
            # Clientes vencidos (cualquier dia)
            filters.append({'field': 'membershipEnd', 'operator': '<', 'value': now})
        elif days_overdue < 0:
            # Proximos N dias (ej: -7 = proximos 7 dias)
            cutoff_date = now + timedelta(days=abs(days_overdue))
            filters.append({'field': 'membershipEnd', 'operator': '<=', 'value': cutoff_date})
            filters.append({'field': 'membershipEnd', 'operator': '>=', 'value': now})
        # days_overdue = -999: todos, sin filtro de fecha
        
        # Solo clientes activos
        filters.append({'field': 'isActive', 'operator': '==', 'value': True})
        
        # Ejecutar query
        firebase_service = FirebaseService()
        clients = firebase_service.query_firestore(
            'clients',
            filters=filters
            # order_by='membershipEnd',
            # direction='ASC'
        )
        
        # Enriquecer datos de los clientes
        enriched_clients = []
        for client in clients:
            client_id = client.get('id')
            
            # Calcular días restantes (negativo = vencido, positivo = por vencer)
            membership_end = client.get('membershipEnd')
            if membership_end:
                if isinstance(membership_end, str):
                    end_date = datetime.fromisoformat(membership_end.replace('Z', '+00:00'))
                elif hasattr(membership_end, 'to_datetime'):
                    end_date = membership_end.to_datetime()
                else:
                    end_date = membership_end
                
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
                
                days_remaining = ceil((end_date - now).total_seconds() / 86400)
            else:
                days_remaining = 0
            
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
            enriched_client['daysRemaining'] = days_remaining
            enriched_client['lastPaymentDate'] = last_payment.get('createdAt') if last_payment else None
            enriched_client['lastPaymentAmount'] = last_payment.get('amount') if last_payment else 0
            
            enriched_clients.append(enriched_client)
        
        # Ordenar: más urgentes primero (menos días restantes)
        enriched_clients.sort(key=lambda x: x['daysRemaining'])
        
        logger.info(f"Reporte de membresías: {len(enriched_clients)} clientes")
        
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
@require_auth
@require_role(['super_admin', 'admin', 'branch_admin'])
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
        user_role = g.current_user.get('role')
        if user_role != 'super_admin' and user_business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})
        
        # Filtro por sede
        if g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            filters.append({'field': 'branchId', 'operator': '==', 'value': user_branch_id})
        elif branch_id:
            filters.append({'field': 'branchId', 'operator': '==', 'value': branch_id})
        
        # Obtener pagos
        firebase_service = FirebaseService()
        logger.info(f"[DEBUG income] filters: {filters}")
        payments = firebase_service.query_firestore(
            'payments',
            filters=filters,
            order_by='createdAt',
            direction='ASC'
        )
        logger.info(f"[DEBUG income] found {len(payments)} payments")
        
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
@require_auth
@require_role(['super_admin', 'admin', 'branch_admin'])
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
        user_role2 = g.current_user.get('role')
        if user_role2 != 'super_admin' and user_business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})
        
        # Filtro por sede
        if user_role2 != 'super_admin':
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

@reports_bp.route('/dashboard', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin', 'branch_admin', 'cashier'])
def get_dashboard():
    """
    Dashboard agregado con métricas, gráfico de ingresos y top clientes

    Query Parameters:
        branchId: string (optional) - Filtrar por sede (solo super_admin)

    Response (200):
    {
        "success": true,
        "data": {
            "activeClients": 42,
            "todayIncome": 175000,
            "overdueClients": 5,
            "expiringThisWeek": 8,
            "incomeChart": [{"date": "2026-07-01", "amount": 35000}, ...],
             "topPayingClients": [{"clientId": "x", "clientName": "Juan", "paymentCount": 5}, ...],
            "retentionRate": 85.5
        }
    }
    """
    try:
        from datetime import datetime, timedelta
        from collections import defaultdict

        branch_id = request.args.get('branchId')
        firebase_service = FirebaseService()
        user_business_id = g.current_user.get('businessId')
        user_role = g.current_user.get('role')
        user_branch_id = g.current_user.get('branchId')
        now = datetime.now()

        # Resolver branch_id efectivo
        effective_branch_id = None
        if user_role != 'super_admin':
            effective_branch_id = user_branch_id
        elif branch_id:
            effective_branch_id = branch_id

        # --- Clients ---
        client_filters = [
            {'field': 'businessId', 'operator': '==', 'value': user_business_id}
        ]
        if effective_branch_id:
            client_filters.append({'field': 'branchId', 'operator': '==', 'value': effective_branch_id})

        all_clients = firebase_service.query_firestore('clients', filters=client_filters)

        active_clients = [c for c in all_clients if c.get('isActive', False)]
        active_count = len(active_clients)
        total_count = len(all_clients)

        overdue_count = 0
        expiring_count = 0
        for c in active_clients:
            membership_end = c.get('membershipEnd')
            if membership_end:
                if isinstance(membership_end, str):
                    membership_end_dt = datetime.fromisoformat(membership_end.replace('Z', '+00:00')).replace(tzinfo=None)
                else:
                    membership_end_dt = membership_end.replace(tzinfo=None) if hasattr(membership_end, 'replace') else membership_end

                if membership_end_dt < now:
                    overdue_count += 1
                elif membership_end_dt <= now + timedelta(days=7):
                    expiring_count += 1

        # --- Payments (last 30 days) ---
        thirty_days_ago = now - timedelta(days=30)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        payment_filters = [
            {'field': 'businessId', 'operator': '==', 'value': user_business_id},
            {'field': 'createdAt', 'operator': '>=', 'value': thirty_days_ago},
            {'field': 'createdAt', 'operator': '<=', 'value': now}
        ]
        if effective_branch_id:
            payment_filters.append({'field': 'branchId', 'operator': '==', 'value': effective_branch_id})

        payments = firebase_service.query_firestore(
            'payments',
            filters=payment_filters,
            order_by='createdAt',
            direction='DESC',
            limit=5000
        )

        # Today income
        today_income = 0
        for p in payments:
            created_at = p.get('createdAt')
            if created_at:
                if isinstance(created_at, str):
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00')).replace(tzinfo=None)
                elif hasattr(created_at, 'replace'):
                    created_dt = created_at.replace(tzinfo=None)
                else:
                    created_dt = created_at

                if created_dt >= today_start:
                    today_income += p.get('amount', 0)

        # Income chart (30 days grouped by date)
        daily_sums = defaultdict(int)
        for p in payments:
            created_at = p.get('createdAt')
            if created_at:
                if isinstance(created_at, str):
                    date_part = created_at.split('T')[0]
                elif hasattr(created_at, 'strftime'):
                    date_part = created_at.strftime('%Y-%m-%d')
                else:
                    date_part = str(created_at)[:10]
                daily_sums[date_part] += p.get('amount', 0)

        income_chart = []
        for i in range(30):
            day = (thirty_days_ago + timedelta(days=i)).strftime('%Y-%m-%d')
            income_chart.append({
                'date': day,
                'amount': daily_sums.get(day, 0)
            })

        # Top paying clients (top 5 by payment count)
        client_payment_counts = defaultdict(lambda: {'count': 0, 'clientName': ''})
        for p in payments:
            cid = p.get('clientId', '')
            if cid:
                client_payment_counts[cid]['count'] += 1
                client_payment_counts[cid]['clientName'] = p.get('clientName', 'Cliente')

        top_spenders = sorted(
            client_payment_counts.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]

        top_paying_clients = [
            {
                'clientId': cid,
                'clientName': data['clientName'],
                'paymentCount': data['count']
            }
            for cid, data in top_spenders
        ]

        # Retention rate
        retention_rate = round((active_count / total_count * 100), 1) if total_count > 0 else 0.0

        logger.info(f"Dashboard: {active_count} activos, {overdue_count} morosos, {expiring_count} próximos, ${today_income/100:.2f} hoy")

        return jsonify({
            'success': True,
            'data': {
                'activeClients': active_count,
                'todayIncome': today_income,
                'overdueClients': overdue_count,
                'expiringThisWeek': expiring_count,
                'incomeChart': income_chart,
                'topPayingClients': top_paying_clients,
                'retentionRate': retention_rate
            }
        }), 200

    except Exception as e:
        logger.error(f"Error generando dashboard: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500
