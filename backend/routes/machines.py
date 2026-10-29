"""
Rutas de inventario de máquinas/equipos y seguimiento de mantenimiento.

Colecciones:
    - `machines`            - inventario de equipos por negocio/sede
    - `machine_maintenance` - bitácora de mantenimientos/reparaciones

Endpoints:
    GET    /api/machines                    - listar (scoped, filtros en Python, paginado)
    GET    /api/machines/summary            - resumen (total, byStatus, próximos, últimas reparaciones)
    GET    /api/machines/<id>               - ficha de una máquina
    POST   /api/machines                    - crear (admin+)
    PUT    /api/machines/<id>               - actualizar (admin+)
    DELETE /api/machines/<id>               - soft delete (admin+)
    GET    /api/machines/<id>/maintenance   - historial DESC paginado
    POST   /api/machines/<id>/maintenance   - registrar + transición de estado

Patrón: Firestore aplica SOLO la igualdad de `businessId` (índice automático de un
campo). Los filtros de `category`/`status`/`branchId`/`search` se resuelven en
Python (volumen 10-50 docs/negocio), evitando índices compuestos en `machines`.
Las transiciones de estado se calculan en línea con `update_document` (mismo
patrón que `attendance.py`; no hay servicio ni schema nuevo).
"""
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify, g

from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from utils.validators import validate_pagination, validate_date_format, clean_image_url

logger = logging.getLogger(__name__)

machines_bp = Blueprint('machines', __name__, url_prefix='/api/machines')

MACHINES_COLLECTION = 'machines'
MAINTENANCE_COLLECTION = 'machine_maintenance'

VALID_KINDS = ['machine', 'item']
VALID_CATEGORIES = ['cardio', 'strength', 'functional', 'free_weights', 'accessory', 'other']
# Subconjunto válido para `kind='item'` (pesas y accesorios): las categorías de
# máquina (cardio/strength/functional) no aplican físicamente a un accesorio.
ITEM_CATEGORIES = ['free_weights', 'accessory', 'other']
VALID_STATUSES = ['operational', 'maintenance', 'out_of_service']
VALID_MAINTENANCE_TYPES = ['preventive', 'repair']
VALID_MAINTENANCE_STATUSES = ['scheduled', 'in_progress', 'completed']
VALID_RESOLVED_STATUSES = ['operational', 'out_of_service']

WRITE_ROLES = ['super_admin', 'admin', 'branch_admin']
READ_ROLES = ['super_admin', 'admin', 'branch_admin', 'cashier', 'trainer']

# Intervalo por defecto entre mantenimientos preventivos.
PREVENTIVE_INTERVAL_DAYS = 90


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
                    'colección `machine_maintenance`: (businessId ASC, machineId ASC) '
                    'y (businessId ASC, date DESC).'
                )
            }
        }), 500
    return None


def _error(code, message):
    return jsonify({'success': False, 'error': {'code': code, 'message': message}}), code


def _is_active(machine):
    """
    Trata un documento legacy sin `isActive` como activo (filtrado defensivo).
    """
    return machine.get('isActive', True) is not False


def _kind(doc):
    """
    Normaliza el discriminador de equipamiento. Un documento legacy sin `kind`
    se trata como `machine` (compatibilidad hacia atrás).
    """
    return doc.get('kind') or 'machine'


