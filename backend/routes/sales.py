"""
Rutas de Punto de Venta (Ventas de productos).

Colecciones:
    - `sales` - libro de ventas (ingreso). Cada venta es un carrito multi-ítem.

Endpoints:
    GET    /api/sales        - listar (TODOS los roles; scoped + paginado, date DESC)
    GET    /api/sales/<id>   - detalle / recibo (TODOS los roles)
    POST   /api/sales        - checkout del carrito (cashier+)

Patrón: copia fiel de `routes/products.py` y `services/payment_service.py`
(generación de número de recibo). Las ventas son una colección separada de
`product_movements` (que ahora es SOLO compras): vender escribe UN documento de
`sales` y descuenta `stockQty` por ítem (sin tocar movimientos).

Roles: lectura para TODOS los roles; creación para `CREATE_ROLES`
(`super_admin`, `admin`, `branch_admin`, `cashier`). El descuento de stock NO es
atómico (validación-todo-primero + escrituras secuenciales); las transacciones
de Firestore están fuera de alcance.

IMPORTANTE: `sales (businessId ASC, date ASC)` requiere índice compuesto manual
(ver `openspec/changes/point-of-sale/firestore-indexes.md`).
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g

from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from models.payment import PaymentModel
from utils.validators import validate_pagination, validate_date_format

logger = logging.getLogger(__name__)

sales_bp = Blueprint('sales', __name__, url_prefix='/api/sales')

SALES_COLLECTION = 'sales'
PRODUCTS_COLLECTION = 'products'

CREATE_ROLES = ['super_admin', 'admin', 'branch_admin', 'cashier']
READ_ROLES = ['super_admin', 'admin', 'branch_admin', 'cashier', 'trainer']

# Métodos de pago reutilizados del modelo de pagos (fuente única de verdad).
VALID_METHODS = PaymentModel.VALID_METHODS

# Métodos que exigen una cuenta destino (payment_accounts).
ACCOUNT_REQUIRED_METHODS = {'zelle', 'pago_movil', 'binance'}


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
                    'colección `sales`: (businessId ASC, date ASC).'
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


def _scope_ids():
    """
    Devuelve (business_id, branch_id) que restringen la consulta del usuario.

    - super_admin: opcionales desde query params (puede ser None → cross-business).
    - otros roles: forzados del usuario autenticado (branchId puede ser None).
    """
    if g.current_user.get('role') == 'super_admin':
        return request.args.get('businessId'), request.args.get('branchId')
    return g.current_user.get('businessId'), g.current_user.get('branchId')


def _product_out_of_scope(product):
    """
    True si el producto está fuera del alcance del usuario (negocio/sede).
    """
    role = g.current_user.get('role')
    if role == 'super_admin':
        return False

    user_business_id = g.current_user.get('businessId')
    user_branch_id = g.current_user.get('branchId')

    if product.get('businessId') != user_business_id:
        return True
    if user_branch_id and product.get('branchId') != user_branch_id:
        return True
    return False


def _sale_scope_denied(sale):
    """
    Devuelve una respuesta 403 si la venta está fuera del alcance del usuario,
    o None si tiene acceso.
    """
    role = g.current_user.get('role')
    if role == 'super_admin':
        return None

    user_business_id = g.current_user.get('businessId')
    user_branch_id = g.current_user.get('branchId')

    if sale.get('businessId') != user_business_id:
        return _error(403, 'No tienes acceso a esta venta')
    if user_branch_id and sale.get('branchId') != user_branch_id:
        return _error(403, 'No tienes acceso a esta venta')
    return None


def _generate_receipt_number(firebase_service, business_id):
    """
    Genera un número de recibo único `V-YYYYMMDD-XXX` (secuencia = conteo de
    ventas del negocio + 1). Fallback con timestamp `V-YYYYMMDD-HHMMSSffffff` si
    el conteo falla o alcanza el techo (mirror de PaymentService).
    """
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    try:
        count = firebase_service.count_firestore(
            SALES_COLLECTION,
            filters=[{'field': 'businessId', 'operator': '==', 'value': business_id}]
        )
        seq = count + 1
        return f'V-{date_str}-{seq:03d}'
    except Exception as e:
        logger.error(f"Error generando número de recibo, fallback timestamp: {str(e)}")
        return f'V-{datetime.now().strftime("%Y%m%d-%H%M%S%f")}'


def _today_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


# ============================================================================
# POST /api/sales  (cashier+)
# ============================================================================

@sales_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(CREATE_ROLES)
def create_sale():
    """
    Registra una venta (checkout del carrito) y descuenta stock por ítem.

    Body: { items:[{productId, qty}], method, paymentAccountId?, clientId?,
            clientName?, branchId?, date? }

    - Valida TODOS los ítems (producto existente/activo/en alcance, qty>0 entero)
      leyendo cada producto UNA vez.
    - Si CUALQUIER ítem supera `stockQty` → 400 nombrando el producto, SIN
      escrituras (rechaza la venta completa).
    - En éxito: escribe el doc de `sales` (totalCents = Σ subtotales) y descuenta
      `stockQty` por ítem (no-atómico, documentado).

    Response (201): { success, data:{id, receiptNumber, ...} }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return _error(400, 'Se requieren datos en el cuerpo del request')

        raw_items = data.get('items')
        if not isinstance(raw_items, list) or len(raw_items) == 0:
            return _error(400, 'items debe ser una lista no vacía de productos')

        # Merge de cantidades por producto (un producto puede aparecer más de una vez).
        qty_by_product = {}
        for item in raw_items:
            if not isinstance(item, dict):
                return _error(400, 'Cada item debe ser un objeto con productId y qty')
            product_id = str(item.get('productId') or '').strip()
            qty = item.get('qty')
            if not product_id:
                return _error(400, 'Cada item requiere un productId')
            if not _valid_int(qty, 1):
                return _error(400, 'qty debe ser un entero mayor que 0')
            qty_by_product[product_id] = qty_by_product.get(product_id, 0) + qty

        method = (data.get('method') or '').strip()
        if method not in VALID_METHODS:
            return _error(400, f'method debe ser uno de: {", ".join(VALID_METHODS)}')

        payment_account_id = data.get('paymentAccountId')
        if payment_account_id is not None:
            payment_account_id = str(payment_account_id).strip() or None

        # Zelle / Pago Móvil / Binance exigen cuenta destino seleccionada.
        if method in ACCOUNT_REQUIRED_METHODS and not payment_account_id:
            return _error(400, f'Debes seleccionar una cuenta destino para {method}')

        client_id = data.get('clientId')
        if client_id is not None:
            client_id = str(client_id).strip() or None
        client_name = data.get('clientName')
        if client_name is not None:
            client_name = str(client_name).strip() or None

        date_str = (data.get('date') or _today_utc()).strip()
        errors = validate_date_format(date_str, 'date')
        if errors:
            return _error(400, '; '.join(errors))

        role = g.current_user.get('role')
        user_branch_id = g.current_user.get('branchId')
        branch_id = data.get('branchId')
        if branch_id is not None:
            branch_id = str(branch_id).strip() or None

        # Alcance de sede: un usuario acotado a sede solo vende en su sede.
        if role != 'super_admin' and user_branch_id:
            branch_id = user_branch_id

        if role == 'super_admin':
            business_id = data.get('businessId') or request.args.get('businessId')
        else:
            business_id = g.current_user.get('businessId')

        firebase_service = FirebaseService()

        # Leer todos los productos UNA vez y validar existencia/activo/alcance/stock.
        items_detail = []
        new_stock = {}
        new_total_cost = {}
        total_cents = 0
        derived_business_id = None
        derived_branch_id = None
        for product_id, qty in qty_by_product.items():
            product = firebase_service.get_document(PRODUCTS_COLLECTION, product_id)
            if not product or not _is_active_product(product):
                return _error(400, f'Producto no encontrado: {product_id}')
            if _product_out_of_scope(product):
                return _error(403, 'No tienes acceso a este producto')

            # La venta pertenece al negocio/sede de los productos vendidos.
            product_business_id = product.get('businessId')
            if derived_business_id is None:
                derived_business_id = product_business_id
            elif product_business_id and product_business_id != derived_business_id:
                return _error(400, 'Los productos de una venta deben pertenecer al mismo negocio')
            if derived_branch_id is None:
                derived_branch_id = product.get('branchId')

            stock_qty = int(product.get('stockQty') or 0)
            if qty > stock_qty:
                return _error(400, f'Stock insuficiente para "{product.get("name", product_id)}"')

            unit_price = int(product.get('salePriceCents') or 0)
            subtotal = qty * unit_price
            total_cents += subtotal
            new_stock[product_id] = stock_qty - qty

            # Costo promedio ponderado: descuenta el costo proporcional de las unidades vendidas
            # Fallback: si el producto no tiene totalCostCents (legacy), calcularlo del stock × costo
            current_total_cost = product.get('totalCostCents')
            if current_total_cost is None:
                current_total_cost = stock_qty * int(product.get('costPriceCents') or 0)
            current_total_cost = int(current_total_cost)
            weighted_avg = current_total_cost / stock_qty if stock_qty > 0 else 0
            cost_deduction = round(qty * weighted_avg)
            new_total_cost[product_id] = max(0, current_total_cost - cost_deduction)

            items_detail.append({
                'productId': product_id,
                'productName': product.get('name'),
                'qty': qty,
                'unitPriceCents': unit_price,
                'subtotalCents': subtotal,
            })

        # Si no vino negocio/sede explícito (p. ej. super_admin sin businessId),
        # se heredan del producto vendido para que los reportes puedan encontrarla.
        if not business_id:
            business_id = derived_business_id
        if not branch_id:
            branch_id = derived_branch_id
        if not business_id:
            return _error(400, 'No se pudo determinar el negocio de la venta')

        receipt = _generate_receipt_number(firebase_service, business_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            'receiptNumber': receipt,
            'date': date_str,
            'totalCents': total_cents,
            'method': method,
            'paymentAccountId': payment_account_id,
            'clientId': client_id,
            'clientName': client_name,
            'items': items_detail,
            'businessId': business_id,
            'branchId': branch_id,
            'registeredBy': g.current_user.get('uid'),
            'registeredByName': g.current_user.get('name'),
            'createdAt': now_iso,
        }

        created = firebase_service.create_document(SALES_COLLECTION, record)
        if not created:
            return _error(500, 'Error al registrar la venta')

        # Descuento de stock y costo por ítem (no-atómico, documentado).
        for product_id, new_qty in new_stock.items():
            update_data = {
                'stockQty': new_qty,
                'totalCostCents': new_total_cost.get(product_id, 0),
            }
            updated = firebase_service.update_document(PRODUCTS_COLLECTION, product_id, update_data)
            if not updated:
                logger.error(f"No se pudo descontar stock del producto {product_id}")

        logger.info(f"Venta registrada: {receipt} ({created.get('id')})")
        return jsonify({'success': True, 'data': created}), 201

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error registrando venta: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/sales  (list — TODOS los roles)
# ============================================================================

