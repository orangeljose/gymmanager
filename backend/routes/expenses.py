"""
Rutas de Egresos (gastos del negocio).

Colección:
    - `expenses` - gastos por categoría, scoped por negocio/sede

Endpoints (TODOS admin+ = super_admin | admin | branch_admin):
    GET    /api/expenses            - listar (scoped, filtros en Python, paginado)
    GET    /api/expenses/summary    - resumen (hoy / 7d / 30d + byCategory)
    POST   /api/expenses            - crear
    PUT    /api/expenses/<id>       - actualizar
    DELETE /api/expenses/<id>       - soft delete + auditoría

Patrón: copia fiel de `routes/machines.py`. Firestore aplica SOLO la igualdad de
`businessId` (índice automático de un campo). Los filtros de `branchId`/`category`
/rango de fechas/`search` y la agregación del resumen se resuelven en Python
(volumen 10-50 docs/negocio), evitando índices compuestos en `expenses`.

Datos financieros ⇒ todos los endpoints exigen rol admin+ (`ADMIN_ROLES`);
`cashier`/`trainer` reciben 403. Phase 1 es SOLO egresos: los ingresos siguen en
`payments` (membresías) y en las ventas futuras de la Fase 2.
"""
import logging
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify, g

from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from models.payment import PaymentModel
from utils.validators import validate_pagination, validate_date_format

logger = logging.getLogger(__name__)

expenses_bp = Blueprint('expenses', __name__, url_prefix='/api/expenses')

EXPENSES_COLLECTION = 'expenses'

EXPENSE_CATEGORIES = ['payroll', 'supplies', 'services', 'rent', 'maintenance', 'other']
ADMIN_ROLES = ['super_admin', 'admin', 'branch_admin']

# Métodos de pago reutilizados del modelo de pagos (fuente única de verdad).
VALID_METHODS = PaymentModel.VALID_METHODS


# ============================================================================
# HELPERS
# ============================================================================

def _index_error_response(exc):
    """
    Devuelve una respuesta 500 accionable si el error es por índice compuesto
    faltante en Firestore; en caso contrario devuelve None.
    """
    message = str(exc).lower()
    if 'index' in message or 'failed_precondition' in message or 'failedprecondition' in message:
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': (
                    'Falta un índice compuesto de Firestore para esta consulta. '
                    'Créalo en la consola de Firebase (Firestore > Índices) en la '
                    'colección `expenses`: (businessId ASC, date ASC).'
                )
            }
        }), 500
    return None


def _error(code, message):
    return jsonify({'success': False, 'error': {'code': code, 'message': message}}), code


def _is_active(expense):
    """
    Un egreso es visible si no fue marcado como borrado (`isDeleted`).
    Los documentos legacy sin el campo se tratan como activos.
    """
    return expense.get('isDeleted') is not True


