"""
Rutas de Productos e Inventario (Fase 2 — Productos, Stock y Movimientos).

Colecciones:
    - `products`          - catálogo de productos vendibles (stock, costo, precio)
    - `product_movements` - libro append-only de compras/ventas que ajusta stock

Endpoints:
    GET    /api/products                - listar (TODOS los roles; filtros en Python, paginado)
    GET    /api/products/summary        - resumen (total, valor de stock, bajo/agotado)
    GET    /api/products/<id>           - detalle (TODOS los roles)
    POST   /api/products                - crear (admin+)
    PUT    /api/products/<id>           - actualizar (admin+)
    DELETE /api/products/<id>           - soft delete + auditoría (admin+)
    GET    /api/products/<id>/movements - historial de movimientos (TODOS los roles)
    POST   /api/products/<id>/movement  - registrar compra ("Reponer", admin+)

Patrón: copia fiel de `routes/expenses.py`. Firestore aplica SOLO la igualdad de
`businessId` (índice automático de un campo); los filtros de `branchId`/`category`
/`lowStock`/`search` y la agregación del resumen se resuelven en Python
(volumen 10-50 docs/negocio), evitando índices compuestos en `products`.

Roles: `products` es lectura para TODOS los roles; las escrituras de catálogo
exigen admin+ (`ADMIN_ROLES`). `POST /movement` registra SOLO compras (`purchase`,
admin+) y usa `@require_role`. Las ventas NO son movimientos: se registran vía
`POST /api/sales` (ver `routes/sales.py`).

IMPORTANTE (anti-doble-conteo): una compra es dinero que sale, pero NUNCA crea ni
muta un documento de `expenses`. Compras y egresos son fuentes separadas.

Los movimientos son INMUTABLES: no existen endpoints de edición/borrado.
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g

from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from models.payment import PaymentModel
from utils.validators import validate_pagination, validate_date_format, clean_image_url

logger = logging.getLogger(__name__)

products_bp = Blueprint('products', __name__, url_prefix='/api/products')

PRODUCTS_COLLECTION = 'products'
MOVEMENTS_COLLECTION = 'product_movements'
SALES_COLLECTION = 'sales'

PRODUCT_CATEGORIES = ['supplement', 'drink', 'apparel', 'accessory', 'other']
MOVEMENT_TYPES = ['purchase']

ADMIN_ROLES = ['super_admin', 'admin', 'branch_admin']
READ_ROLES = ['super_admin', 'admin', 'branch_admin', 'cashier', 'trainer']

# Métodos de pago reutilizados del modelo de pagos (fuente única de verdad).
VALID_METHODS = PaymentModel.VALID_METHODS

# Compras de mercancía (egresos de dinero): mismos 4 métodos que el POS.
PURCHASE_METHODS = ['zelle', 'cash', 'pago_movil', 'binance']
# Estos métodos exigen una cuenta destino registrada.
ACCOUNT_REQUIRED_METHODS = {'zelle', 'pago_movil', 'binance'}

DEFAULT_LOW_STOCK_THRESHOLD = 5


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
                    'colección `product_movements`: (businessId ASC, date ASC).'
                )
            }
        }), 500
    return None


def _error(code, message):
    return jsonify({'success': False, 'error': {'code': code, 'message': message}}), code


def _is_active_product(product):
    """
    Un producto es visible si no fue marcado como borrado (`isActive:false`).
    Los documentos legacy sin el campo se tratan como activos.
    """
    return product.get('isActive', True) is not False


def _valid_int(value, minimum):
    """True si `value` es un entero (no bool) >= `minimum`."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _threshold(product):
    """Umbral de stock bajo; default 5 si falta o es inválido."""
    value = product.get('lowStockThreshold')
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return DEFAULT_LOW_STOCK_THRESHOLD


def _scope_ids():
    """
    Devuelve (business_id, branch_id) que restringen la consulta del usuario.

    - super_admin: opcionales desde query params (puede ser None → cross-business).
    - otros roles: forzados del usuario autenticado (branchId puede ser None).
    """
    if g.current_user.get('role') == 'super_admin':
        return request.args.get('businessId'), request.args.get('branchId')
    return g.current_user.get('businessId'), g.current_user.get('branchId')


