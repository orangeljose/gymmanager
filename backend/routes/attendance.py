"""
Rutas de control de asistencia (check-in) de clientes para GymManager

Colección: `attendance`
Endpoints:
    POST   /api/attendance              - registrar check-in (idempotente por cliente/día)
    GET    /api/attendance              - listar check-ins (business[/branch] + fecha)
    GET    /api/attendance/client/<id>  - historial + stats de un cliente
    GET    /api/attendance/stats        - agregados hoy/semana/mes + series + top asistentes

Patrón: Firestore hace los filtros de igualdad/rango; Python ordena, pagina y
agrupa (mismo patrón que `clients.py`). El `date` es autoritativo del servidor en
la zona horaria del negocio (Config.TIMEZONE).
"""
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, request, jsonify, g

from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from config import Config
from utils.validators import validate_pagination, validate_date_format

logger = logging.getLogger(__name__)

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')

VALID_METHODS = ['manual', 'qr', 'biometric']
POST_ROLES = ['super_admin', 'admin', 'branch_admin', 'cashier']
READ_ROLES = ['super_admin', 'admin', 'branch_admin', 'cashier', 'trainer']

# Offset fijo de respaldo por si el entorno no tiene la base de datos IANA
# (paquete `tzdata`). Caracas no aplica DST (UTC-4 todo el año).
_TZ_FALLBACK_OFFSETS = {
    'America/Caracas': -4,
    'America/Bogota': -5,
    'America/Mexico_City': -6,
    'America/Lima': -5,
    'America/Santiago': -4,
    'America/Argentina/Buenos_Aires': -3,
    'Europe/Madrid': 1,
}


def _business_tz():
    """Devuelve la tzinfo del negocio, con respaldo de offset fijo si falta tzdata."""
    try:
        return ZoneInfo(Config.TIMEZONE)
    except Exception:
        offset = _TZ_FALLBACK_OFFSETS.get(Config.TIMEZONE, 0)
        return timezone(timedelta(hours=offset))


def _business_today():
    """Fecha de 'hoy' (YYYY-MM-DD) en la zona horaria del negocio — autoridad del servidor."""
    return datetime.now(_business_tz()).strftime('%Y-%m-%d')


def _index_error_response(exc):
    """
    Devuelve una respuesta 500 accionable si el error es por índice compuesto
    faltante en Firestore; en caso contrario devuelve None.

    Nota: `FirebaseService.query_firestore` actualmente captura y descarta los
    errores devolviendo []. Este helper queda como red de seguridad por si la
    capa de servicio propaga la excepción (FAILED_PRECONDITION).
    """
    message = str(exc).lower()
    if 'index' in message or 'failed_precondition' in message or 'failedprecondition' in message:
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': (
                    'Falta un índice compuesto de Firestore para esta consulta. '
                    'Créalo en la consola de Firebase (Firestore > Índices): '
                    'attendance (businessId ASC, date ASC) y '
                    '(businessId ASC, branchId ASC, date ASC).'
                )
            }
        }), 500
    return None


def _resolve_scope_filters(filters, date_filter=None):
    """
    Agrega los filtros de negocio/sede según el rol del usuario autenticado.

    - super_admin: businessId/branchId opcionales desde query params.
    - otros roles: businessId forzado del usuario; branchId forzado si está asignado.

    Returns:
        (branch_scoped: bool) True si se aplicó un filtro de sede por rol.
    """
    user_role = g.current_user.get('role')
    branch_scoped = False

    if user_role == 'super_admin':
        business_id = request.args.get('businessId')
        if business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': business_id})
    else:
        user_business_id = g.current_user.get('businessId')
        if user_business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})

    if date_filter is not None:
        filters.append(date_filter)

    if user_role != 'super_admin':
        user_branch_id = g.current_user.get('branchId')
        if user_branch_id:
            filters.append({'field': 'branchId', 'operator': '==', 'value': user_branch_id})
            branch_scoped = True
    else:
        branch_id = request.args.get('branchId')
        if branch_id:
            filters.append({'field': 'branchId', 'operator': '==', 'value': branch_id})
            branch_scoped = True

    return branch_scoped