def _valid_amount(value):
    """`amountCents` debe ser un entero > 0 (bool excluido explícitamente)."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _scope_ids():
    """
    Devuelve (business_id, branch_id) que restringen la consulta del usuario.

    - super_admin: opcionales desde query params (puede ser None → cross-business).
    - otros roles: forzados del usuario autenticado (branchId puede ser None).
    """
    if g.current_user.get('role') == 'super_admin':
        return request.args.get('businessId'), request.args.get('branchId')
    return g.current_user.get('businessId'), g.current_user.get('branchId')


def _expense_scope_denied(expense):
    """
    Devuelve una respuesta 403 si el egreso está fuera del alcance del usuario,
    o None si tiene acceso.
    """
    role = g.current_user.get('role')
    if role == 'super_admin':
        return None

    user_business_id = g.current_user.get('businessId')
    user_branch_id = g.current_user.get('branchId')

    if expense.get('businessId') != user_business_id:
        return _error(403, 'No tienes acceso a este egreso')

    if user_branch_id and expense.get('branchId') != user_branch_id:
        return _error(403, 'No tienes acceso a este egreso')

    return None


def _fetch_active_expense(firebase_service, expense_id):
    """
    Devuelve (expense, None) o (None, response) con 404 si no existe/está borrado.
    """
    expense = firebase_service.get_document(EXPENSES_COLLECTION, expense_id)
    if not expense or not _is_active(expense):
        return None, _error(404, 'Egreso no encontrado')
    return expense, None


def _today_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _days_ago_utc(days):
    return (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()


# ============================================================================
# GET /api/expenses
# ============================================================================

@expenses_bp.route('', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(ADMIN_ROLES)
def list_expenses():
    """
    Lista los egresos del negocio (y sede si aplica) con filtros y paginación.

    Query Params: category, startDate, endDate, search, branchId,
                  businessId (super_admin), page, limit
    Response (200): { success, data[], meta{total,page,limit,pages} }
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        pagination = validate_pagination(page, limit)

        business_id, branch_id = _scope_ids()

        filters = []
        if business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': business_id})

        firebase_service = FirebaseService()
        try:
            expenses = firebase_service.query_firestore(EXPENSES_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        # Filtrado defensivo + filtros de negocio/sede/fecha en Python.
        category = (request.args.get('category') or '').strip()
        start_date = (request.args.get('startDate') or '').strip()
        end_date = (request.args.get('endDate') or '').strip()
        search = (request.args.get('search') or '').strip().lower()

        result = []
        for e in expenses:
            if not _is_active(e):
                continue
            if branch_id and e.get('branchId') != branch_id:
                continue
            if category and e.get('category') != category:
                continue
            e_date = e.get('date') or ''
            if start_date and e_date < start_date:
                continue
            if end_date and e_date > end_date:
                continue
            if search and search not in str(e.get('description') or '').lower():
                continue
            result.append(e)

        # Orden por fecha DESC (más recientes primero).
        result.sort(key=lambda e: e.get('date') or '', reverse=True)

        total = len(result)
        start_idx = pagination['offset']
        page_records = result[start_idx:start_idx + pagination['limit']]
        pages = (total + pagination['limit'] - 1) // pagination['limit'] if pagination['limit'] else 0

        return jsonify({
            'success': True,
            'data': page_records,
            'meta': {
                'total': total,
                'page': pagination['page'],
                'limit': pagination['limit'],
                'pages': pages,
            }
        }), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error listando egresos: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/expenses/summary
# ============================================================================

@expenses_bp.route('/summary', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(ADMIN_ROLES)
def expenses_summary():
    """
    Resumen de egresos: total de hoy, últimos 7 días (rolling) y últimos 30 días
    (rolling), más el desglose por categoría.

    Eficiencia: UNA query scoped a `expenses` (igualdad businessId) y toda la
    agrupación en Python. No hay contadores diarios (a diferencia de asistencia).
    `byCategory` agrega TODO el histórico no borrado dentro del alcance.

    Response (200): { success, data:{today, week, month, byCategory} }
    """
    try:
        business_id, branch_id = _scope_ids()

        filters = []
        if business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': business_id})

        firebase_service = FirebaseService()
        try:
            expenses = firebase_service.query_firestore(EXPENSES_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        active = [
            e for e in expenses
            if _is_active(e) and (not branch_id or e.get('branchId') == branch_id)
        ]

        today = _today_utc()
        week_start = _days_ago_utc(6)   # rolling 7d (incluye hoy)
        month_start = _days_ago_utc(29)  # rolling 30d (incluye hoy)

        totals = {'today': 0, 'week': 0, 'month': 0}
        by_category = {c: 0 for c in EXPENSE_CATEGORIES}

        for e in active:
            amount = e.get('amountCents') or 0
            e_date = e.get('date') or ''

            if e_date == today:
                totals['today'] += amount
            if e_date >= week_start:
                totals['week'] += amount
            if e_date >= month_start:
                totals['month'] += amount

            cat = e.get('category')
            if cat in by_category:
                by_category[cat] += amount

        return jsonify({
            'success': True,
            'data': {
                'today': totals['today'],
                'week': totals['week'],
                'month': totals['month'],
                'byCategory': by_category,
            }
        }), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error calculando resumen de egresos: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# POST /api/expenses
# ============================================================================

@expenses_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(ADMIN_ROLES)
def create_expense():
    """
    Crea un egreso. Valida `category` permitida, `amountCents` entero > 0 y
    `date` en formato YYYY-MM-DD. `description` es opcional.

    Response (201): { success, data:{...} }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return _error(400, 'Se requieren datos en el cuerpo del request')

        category = (data.get('category') or '').strip()
        if category not in EXPENSE_CATEGORIES:
            return _error(400, f'category debe ser uno de: {", ".join(EXPENSE_CATEGORIES)}')

        amount_cents = data.get('amountCents')
        if not _valid_amount(amount_cents):
            return _error(400, 'amountCents debe ser un entero de centavos mayor que 0')

        date_str = (data.get('date') or '').strip()
        errors = validate_date_format(date_str, 'date')
        if errors:
            return _error(400, '; '.join(errors))

        description = data.get('description')
        if description is not None:
            description = str(description).strip() or None

        method = str(data.get('method') or 'cash').strip() or 'cash'
        if method not in VALID_METHODS:
            return _error(400, f'method debe ser uno de: {", ".join(VALID_METHODS)}')

        payment_account_id = data.get('paymentAccountId')
        if payment_account_id is not None:
            payment_account_id = str(payment_account_id).strip() or None

        role = g.current_user.get('role')
        user_branch_id = g.current_user.get('branchId')
        branch_id = data.get('branchId')

        # Alcance de sede: un usuario acotado a sede solo crea en su sede.
        if role != 'super_admin' and user_branch_id and branch_id and branch_id != user_branch_id:
            return _error(403, 'No puedes registrar egresos en esta sede')
        if role != 'super_admin' and user_branch_id:
            branch_id = user_branch_id

        if role == 'super_admin':
            business_id = data.get('businessId') or request.args.get('businessId')
        else:
            business_id = g.current_user.get('businessId')

        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            'category': category,
            'amountCents': amount_cents,
            'description': description,
            'date': date_str,
            'method': method,
            'paymentAccountId': payment_account_id,
            'businessId': business_id,
            'branchId': branch_id,
            'registeredBy': g.current_user.get('uid'),
            'registeredByName': g.current_user.get('name'),
            'createdAt': now_iso,
            'isDeleted': False,
        }

        firebase_service = FirebaseService()
        created = firebase_service.create_document(EXPENSES_COLLECTION, record)
        if not created:
            return _error(500, 'Error al crear el egreso')

        logger.info(f"Egreso creado: {created.get('id')}")
        return jsonify({'success': True, 'data': created}), 201

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error creando egreso: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# PUT /api/expenses/<id>
# ============================================================================

@expenses_bp.route('/<expense_id>', methods=['PUT', 'OPTIONS'])
@require_auth
@require_role(ADMIN_ROLES)
def update_expense(expense_id):
    """Actualiza un egreso. 404 si no existe/borrado; 403 fuera de alcance."""
    try:
        firebase_service = FirebaseService()
        expense, not_found = _fetch_active_expense(firebase_service, expense_id)
        if not_found:
            return not_found

        denied = _expense_scope_denied(expense)
        if denied:
            return denied

        data = request.get_json(silent=True)
        if not data:
            return _error(400, 'Se requieren datos en el cuerpo del request')

        update = {}

        if 'category' in data:
            category = (data.get('category') or '').strip()
            if category not in EXPENSE_CATEGORIES:
                return _error(400, f'category debe ser uno de: {", ".join(EXPENSE_CATEGORIES)}')
            update['category'] = category

        if 'amountCents' in data:
            amount_cents = data.get('amountCents')
            if not _valid_amount(amount_cents):
                return _error(400, 'amountCents debe ser un entero de centavos mayor que 0')
            update['amountCents'] = amount_cents

        if 'date' in data:
            date_str = (data.get('date') or '').strip()
            errors = validate_date_format(date_str, 'date')
            if errors:
                return _error(400, '; '.join(errors))
            update['date'] = date_str

        if 'description' in data:
            description = data.get('description')
            update['description'] = str(description).strip() or None if description is not None else None

        if 'method' in data:
            method = str(data.get('method') or '').strip()
            if method not in VALID_METHODS:
                return _error(400, f'method debe ser uno de: {", ".join(VALID_METHODS)}')
            update['method'] = method

        if 'paymentAccountId' in data:
            account_id = data.get('paymentAccountId')
            update['paymentAccountId'] = str(account_id).strip() or None if account_id is not None else None

        if not update:
            return _error(400, 'No se enviaron campos válidos para actualizar')

        success = firebase_service.update_document(EXPENSES_COLLECTION, expense_id, update)
        if not success:
            return _error(500, 'Error al actualizar el egreso')

        logger.info(f"Egreso actualizado: {expense_id}")
        return jsonify({'success': True, 'data': {'id': expense_id, **update}}), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error actualizando egreso {expense_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# DELETE /api/expenses/<id>
# ============================================================================

@expenses_bp.route('/<expense_id>', methods=['DELETE', 'OPTIONS'])
@require_auth
@require_role(ADMIN_ROLES)
def delete_expense(expense_id):
    """Soft delete: marca isDeleted=true y conserva auditoría (deletedBy, deletedAt)."""
    try:
        firebase_service = FirebaseService()
        expense, not_found = _fetch_active_expense(firebase_service, expense_id)
        if not_found:
            return not_found

        denied = _expense_scope_denied(expense)
        if denied:
            return denied

        now_iso = datetime.now(timezone.utc).isoformat()
        success = firebase_service.update_document(EXPENSES_COLLECTION, expense_id, {
            'isDeleted': True,
            'deletedBy': g.current_user.get('uid'),
            'deletedAt': now_iso,
        })
        if not success:
            return _error(500, 'Error al eliminar el egreso')

        logger.info(f"Egreso eliminado (soft delete): {expense_id}")
        return jsonify({'success': True, 'data': {'id': expense_id}}), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error eliminando egreso {expense_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')