@sales_bp.route('', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def list_sales():
    """
    Lista las ventas del negocio (y sede si aplica) con filtros y paginación.

    Query Params: startDate, endDate (YYYY-MM-DD, opcionales), clientName
                  (búsqueda), branchId, businessId (super_admin), page, limit
    Response (200): { success, data[], meta{total,page,limit,pages} }

    Firestore aplica SOLO la igualdad de `businessId`; los filtros de rango,
    `branchId` y búsqueda por cliente + el orden `date` DESC se resuelven en
    Python (volumen bajo/medio de ventas por negocio).
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        pagination = validate_pagination(page, limit)

        business_id, branch_id = _scope_ids()

        start_date = (request.args.get('startDate') or '').strip()
        end_date = (request.args.get('endDate') or '').strip()
        client_name = (request.args.get('clientName') or '').strip().lower()

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
            sales = firebase_service.query_firestore(SALES_COLLECTION, filters=filters)
        except Exception as query_error:
            index_response = _index_error_response(query_error)
            if index_response:
                return index_response
            raise

        result = []
        for s in sales:
            if branch_id and s.get('branchId') != branch_id:
                continue
            s_date = s.get('date') or ''
            if start_date and s_date < start_date:
                continue
            if end_date and s_date > end_date:
                continue
            if client_name and client_name not in str(s.get('clientName') or '').lower():
                continue
            result.append(s)

        # date DESC; desempate por createdAt DESC para ventas del mismo día.
        result.sort(
            key=lambda s: (s.get('date') or '', s.get('createdAt') or ''),
            reverse=True,
        )

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
        logger.error(f"Error listando ventas: {str(e)}")
        return _error(500, 'Error interno del servidor')


# ============================================================================
# GET /api/sales/<id>  (detalle/recibo — TODOS los roles)
# ============================================================================

@sales_bp.route('/<sale_id>', methods=['GET', 'OPTIONS'])
@require_auth
@require_role(READ_ROLES)
def get_sale(sale_id):
    """
    Detalle de una venta (recibo). 404 si no existe; 403 fuera de alcance.

    Response (200): { success, data:{id, receiptNumber, items[], ...} }
    """
    try:
        firebase_service = FirebaseService()
        sale = firebase_service.get_document(SALES_COLLECTION, sale_id)
        if not sale:
            return _error(404, 'Venta no encontrada')

        denied = _sale_scope_denied(sale)
        if denied:
            return denied

        return jsonify({'success': True, 'data': sale}), 200

    except Exception as e:
        index_response = _index_error_response(e)
        if index_response:
            return index_response
        logger.error(f"Error obteniendo venta {sale_id}: {str(e)}")
        return _error(500, 'Error interno del servidor')