@attendance_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(POST_ROLES)
def register_attendance():
    """
    Registra el check-in de un cliente.

    Request Body:
        { "clientId": "client-001", "method": "manual", "branchId": "sede-norte" }

    Respuestas:
        201 - check-in nuevo creado (alreadyCheckedIn=false)
        200 - ya existía un check-in hoy (alreadyCheckedIn=true)
        400 - body inválido o método inválido
        403 - cliente de otro negocio/sede
        404 - cliente inexistente o eliminado
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'Se requieren datos en el cuerpo del request'}
            }), 400

        client_id = (data.get('clientId') or '').strip()
        if not client_id:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'El campo clientId es requerido'}
            }), 400

        method = data.get('method') or 'manual'
        if method not in VALID_METHODS:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': f'Método debe ser uno de: {", ".join(VALID_METHODS)}'
                }
            }), 400

        firebase_service = FirebaseService()

        # 1) Cliente: existencia + scope (business/sede) — el doc del cliente es la fuente de verdad
        client = firebase_service.get_document('clients', client_id)
        if not client or client.get('isDeleted', False):
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Cliente no encontrado'}
            }), 404

        client_business_id = client.get('businessId')
        client_branch_id = client.get('branchId')
        user_role = g.current_user.get('role')
        user_business_id = g.current_user.get('businessId')
        user_branch_id = g.current_user.get('branchId')

        if client_business_id != user_business_id and user_role != 'super_admin':
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a este cliente'}
            }), 403

        if user_role != 'super_admin' and user_branch_id and client_branch_id != user_branch_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a este cliente'}
            }), 403

        # branchId autoritativo = el del cliente (no se permite spoofing desde el body)
        branch_id = client_branch_id or data.get('branchId')

        # 2) Idempotencia por id determinístico {clientId}_{date}
        date_str = _business_today()
        doc_id = f"{client_id}_{date_str}"

        existing = firebase_service.get_document('attendance', doc_id)
        if existing:
            existing['alreadyCheckedIn'] = True
            logger.info(f"Check-in repetido (ya registrado hoy): {doc_id}")
            return jsonify({'success': True, 'data': existing}), 200

        now_iso = datetime.now(timezone.utc).isoformat()
        record = {
            'id': doc_id,
            'clientId': client_id,
            'clientName': client.get('name'),
            'businessId': client_business_id,
            'branchId': branch_id,
            'date': date_str,
            'checkInAt': now_iso,
            'method': method,
            'registeredBy': g.current_user.get('uid'),
            'registeredByName': g.current_user.get('name'),
            'createdAt': now_iso,
        }

        # set_document inyecta SERVER_TIMESTAMP: usar copia para no romper la respuesta JSON
        created = firebase_service.set_document('attendance', doc_id, record.copy())
        if not created:
            return jsonify({
                'success': False,
                'error': {'code': 500, 'message': 'Error al registrar la asistencia'}
            }), 500

        logger.info(f"Check-in registrado: {doc_id}")
        return jsonify({
            'success': True,
            'data': {**record, 'alreadyCheckedIn': False}
        }), 201

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error registrando asistencia: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@attendance_bp.route('', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def get_attendance():
    """
    Lista los check-ins del negocio (y sede si aplica) para una fecha.

    Query Params: date (YYYY-MM-DD, default hoy), businessId (super_admin),
                  branchId, clientId, page, limit
    Response (200): { success, data[], meta{total,page,limit,pages}, summary{total,byMethod} }
    """
    try:
        date_str = request.args.get('date') or _business_today()
        date_errors = validate_date_format(date_str, 'date')
        if date_errors:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': '; '.join(date_errors)}
            }), 400

        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        pagination = validate_pagination(page, limit)

        filters = []
        _resolve_scope_filters(
            filters,
            date_filter={'field': 'date', 'operator': '==', 'value': date_str}
        )

        client_id = request.args.get('clientId')
        if client_id:
            filters.append({'field': 'clientId', 'operator': '==', 'value': client_id})

        firebase_service = FirebaseService()
        try:
            records = firebase_service.query_firestore('attendance', filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        # Orden DESC por checkInAt en Python (sin orderBy → sin índices DESC extra)
        records.sort(key=lambda r: r.get('checkInAt') or '', reverse=True)

        total = len(records)
        by_method = Counter(r.get('method', 'manual') for r in records)

        start_idx = pagination['offset']
        page_records = records[start_idx:start_idx + pagination['limit']]
        pages = (total + pagination['limit'] - 1) // pagination['limit'] if pagination['limit'] else 0

        return jsonify({
            'success': True,
            'data': page_records,
            'meta': {
                'total': total,
                'page': pagination['page'],
                'limit': pagination['limit'],
                'pages': pages,
            },
            'summary': {
                'total': total,
                'byMethod': dict(by_method),
            }
        }), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error listando asistencias: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@attendance_bp.route('/stats', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def get_attendance_stats():
    """
    Agregados de asistencia: hoy / semana (7d) / mes (30d) + series + top asistentes.

    UNA sola query acotada (rango 30 días) en Firestore; agrupación en Python.

    Query Params: date (default hoy), branchId, businessId (super_admin)
    Response (200): { success, data: AttendanceStats }
    """
    try:
        date_str = request.args.get('date') or _business_today()
        date_errors = validate_date_format(date_str, 'date')
        if date_errors:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': '; '.join(date_errors)}
            }), 400

        try:
            today_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': {'code': 400, 'message': 'La fecha debe tener formato YYYY-MM-DD'}
            }), 400

        start_month = today_dt - timedelta(days=29)
        start_week = today_dt - timedelta(days=6)
        start_month_str = start_month.isoformat()
        start_week_str = start_week.isoformat()

        filters = []
        _resolve_scope_filters(filters, date_filter=None)
        filters.append({'field': 'date', 'operator': '>=', 'value': start_month_str})
        filters.append({'field': 'date', 'operator': '<=', 'value': date_str})

        firebase_service = FirebaseService()
        try:
            rows = firebase_service.query_firestore('attendance', filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        today_count = 0
        week_count = 0
        month_count = 0
        daily_counts = Counter()
        attendee_counts = Counter()
        attendee_names = {}

        for row in rows:
            row_date = row.get('date') or ''
            if row_date:
                daily_counts[row_date] += 1
            if row_date == date_str:
                today_count += 1
            if start_week_str <= row_date <= date_str:
                week_count += 1
            if start_month_str <= row_date <= date_str:
                month_count += 1

            cid = row.get('clientId')
            if cid:
                attendee_counts[cid] += 1
                if row.get('clientName'):
                    attendee_names[cid] = row.get('clientName')

        series30 = [
            {'date': (today_dt - timedelta(days=i)).isoformat(),
             'count': daily_counts.get((today_dt - timedelta(days=i)).isoformat(), 0)}
            for i in range(29, -1, -1)
        ]
        series7 = series30[-7:]

        top_attendees = [
            {
                'clientId': cid,
                'clientName': attendee_names.get(cid, cid),
                'count': count,
            }
            for cid, count in attendee_counts.most_common(5)
        ]

        return jsonify({
            'success': True,
            'data': {
                'today': today_count,
                'week': week_count,
                'month': month_count,
                'series7': series7,
                'series30': series30,
                # alias de compatibilidad con el wording del spec
                'last7Days': series7,
                'topAttendees': top_attendees,
            }
        }), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error calculando stats de asistencia: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500


@attendance_bp.route('/client/<client_id>', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def get_client_attendance(client_id):
    """
    Historial de asistencia de un cliente + stats (total, mes actual, última visita).

    Response (200): { success, data[], stats{total, thisMonth, lastVisit} }
    """
    try:
        firebase_service = FirebaseService()

        client = firebase_service.get_document('clients', client_id)
        if not client or client.get('isDeleted', False):
            return jsonify({
                'success': False,
                'error': {'code': 404, 'message': 'Cliente no encontrado'}
            }), 404

        client_business_id = client.get('businessId')
        client_branch_id = client.get('branchId')
        user_role = g.current_user.get('role')
        user_business_id = g.current_user.get('businessId')
        user_branch_id = g.current_user.get('branchId')

        if client_business_id != user_business_id and user_role != 'super_admin':
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a este cliente'}
            }), 403

        if user_role != 'super_admin' and user_branch_id and client_branch_id != user_branch_id:
            return jsonify({
                'success': False,
                'error': {'code': 403, 'message': 'No tienes acceso a este cliente'}
            }), 403

        filters = [{'field': 'clientId', 'operator': '==', 'value': client_id}]
        if client_business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': client_business_id})

        try:
            history = firebase_service.query_firestore('attendance', filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        history.sort(key=lambda r: r.get('checkInAt') or '', reverse=True)

        current_month = _business_today()[:7]
        this_month = sum(1 for r in history if (r.get('date') or '').startswith(current_month))
        last_visit = history[0].get('checkInAt') if history else None

        return jsonify({
            'success': True,
            'data': history,
            'stats': {
                'total': len(history),
                'thisMonth': this_month,
                'lastVisit': last_visit,
            }
        }), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error obteniendo historial de asistencia de {client_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500