def _product_scope_denied(product):
    """
    Devuelve una respuesta 403 si el producto está fuera del alcance del usuario,
    o None si tiene acceso.
    """
    role = g.current_user.get('role')
    if role == 'super_admin':
        return None

    user_business_id = g.current_user.get('businessId')
    user_branch_id = g.current_user.get('branchId')

    if product.get('businessId') != user_business_id:
        return _error(403, 'No tienes acceso a este producto')

    if user_branch_id and product.get('branchId') != user_branch_id:
        return _error(403, 'No tienes acceso a este producto')

    return None


def _fetch_active_product(firebase_service, product_id):
    """
    Devuelve (product, None) o (None, response) con 404 si no existe/está borrado.
    """
    product = firebase_service.get_document(PRODUCTS_COLLECTION, product_id)
    if not product or not _is_active_product(product):
        return None, _error(404, 'Producto no encontrado')
    return product, None


def _today_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


# ============================================================================
# GET /api/products  (list — TODOS los roles)
# ============================================================================

@products_bp.route('', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def list_products():
    """
    Lista los productos del negocio (y sede si aplica) con filtros y paginación.

    Query Params: category, lowStock (bool), search, branchId, businessId
                  (super_admin), page, limit
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
            products = firebase_service.query_firestore(PRODUCTS_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        # Filtrado defensivo + filtros de negocio/sede/categoría/stock/búsqueda en Python.
        category = (request.args.get('category') or '').strip()
        low_stock = (request.args.get('lowStock') or '').strip().lower() in ('true', '1', 'yes')
        search = (request.args.get('search') or '').strip().lower()

        result = []
        for p in products:
            if not _is_active_product(p):
                continue
            if branch_id and p.get('branchId') != branch_id:
                continue
            if category and p.get('category') != category:
                continue
            stock_qty = int(p.get('stockQty') or 0)
            if low_stock:
                # Stock bajo = en existencia pero en/por debajo del umbral
                # (misma semántica que `lowStockCount` del resumen).
                if not (0 < stock_qty <= _threshold(p)):
                    continue
            if search and search not in str(p.get('name') or '').lower():
                continue
            result.append(p)

        # Orden estable por nombre.
        result.sort(key=lambda p: (p.get('name') or '').lower())

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
        logger.error(f"Error listando productos: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/products/summary  (TODOS los roles)
# IMPORTANTE: declarado ANTES de `/<product_id>` para no ser capturado.
# ============================================================================

@products_bp.route('/summary', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def products_summary():
    """
    Resumen de inventario calculado con UNA sola query scoped a `products`.

    Response (200): { success, data:{totalProducts, totalStockValue,
                     lowStockCount, outOfStockCount} }
    """
    try:
        business_id, branch_id = _scope_ids()

        filters = []
        if business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': business_id})

        firebase_service = FirebaseService()
        try:
            products = firebase_service.query_firestore(PRODUCTS_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        active = [
            p for p in products
            if _is_active_product(p) and (not branch_id or p.get('branchId') == branch_id)
        ]

        total_stock_value = 0
        low_stock_count = 0
        out_of_stock_count = 0

        for p in active:
            stock_qty = int(p.get('stockQty') or 0)
            # Valor del stock = totalCostCents (costo real invertido). Fallback a
            # stockQty * costPriceCents para productos legacy sin el campo.
            total_cost = p.get('totalCostCents')
            if total_cost is not None:
                total_stock_value += int(total_cost)
            else:
                cost_cents = int(p.get('costPriceCents') or 0)
                total_stock_value += stock_qty * cost_cents
            if stock_qty == 0:
                out_of_stock_count += 1
            elif stock_qty <= _threshold(p):
                low_stock_count += 1

        return jsonify({
            'success': True,
            'data': {
                'totalProducts': len(active),
                'totalStockValue': total_stock_value,
                'lowStockCount': low_stock_count,
                'outOfStockCount': out_of_stock_count,
            }
        }), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error calculando resumen de productos: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/products/report  (TODOS los roles)
# IMPORTANTE: declarado ANTES de `/<product_id>` para no ser capturado.
# ============================================================================

@products_bp.route('/report', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def products_report():
    """
    Reporte de ventas vs compras: ingreso desde `sales`, egreso desde
    `product_movements` (compras solamente).

    Query Params: startDate, endDate (YYYY-MM-DD, opcionales), branchId,
                  businessId (super_admin)
    Response (200): { success, data:{ sales:{count,totalCents},
                     purchases:{count,totalCents}, net, daily:[
                     {date, salesCents, purchasesCents}] } }

    `net = sales.totalCents - purchases.totalCents` (una compra es dinero que
    sale). DOS queries scoped (igualdad businessId en `sales` y en
    `product_movements`) y toda la agregación por fecha en Python.
    """
    try:
        business_id, branch_id = _scope_ids()

        start_date = (request.args.get('startDate') or '').strip()
        end_date = (request.args.get('endDate') or '').strip()

        errors = []
        if start_date:
            errors.extend(validate_date_format(start_date, 'startDate'))
        if end_date:
            errors.extend(validate_date_format(end_date, 'endDate'))
        if errors:
            return _error(400, '; '.join(errors))

        filters = []
        if business_id:
            filters.append({'field': 'businessId', 'operator': '==', 'value': business_id})

        firebase_service = FirebaseService()
        try:
            sales_docs = firebase_service.query_firestore(SALES_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        try:
            movements = firebase_service.query_firestore(MOVEMENTS_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        sales_count = 0
        sales_cents = 0
        purchases_count = 0
        purchases_cents = 0
        daily_map = {}

        for s in sales_docs:
            if branch_id and s.get('branchId') != branch_id:
                continue
            s_date = s.get('date') or ''
            if start_date and s_date < start_date:
                continue
            if end_date and s_date > end_date:
                continue

            total = int(s.get('totalCents') or 0)
            sales_count += 1
            sales_cents += total
            day = daily_map.setdefault(
                s_date, {'date': s_date, 'salesCents': 0, 'purchasesCents': 0}
            )
            day['salesCents'] += total

        for m in movements:
            if branch_id and m.get('branchId') != branch_id:
                continue
            if m.get('type') != 'purchase':
                continue
            m_date = m.get('date') or ''
            if start_date and m_date < start_date:
                continue
            if end_date and m_date > end_date:
                continue

            total = int(m.get('totalCents') or 0)
            purchases_count += 1
            purchases_cents += total
            day = daily_map.setdefault(
                m_date, {'date': m_date, 'salesCents': 0, 'purchasesCents': 0}
            )
            day['purchasesCents'] += total

        daily = sorted(daily_map.values(), key=lambda d: d['date'])

        return jsonify({
            'success': True,
            'data': {
                'sales': {'count': sales_count, 'totalCents': sales_cents},
                'purchases': {'count': purchases_count, 'totalCents': purchases_cents},
                'net': sales_cents - purchases_cents,
                'daily': daily,
            }
        }), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error calculando reporte de productos: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/products/<id>  (TODOS los roles)
# Declarado DESPUÉS de `/summary` y `/report` para que las rutas estáticas no
# sean capturadas.
# ============================================================================

@products_bp.route('/<product_id>', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def get_product(product_id):
    """
    Detalle de un producto del catálogo. 404 si no existe o está borrado
    (`isActive:false`); 403 si está fuera del alcance del usuario (negocio/sede).

    Response (200): { success, data:{id, ...campos} }
    """
    try:
        firebase_service = FirebaseService()
        product, not_found = _fetch_active_product(firebase_service, product_id)
        if not_found:
            return not_found

        denied = _product_scope_denied(product)
        if denied:
            return denied

        return jsonify({'success': True, 'data': product}), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error obteniendo producto {product_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# POST /api/products  (admin+)
# ============================================================================

@products_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(ADMIN_ROLES)
def create_product():
    """
    Crea un producto. Valida `name`, `category`, `costPriceCents >= 0` y
    `salePriceCents > 0`. `stockQty >= 0` opcional (default 0) y
    `lowStockThreshold` opcional (default 5).

    Si `stockQty > 0` se crea automáticamente un movimiento `purchase` inicial
    (`qty=stockQty`, `unitPriceCents=costPriceCents`) — segunda escritura.

    Response (201): { success, data:{...} }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return _error(400, 'Se requieren datos en el cuerpo del request')

        name = (data.get('name') or '').strip()
        if not name:
            return _error(400, 'El campo name es requerido')

        category = (data.get('category') or '').strip()
        if category not in PRODUCT_CATEGORIES:
            return _error(400, f'category debe ser uno de: {", ".join(PRODUCT_CATEGORIES)}')

        cost_cents = data.get('costPriceCents')
        if not _valid_int(cost_cents, 0):
            return _error(400, 'costPriceCents debe ser un entero de centavos >= 0')

        sale_cents = data.get('salePriceCents')
        if not _valid_int(sale_cents, 1):
            return _error(400, 'salePriceCents debe ser un entero de centavos mayor que 0')

        stock_qty = data.get('stockQty', 0)
        if not _valid_int(stock_qty, 0):
            return _error(400, 'stockQty debe ser un entero >= 0')

        threshold = data.get('lowStockThreshold', DEFAULT_LOW_STOCK_THRESHOLD)
        if not _valid_int(threshold, 0):
            return _error(400, 'lowStockThreshold debe ser un entero >= 0')

        role = g.current_user.get('role')
        user_branch_id = g.current_user.get('branchId')
        branch_id = data.get('branchId')

        # Alcance de sede: un usuario acotado a sede solo crea en su sede.
        if role != 'super_admin' and user_branch_id and branch_id and branch_id != user_branch_id:
            return _error(403, 'No puedes crear productos en esta sede')
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

        method = str(data.get('method') or 'cash').strip() or 'cash'
        if method not in PURCHASE_METHODS:
            return _error(400, f'method debe ser uno de: {", ".join(PURCHASE_METHODS)}')
        payment_account_id = data.get('paymentAccountId')
        if payment_account_id is not None:
            payment_account_id = str(payment_account_id).strip() or None
        if method in ACCOUNT_REQUIRED_METHODS and not payment_account_id:
            return _error(400, f'Debes seleccionar una cuenta destino para {method}')

        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            'name': name,
            'category': category,
            'costPriceCents': cost_cents,
            'salePriceCents': sale_cents,
            'stockQty': stock_qty,
            'totalCostCents': stock_qty * cost_cents,
            'lowStockThreshold': threshold,
            'imageUrl': image_url,
            'businessId': business_id,
            'branchId': branch_id,
            'isActive': True,
            'registeredBy': g.current_user.get('uid'),
            'registeredByName': g.current_user.get('name'),
            'createdAt': now_iso,
        }

        firebase_service = FirebaseService()
        created = firebase_service.create_document(PRODUCTS_COLLECTION, record)
        if not created:
            return _error(500, 'Error al crear el producto')

        # Stock inicial ⇒ movimiento de compra auditable (segunda escritura).
        if stock_qty > 0:
            movement = {
                'productId': created.get('id'),
                'type': 'purchase',
                'qty': stock_qty,
                'unitPriceCents': cost_cents,
                'totalCents': stock_qty * cost_cents,
                'date': _today_utc(),
                'method': method,
                'paymentAccountId': payment_account_id,
                'businessId': business_id,
                'branchId': branch_id,
                'registeredBy': g.current_user.get('uid'),
                'registeredByName': g.current_user.get('name'),
                'createdAt': now_iso,
                'note': 'Stock inicial',
            }
            firebase_service.create_document(MOVEMENTS_COLLECTION, movement)

        logger.info(f"Producto creado: {created.get('id')}")
        return jsonify({'success': True, 'data': created}), 201

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error creando producto: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# PUT /api/products/<id>  (admin+)
# ============================================================================