def _valid_quantity(value):
    """`quantity` debe ser un entero >= 1 (bool excluido explícitamente)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _valid_weight(value):
    """`weightKg` debe ser un número >= 0 o null."""
    if value is None:
        return True
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def _scope_ids():
    """
    Devuelve (business_id, branch_id) que restringen la consulta del usuario.

    - super_admin: opcionales desde query params (puede ser None → cross-business).
    - otros roles: forzados del usuario autenticado (branchId puede ser None).
    """
    if g.current_user.get('role') == 'super_admin':
        return request.args.get('businessId'), request.args.get('branchId')
    return g.current_user.get('businessId'), g.current_user.get('branchId')


def _machine_scope_denied(machine):
    """
    Devuelve una respuesta 403 si la máquina está fuera del alcance del usuario,
    o None si tiene acceso.
    """
    role = g.current_user.get('role')
    if role == 'super_admin':
        return None

    user_business_id = g.current_user.get('businessId')
    user_branch_id = g.current_user.get('branchId')

    if machine.get('businessId') != user_business_id:
        return _error(403, 'No tienes acceso a esta máquina')

    if user_branch_id and machine.get('branchId') != user_branch_id:
        return _error(403, 'No tienes acceso a esta máquina')

    return None


def _fetch_active_machine(firebase_service, machine_id):
    """
    Devuelve (machine, None) o (None, response) con 404 si no existe/está borrada.
    """
    machine = firebase_service.get_document(MACHINES_COLLECTION, machine_id)
    if not machine or not _is_active(machine):
        return None, _error(404, 'Máquina no encontrada')
    return machine, None


def _add_days(date_str, days):
    """Suma `days` a una fecha YYYY-MM-DD y devuelve YYYY-MM-DD."""
    base = datetime.strptime(date_str, '%Y-%m-%d').date()
    return (base + timedelta(days=days)).isoformat()


def _today_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


# ============================================================================
# GET /api/machines
# ============================================================================

@machines_bp.route('', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def list_machines():
    """
    Lista las máquinas del negocio (y sede si aplica) con filtros y paginación.

    Query Params: category, status, search, branchId, businessId (super_admin),
                  page, limit
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
            machines = firebase_service.query_firestore(MACHINES_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        # Filtrado defensivo + filtros de negocio/sede en Python.
        category = (request.args.get('category') or '').strip()
        status = (request.args.get('status') or '').strip()
        kind = (request.args.get('kind') or '').strip()
        search = (request.args.get('search') or '').strip().lower()

        result = []
        for m in machines:
            if not _is_active(m):
                continue
            if branch_id and m.get('branchId') != branch_id:
                continue
            if category and m.get('category') != category:
                continue
            if status and m.get('status') != status:
                continue
            if kind and _kind(m) != kind:
                continue
            if search:
                haystack = ' '.join([
                    str(m.get('name') or ''),
                    str(m.get('brand') or ''),
                    str(m.get('model') or ''),
                ]).lower()
                if search not in haystack:
                    continue
            result.append(m)

        # Orden estable por nombre.
        result.sort(key=lambda m: (m.get('name') or '').lower())

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
        logger.error(f"Error listando máquinas: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/machines/summary
# ============================================================================

@machines_bp.route('/summary', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def machines_summary():
    """
    Resumen de inventario: total, conteo por estado, próximos mantenimientos
    (nextMaintenanceDate <= hoy + 7 días) y las últimas 5 actuaciones.

    Eficiencia: UNA query scoped a `machines` (igualdad businessId) para los
    conteos en Python; UNA query acotada (`businessId`, `date DESC`, limit 5) a
    `machine_maintenance` para las recientes.

    Response (200): { success, data:{total, byStatus, upcomingMaintenance, recentRepairs} }
    """
    try:
        business_id, branch_id = _scope_ids()

        machine_filters = []
        if business_id:
            machine_filters.append({'field': 'businessId', 'operator': '==', 'value': business_id})

        firebase_service = FirebaseService()
        try:
            machines = firebase_service.query_firestore(MACHINES_COLLECTION, filters=machine_filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        active_docs = [
            m for m in machines
            if _is_active(m) and (not branch_id or m.get('branchId') == branch_id)
        ]

        # Split por `kind` en Python sobre la MISMA query scoped a `machines`
        # (sin índice nuevo). `machine` conserva los statos; `item` va al bloque
        # aditivo `items`.
        active_machines = [m for m in active_docs if _kind(m) == 'machine']
        active_items = [m for m in active_docs if _kind(m) == 'item']

        by_status = {s: 0 for s in VALID_STATUSES}
        for m in active_machines:
            st = m.get('status') or 'operational'
            if st not in by_status:
                by_status[st] = 0
            by_status[st] += 1

        horizon = _add_days(_today_utc(), 7)
        upcoming = [
            m for m in active_machines
            if m.get('nextMaintenanceDate') and m.get('nextMaintenanceDate') <= horizon
        ]
        upcoming.sort(key=lambda m: m.get('nextMaintenanceDate') or '')

        items_summary = {
            'itemTypes': len(active_items),
            'totalUnits': sum(int(m.get('quantity') or 1) for m in active_items),
        }

        maintenance_filters = []
        if business_id:
            maintenance_filters.append({'field': 'businessId', 'operator': '==', 'value': business_id})

        try:
            recent = firebase_service.query_firestore(
                MAINTENANCE_COLLECTION,
                filters=maintenance_filters,
                order_by='date',
                direction='DESC',
                limit=5,
            )
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        if branch_id:
            recent = [r for r in recent if r.get('branchId') == branch_id]
        recent.sort(key=lambda r: r.get('date') or '', reverse=True)
        recent = recent[:5]

        return jsonify({
            'success': True,
            'data': {
                'total': len(active_machines),
                'byStatus': by_status,
                'upcomingMaintenance': upcoming,
                'recentRepairs': recent,
                'items': items_summary,
            }
        }), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error calculando resumen de máquinas: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/machines/<id>
# ============================================================================

@machines_bp.route('/<machine_id>', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def get_machine(machine_id):
    """Ficha de una máquina. 404 si no existe o está soft-deleted; 403 fuera de alcance."""
    try:
        firebase_service = FirebaseService()
        machine, not_found = _fetch_active_machine(firebase_service, machine_id)
        if not_found:
            return not_found

        denied = _machine_scope_denied(machine)
        if denied:
            return denied

        return jsonify({'success': True, 'data': machine}), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error obteniendo máquina {machine_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# POST /api/machines
# ============================================================================

@machines_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(WRITE_ROLES)
def create_machine():
    """
    Crea una máquina. Valida `name` no vacío, `category` permitida y `branchId`
    dentro del alcance. Defaults: status='operational', isActive=true.

    Response (201): { success, data:{...} }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return _error(400, 'Se requieren datos en el cuerpo del request')

        name = (data.get('name') or '').strip()
        if not name:
            return _error(400, 'El campo name es requerido')

        kind = (data.get('kind') or 'machine').strip()
        if kind not in VALID_KINDS:
            return _error(400, f'kind debe ser uno de: {", ".join(VALID_KINDS)}')

        # Campos específicos por tipo. Sólo el branch correspondiente se valida;
        # el path de máquina conserva byte-a-byte su comportamiento original.
        item_fields = {}
        category = ''
        status = 'operational'

        if kind == 'item':
            category = (data.get('category') or '').strip()
            if category not in ITEM_CATEGORIES:
                return _error(400, f'category de accesorio debe ser uno de: {", ".join(ITEM_CATEGORIES)}')

            quantity = data.get('quantity', 1)
            if not _valid_quantity(quantity):
                return _error(400, 'quantity debe ser un entero >= 1')

            weight_kg = data.get('weightKg')
            if not _valid_weight(weight_kg):
                return _error(400, 'weightKg debe ser un número >= 0 o null')

            purchase_date = data.get('purchaseDate')
            if purchase_date:
                errors = validate_date_format(purchase_date, 'purchaseDate')
                if errors:
                    return _error(400, '; '.join(errors))

            # Los accesorios no tienen mantenimiento ni estado editable.
            item_fields = {'quantity': quantity, 'weightKg': weight_kg}

        else:
            category = (data.get('category') or '').strip()
            if category not in VALID_CATEGORIES:
                return _error(400, f'category debe ser uno de: {", ".join(VALID_CATEGORIES)}')

            status = (data.get('status') or 'operational').strip()
            if status not in VALID_STATUSES:
                return _error(400, f'status debe ser uno de: {", ".join(VALID_STATUSES)}')

            for field in ('purchaseDate', 'warrantyUntil', 'nextMaintenanceDate'):
                value = data.get(field)
                if value:
                    errors = validate_date_format(value, field)
                    if errors:
                        return _error(400, '; '.join(errors))

        role = g.current_user.get('role')
        user_branch_id = g.current_user.get('branchId')
        branch_id = data.get('branchId')

        # Alcance de sede: un usuario acotado a sede solo crea en su sede.
        if role != 'super_admin' and user_branch_id and branch_id and branch_id != user_branch_id:
            return _error(403, 'No puedes crear máquinas en esta sede')
        if role != 'super_admin' and user_branch_id:
            branch_id = user_branch_id

        if role == 'super_admin':
            business_id = data.get('businessId') or request.args.get('businessId')
        else:
            business_id = g.current_user.get('businessId')
        if not business_id:
            return _error(400, 'Selecciona un negocio antes de continuar' if role == 'super_admin'
                          else 'Tu usuario no tiene un negocio asignado')

        try:
            image_url = clean_image_url(data.get('imageUrl'))
        except ValueError as exc:
            return _error(400, str(exc))

        now_iso = datetime.now(timezone.utc).isoformat()

        if kind == 'item':
            record = {
                'kind': 'item',
                'name': name,
                'imageUrl': image_url,
                'brand': None,
                'model': None,
                'category': category,
                'purchaseDate': data.get('purchaseDate'),
                'warrantyUntil': None,
                'businessId': business_id,
                'branchId': branch_id,
                'status': 'operational',
                'nextMaintenanceDate': None,
                'quantity': item_fields['quantity'],
                'weightKg': item_fields['weightKg'],
                'isActive': True,
                'registeredBy': g.current_user.get('uid'),
                'registeredByName': g.current_user.get('name'),
                'createdAt': now_iso,
            }
        else:
            record = {
                'kind': 'machine',
                'name': name,
                'imageUrl': image_url,
                'brand': data.get('brand'),
                'model': data.get('model'),
                'category': category,
                'purchaseDate': data.get('purchaseDate'),
                'warrantyUntil': data.get('warrantyUntil'),
                'businessId': business_id,
                'branchId': branch_id,
                'status': status,
                'nextMaintenanceDate': data.get('nextMaintenanceDate'),
                'isActive': True,
                'registeredBy': g.current_user.get('uid'),
                'registeredByName': g.current_user.get('name'),
                'createdAt': now_iso,
            }

        firebase_service = FirebaseService()
        created = firebase_service.create_document(MACHINES_COLLECTION, record)
        if not created:
            return _error(500, 'Error al crear la máquina')

        logger.info(f"Máquina creada: {created.get('id')}")
        return jsonify({'success': True, 'data': created}), 201

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error creando máquina: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# PUT /api/machines/<id>
# ============================================================================

@machines_bp.route('/<machine_id>', methods=['PUT', 'OPTIONS'])
@require_auth
@require_role(WRITE_ROLES)
def update_machine(machine_id):
    """Actualiza una máquina (incluye `status`). 404 si no existe/borrada; 403 fuera de alcance."""
    try:
        firebase_service = FirebaseService()
        machine, not_found = _fetch_active_machine(firebase_service, machine_id)
        if not_found:
            return not_found

        denied = _machine_scope_denied(machine)
        if denied:
            return denied

        data = request.get_json(silent=True)
        if not data:
            return _error(400, 'Se requieren datos en el cuerpo del request')

        update = {}

        if 'imageUrl' in data:
            try:
                update['imageUrl'] = clean_image_url(data.get('imageUrl'))
            except ValueError as exc:
                return _error(400, str(exc))

        if _kind(machine) == 'item':
            # Los accesorios sólo permiten editar name, category (set de ítems),
            # quantity, weightKg y purchaseDate. El status queda fijo en
            # 'operational' y no tienen mantenimiento.
            if 'name' in data:
                name = (data.get('name') or '').strip()
                if not name:
                    return _error(400, 'El campo name no puede estar vacío')
                update['name'] = name

            if 'category' in data:
                category = (data.get('category') or '').strip()
                if category not in ITEM_CATEGORIES:
                    return _error(400, f'category de accesorio debe ser uno de: {", ".join(ITEM_CATEGORIES)}')
                update['category'] = category

            if 'quantity' in data:
                quantity = data.get('quantity')
                if not _valid_quantity(quantity):
                    return _error(400, 'quantity debe ser un entero >= 1')
                update['quantity'] = quantity

            if 'weightKg' in data:
                weight_kg = data.get('weightKg')
                if not _valid_weight(weight_kg):
                    return _error(400, 'weightKg debe ser un número >= 0 o null')
                update['weightKg'] = weight_kg

            if 'purchaseDate' in data:
                value = data.get('purchaseDate')
                if value:
                    errors = validate_date_format(value, 'purchaseDate')
                    if errors:
                        return _error(400, '; '.join(errors))
                update['purchaseDate'] = value

        else:
            if 'name' in data:
                name = (data.get('name') or '').strip()
                if not name:
                    return _error(400, 'El campo name no puede estar vacío')
                update['name'] = name

            if 'category' in data:
                category = (data.get('category') or '').strip()
                if category not in VALID_CATEGORIES:
                    return _error(400, f'category debe ser uno de: {", ".join(VALID_CATEGORIES)}')
                update['category'] = category

            if 'status' in data:
                status = (data.get('status') or '').strip()
                if status not in VALID_STATUSES:
                    return _error(400, f'status debe ser uno de: {", ".join(VALID_STATUSES)}')
                update['status'] = status

            for field in ('brand', 'model', 'purchaseDate', 'warrantyUntil', 'nextMaintenanceDate'):
                if field in data:
                    value = data.get(field)
                    if value:
                        errors = validate_date_format(value, field)
                        if errors and field in ('purchaseDate', 'warrantyUntil', 'nextMaintenanceDate'):
                            return _error(400, '; '.join(errors))
                    update[field] = value

        if not update:
            return _error(400, 'No se enviaron campos válidos para actualizar')

        success = firebase_service.update_document(MACHINES_COLLECTION, machine_id, update)
        if not success:
            return _error(500, 'Error al actualizar la máquina')

        logger.info(f"Máquina actualizada: {machine_id}")
        return jsonify({'success': True, 'data': {'id': machine_id, **update}}), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error actualizando máquina {machine_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# DELETE /api/machines/<id>
# ============================================================================

@machines_bp.route('/<machine_id>', methods=['DELETE', 'OPTIONS'])
@require_auth
@require_role(WRITE_ROLES)
def delete_machine(machine_id):
    """Soft delete: marca isActive=false y conserva auditoría (deletedBy, deletedAt)."""
    try:
        firebase_service = FirebaseService()
        machine, not_found = _fetch_active_machine(firebase_service, machine_id)
        if not_found:
            return not_found

        denied = _machine_scope_denied(machine)
        if denied:
            return denied

        now_iso = datetime.now(timezone.utc).isoformat()
        success = firebase_service.update_document(MACHINES_COLLECTION, machine_id, {
            'isActive': False,
            'deletedBy': g.current_user.get('uid'),
            'deletedAt': now_iso,
        })
        if not success:
            return _error(500, 'Error al eliminar la máquina')

        logger.info(f"Máquina eliminada (soft delete): {machine_id}")
        return jsonify({'success': True, 'data': {'id': machine_id}}), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error eliminando máquina {machine_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/machines/<id>/maintenance
# ============================================================================

@machines_bp.route('/<machine_id>/maintenance', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def get_machine_maintenance(machine_id):
    """
    Historial de mantenimiento de una máquina, ordenado por `date` DESC y paginado.

    Query Params: page, limit
    Response (200): { success, data[], meta{total,page,limit,pages} }
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        pagination = validate_pagination(page, limit)

        firebase_service = FirebaseService()
        machine, not_found = _fetch_active_machine(firebase_service, machine_id)
        if not_found:
            return not_found

        denied = _machine_scope_denied(machine)
        if denied:
            return denied

        filters = [
            {'field': 'machineId', 'operator': '==', 'value': machine_id},
        ]
        if machine.get('businessId'):
            filters.append({'field': 'businessId', 'operator': '==', 'value': machine.get('businessId')})

        try:
            records = firebase_service.query_firestore(MAINTENANCE_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        records.sort(key=lambda r: r.get('date') or '', reverse=True)

        total = len(records)
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
            }
        }), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error obteniendo historial de {machine_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# POST /api/machines/<id>/maintenance
# ============================================================================

@machines_bp.route('/<machine_id>/maintenance', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(WRITE_ROLES)
def add_machine_maintenance(machine_id):
    """
    Registra un mantenimiento/reparación y aplica la transición de estado:

      - repair + completed     → machines.status = resolvedStatus (requerido)
      - preventive + completed → machines.nextMaintenanceDate = date + 90d
                                 (override explícito permitido); si la máquina
                                 estaba en 'maintenance' vuelve a 'operational'
      - scheduled / in_progress → machines.status = 'maintenance'

    Response (201): { success, data:{...record...} }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return _error(400, 'Se requieren datos en el cuerpo del request')

        mtype = (data.get('type') or '').strip()
        if mtype not in VALID_MAINTENANCE_TYPES:
            return _error(400, f'type debe ser uno de: {", ".join(VALID_MAINTENANCE_TYPES)}')

        status = (data.get('status') or 'completed').strip()
        if status not in VALID_MAINTENANCE_STATUSES:
            return _error(400, f'status debe ser uno de: {", ".join(VALID_MAINTENANCE_STATUSES)}')

        date_str = (data.get('date') or _today_utc()).strip()
        errors = validate_date_format(date_str, 'date')
        if errors:
            return _error(400, '; '.join(errors))

        resolved_status = data.get('resolvedStatus')
        if resolved_status is not None:
            resolved_status = str(resolved_status).strip()
            if resolved_status not in VALID_RESOLVED_STATUSES:
                return _error(400, f'resolvedStatus debe ser uno de: {", ".join(VALID_RESOLVED_STATUSES)}')

        # Una reparación COMPLETADA exige destino explícito del estado.
        if mtype == 'repair' and status == 'completed' and not resolved_status:
            return _error(400, 'Una reparación completada requiere resolvedStatus')

        cost_cents = data.get('costCents')
        if cost_cents is not None:
            if isinstance(cost_cents, bool) or not isinstance(cost_cents, int) or cost_cents < 0:
                return _error(400, 'costCents debe ser un entero de centavos (>= 0)')

        override_next = data.get('nextMaintenanceDate')
        if override_next:
            next_errors = validate_date_format(override_next, 'nextMaintenanceDate')
            if next_errors:
                return _error(400, '; '.join(next_errors))

        firebase_service = FirebaseService()
        machine, not_found = _fetch_active_machine(firebase_service, machine_id)
        if not_found:
            return not_found

        denied = _machine_scope_denied(machine)
        if denied:
            return denied

        # Los accesorios (kind='item') no tienen mantenimiento: rechazo antes de
        # cualquier escritura.
        if _kind(machine) == 'item':
            return _error(400, 'Los accesorios no tienen mantenimiento')

        now_iso = datetime.now(timezone.utc).isoformat()
        record = {
            'machineId': machine_id,
            'machineName': machine.get('name'),
            'type': mtype,
            'description': data.get('description'),
            'date': date_str,
            'costCents': cost_cents,
            'technician': data.get('technician'),
            'status': status,
            'resolvedStatus': resolved_status,
            'businessId': machine.get('businessId'),
            'branchId': machine.get('branchId'),
            'registeredBy': g.current_user.get('uid'),
            'registeredByName': g.current_user.get('name'),
            'createdAt': now_iso,
        }

        created = firebase_service.create_document(MAINTENANCE_COLLECTION, record)
        if not created:
            return _error(500, 'Error al registrar el mantenimiento')

        # --- Transición de estado de la máquina ---
        machine_update = {}
        if mtype == 'repair' and status == 'completed':
            machine_update['status'] = resolved_status
        elif mtype == 'preventive' and status == 'completed':
            machine_update['nextMaintenanceDate'] = override_next or _add_days(date_str, PREVENTIVE_INTERVAL_DAYS)
            if machine.get('status') == 'maintenance':
                machine_update['status'] = 'operational'
        elif status in ('scheduled', 'in_progress'):
            machine_update['status'] = 'maintenance'

        if machine_update:
            try:
                firebase_service.update_document(MACHINES_COLLECTION, machine_id, machine_update)
            except Exception as update_error:
                # El registro ya quedó creado; el fallo de transición no debe perderlo.
                logger.error(
                    f"No se pudo aplicar la transición de estado a {machine_id}: {update_error}"
                )

        logger.info(f"Mantenimiento registrado para {machine_id}: {created.get('id')}")
        return jsonify({'success': True, 'data': created}), 201

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error registrando mantenimiento de {machine_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')