@products_bp.route('/<product_id>', methods=['PUT', 'OPTIONS'])
@require_auth
@require_role(ADMIN_ROLES)
def update_product(product_id):
    """
    Actualiza un producto. 404 si no existe/borrado; 403 fuera de alcance.

    El stock NO se edita aquí: solo se ajusta mediante movimientos (libro
    append-only), preservando la trazabilidad del inventario.

    Response (200): { success, data:{id, ...campos} }
    """
    try:
        firebase_service = FirebaseService()
        product, not_found = _fetch_active_product(firebase_service, product_id)
        if not_found:
            return not_found

        denied = _product_scope_denied(product)
        if denied:
            return denied

        data = request.get_json(silent=True)
        if not data:
            return _error(400, 'Se requieren datos en el cuerpo del request')

        update = {}

        if 'name' in data:
            name = (data.get('name') or '').strip()
            if not name:
                return _error(400, 'El campo name no puede estar vacío')
            update['name'] = name

        if 'category' in data:
            category = (data.get('category') or '').strip()
            if category not in PRODUCT_CATEGORIES:
                return _error(400, f'category debe ser uno de: {", ".join(PRODUCT_CATEGORIES)}')
            update['category'] = category

        if 'costPriceCents' in data:
            cost_cents = data.get('costPriceCents')
            if not _valid_int(cost_cents, 0):
                return _error(400, 'costPriceCents debe ser un entero de centavos >= 0')
            update['costPriceCents'] = cost_cents

        if 'salePriceCents' in data:
            sale_cents = data.get('salePriceCents')
            if not _valid_int(sale_cents, 1):
                return _error(400, 'salePriceCents debe ser un entero de centavos mayor que 0')
            update['salePriceCents'] = sale_cents

        if 'lowStockThreshold' in data:
            threshold = data.get('lowStockThreshold')
            if not _valid_int(threshold, 0):
                return _error(400, 'lowStockThreshold debe ser un entero >= 0')
            update['lowStockThreshold'] = threshold

        if 'imageUrl' in data:
            try:
                update['imageUrl'] = clean_image_url(data.get('imageUrl'))
            except ValueError as exc:
                return _error(400, str(exc))

        if not update:
            return _error(400, 'No se enviaron campos válidos para actualizar')

        success = firebase_service.update_document(PRODUCTS_COLLECTION, product_id, update)
        if not success:
            return _error(500, 'Error al actualizar el producto')

        logger.info(f"Producto actualizado: {product_id}")
        return jsonify({'success': True, 'data': {'id': product_id, **update}}), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error actualizando producto {product_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# DELETE /api/products/<id>  (admin+)
# ============================================================================

@products_bp.route('/<product_id>', methods=['DELETE', 'OPTIONS'])
@require_auth
@require_role(ADMIN_ROLES)
def delete_product(product_id):
    """Soft delete: marca isActive=false y conserva auditoría (deletedBy, deletedAt)."""
    try:
        firebase_service = FirebaseService()
        product, not_found = _fetch_active_product(firebase_service, product_id)
        if not_found:
            return not_found

        denied = _product_scope_denied(product)
        if denied:
            return denied

        now_iso = datetime.now(timezone.utc).isoformat()
        success = firebase_service.update_document(PRODUCTS_COLLECTION, product_id, {
            'isActive': False,
            'deletedBy': g.current_user.get('uid'),
            'deletedAt': now_iso,
        })
        if not success:
            return _error(500, 'Error al eliminar el producto')

        logger.info(f"Producto eliminado (soft delete): {product_id}")
        return jsonify({'success': True, 'data': {'id': product_id}}), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error eliminando producto {product_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/products/<id>/movements  (TODOS los roles)
# ============================================================================

@products_bp.route('/<product_id>/movements', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def get_product_movements(product_id):
    """
    Historial de movimientos de un producto, ordenado por `date` DESC y paginado.
    404 si el producto no existe/está borrado.

    Query Params: page, limit
    Response (200): { success, data[], meta{total,page,limit,pages} }
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        pagination = validate_pagination(page, limit)

        firebase_service = FirebaseService()
        product, not_found = _fetch_active_product(firebase_service, product_id)
        if not_found:
            return not_found

        denied = _product_scope_denied(product)
        if denied:
            return denied

        filters = [
            {'field': 'productId', 'operator': '==', 'value': product_id},
        ]
        if product.get('businessId'):
            filters.append({'field': 'businessId', 'operator': '==', 'value': product.get('businessId')})

        try:
            records = firebase_service.query_firestore(MOVEMENTS_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        # date DESC; desempate por createdAt DESC para movimientos del mismo día.
        records.sort(
            key=lambda r: (r.get('date') or '', r.get('createdAt') or ''),
            reverse=True,
        )

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
        logger.error(f"Error obteniendo movimientos de {product_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# POST /api/products/<id>/movement  (compra "Reponer", admin+)
# ============================================================================

@products_bp.route('/<product_id>/movement', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(ADMIN_ROLES)
def register_movement(product_id):
    """
    Registra una COMPRA (append-only) y aumenta el stock del producto.

    Body: {type:'purchase', qty:int>0, unitPriceCents:int>=0, updateCostPrice?:bool,
           date?:YYYY-MM-DD, note?:str}

    - SOLO admin+ (ADMIN_ROLES); cashier ⇒ 403 (vía `@require_role`).
    - `unitPriceCents` (costo) es requerido; con `updateCostPrice:true` actualiza
      `product.costPriceCents`.
    - Las ventas NO son movimientos: se registran vía `POST /api/sales`.

    NUNCA crea/muta documentos de `expenses` (anti-doble-conteo).
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return _error(400, 'Se requieren datos en el cuerpo del request')

        mtype = (data.get('type') or '').strip()
        if mtype not in MOVEMENT_TYPES:
            return _error(400, f'type debe ser uno de: {", ".join(MOVEMENT_TYPES)}')

        qty = data.get('qty')
        if not _valid_int(qty, 1):
            return _error(400, 'qty debe ser un entero mayor que 0')

        date_str = (data.get('date') or _today_utc()).strip()
        errors = validate_date_format(date_str, 'date')
        if errors:
            return _error(400, '; '.join(errors))

        note = data.get('note')
        if note is not None:
            note = str(note).strip() or None

        method = str(data.get('method') or 'cash').strip() or 'cash'
        if method not in PURCHASE_METHODS:
            return _error(400, f'method debe ser uno de: {", ".join(PURCHASE_METHODS)}')

        payment_account_id = data.get('paymentAccountId')
        if payment_account_id is not None:
            payment_account_id = str(payment_account_id).strip() or None
        if method in ACCOUNT_REQUIRED_METHODS and not payment_account_id:
            return _error(400, f'Debes seleccionar una cuenta destino para {method}')

        firebase_service = FirebaseService()
        product, not_found = _fetch_active_product(firebase_service, product_id)
        if not_found:
            return not_found

        denied = _product_scope_denied(product)
        if denied:
            return denied

        stock_qty = int(product.get('stockQty') or 0)
        now_iso = datetime.now(timezone.utc).isoformat()

        unit_price = data.get('unitPriceCents')
        if not _valid_int(unit_price, 0):
            return _error(400, 'unitPriceCents es requerido y debe ser un entero de centavos >= 0')

        product_update = {'stockQty': stock_qty + qty}
        # Actualizar totalCostCents: sumar lo invertido en esta compra.
        # Fallback: si el producto no tiene totalCostCents (legacy), calcularlo del stock × costo.
        current_total_cost = product.get('totalCostCents')
        if current_total_cost is None:
            current_total_cost = stock_qty * int(product.get('costPriceCents') or 0)
        product_update['totalCostCents'] = int(current_total_cost) + (qty * unit_price)
        if data.get('updateCostPrice') is True:
            product_update['costPriceCents'] = unit_price

        record = {
            'productId': product_id,
            'type': 'purchase',
            'qty': qty,
            'unitPriceCents': unit_price,
            'totalCents': qty * unit_price,
            'date': date_str,
            'method': method,
            'paymentAccountId': payment_account_id,
            'businessId': product.get('businessId'),
            'branchId': product.get('branchId'),
            'registeredBy': g.current_user.get('uid'),
            'registeredByName': g.current_user.get('name'),
            'createdAt': now_iso,
            'note': note,
        }

        created = firebase_service.create_document(MOVEMENTS_COLLECTION, record)
        if not created:
            return _error(500, 'Error al registrar el movimiento')

        updated = firebase_service.update_document(PRODUCTS_COLLECTION, product_id, product_update)
        if not updated:
            return _error(500, 'Error al actualizar el stock del producto')

        logger.info(f"Movimiento purchase registrado para {product_id}: {created.get('id')}")
        return jsonify({'success': True, 'data': created}), 201

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error registrando movimiento de {product_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')
