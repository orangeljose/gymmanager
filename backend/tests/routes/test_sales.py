"""
Tests para las rutas de Punto de Venta (/api/sales)

Patrón de mock (idéntico a test_products.py / test_expenses.py): las rutas
importan `FirebaseService` a nivel de módulo, por lo que se parchea el símbolo en
`routes.sales` y en `middleware.auth_middleware`, además del módulo
`services.firebase_service` que usa `app.py` al inicializar. Cada request se
ejecuta DENTRO de los patches para que cada test use SU mock y no dependa del
orden de ejecución entre archivos.

Cubre: checkout multi-ítem 201 + descuento por ítem, sobreventa 400 sin
escrituras, recibo `V-YYYYMMDD-XXX` + secuencial (`count=4` → `-005`),
list/detail + scope + permisos, walk-in sin cliente, frontera `stockQty:2`/qty:2 → 0.
"""
import re
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

RECEIPT_RE = re.compile(r'^V-\d{8}-\d{3}$')


# ============================================================================
# FACTORY
# ============================================================================

def create_mock_service(role='cashier', uid='user-123', business_id='biz-1', branch_id='branch-1'):
    """Crea un FirebaseService mockeado con un usuario del rol indicado."""
    user_data = {
        'uid': uid,
        'email': f'{role}@test.com',
        'name': f'{role.title()} Test',
        'role': role,
        'businessId': business_id,
        'branchId': None if role == 'super_admin' else branch_id,
        'permissions': ['*'] if role == 'super_admin' else [],
        'isActive': True,
    }

    mock = MagicMock()
    mock.verify_token.return_value = {'uid': uid}
    mock.get_user_by_uid.return_value = user_data
    mock.query_firestore.return_value = []
    mock.get_document.return_value = None
    mock.create_document.return_value = {'id': 'sale-1'}
    mock.update_document.return_value = True
    mock.count_firestore.return_value = 0
    return mock


def _product(**overrides):
    base = {
        'id': 'p1', 'name': 'Proteína Whey', 'category': 'supplement',
        'costPriceCents': 1500, 'salePriceCents': 2500, 'stockQty': 10,
        'lowStockThreshold': 5, 'businessId': 'biz-1', 'branchId': 'branch-1',
        'isActive': True, 'registeredBy': 'user-123', 'registeredByName': 'Cashier Test',
        'createdAt': '2026-10-10T10:00:00+00:00',
    }
    base.update(overrides)
    return base


def _sale(**overrides):
    base = {
        'id': 's1', 'receiptNumber': 'V-20261015-001', 'date': '2026-10-15',
        'totalCents': 5000, 'method': 'cash', 'paymentAccountId': None,
        'clientId': None, 'clientName': None,
        'items': [
            {'productId': 'p1', 'productName': 'Proteína Whey', 'qty': 2,
             'unitPriceCents': 2500, 'subtotalCents': 5000},
        ],
        'businessId': 'biz-1', 'branchId': 'branch-1',
        'registeredBy': 'user-123', 'registeredByName': 'Cashier Test',
        'createdAt': '2026-10-15T12:00:00+00:00',
    }
    base.update(overrides)
    return base


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    from services import firebase_service
    firebase_service.FirebaseService._reset()
    yield
    firebase_service.FirebaseService._reset()


@pytest.fixture(scope='module', autouse=True)
def prime_app_modules():
    """
    CRITICAL-01 (aislamiento entre archivos): el PRIMER import de `app` del
    proceso fija el binding de `FirebaseService` en middleware/rutas para TODOS
    los archivos que no parchean su call-site. Se primea con un mock super_admin
    bien configurado para no romper require_role en los archivos siguientes.
    """
    with patch('services.firebase_service.FirebaseService',
               return_value=create_mock_service(role='super_admin')):
        from app import create_app
        create_app()
    yield


@pytest.fixture
def auth_header():
    return {'Authorization': 'Bearer test-token'}


@pytest.fixture
def make_client():
    """Factory que arma el test_client con el mock dado, parchando los call-sites."""
    contexts = []

    def _factory(mock):
        ctx1 = patch('services.firebase_service.FirebaseService', return_value=mock)
        ctx1.start()
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        ctx2 = patch('routes.sales.FirebaseService', return_value=mock)
        ctx3 = patch('middleware.auth_middleware.FirebaseService', return_value=mock)
        ctx2.start()
        ctx3.start()
        contexts.append((ctx1, ctx2, ctx3))
        return app.test_client()

    yield _factory

    for ctx1, ctx2, ctx3 in contexts:
        ctx3.stop()
        ctx2.stop()
        ctx1.stop()


# ============================================================================
# POST /api/sales
# ============================================================================

class TestCreateSale:

    def test_multi_item_checkout_201_and_decrements_stock(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        products = {
            'p1': _product(id='p1', name='Proteína', stockQty=10, salePriceCents=2500),
            'p2': _product(id='p2', name='Agua', stockQty=20, salePriceCents=100),
        }
        mock.get_document.side_effect = lambda coll, doc_id: products.get(doc_id) if coll == 'products' else None
        mock.create_document.return_value = {'id': 'sale-9'}
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={
                'items': [
                    {'productId': 'p1', 'qty': 2},
                    {'productId': 'p2', 'qty': 3},
                ],
                'method': 'cash',
            },
            headers=auth_header,
        )

        assert response.status_code == 201
        collection, record = mock.create_document.call_args[0]
        assert collection == 'sales'
        assert RECEIPT_RE.match(record['receiptNumber'])
        assert record['totalCents'] == 2 * 2500 + 3 * 100
        assert record['method'] == 'cash'
        assert len(record['items']) == 2
        assert {i['productId'] for i in record['items']} == {'p1', 'p2'}

        # Descuento por ítem: stockQty -= qty
        updates = {c[0][1]: c[0][2] for c in mock.update_document.call_args_list}
        assert updates == {'p1': {'stockQty': 8, 'totalCostCents': 12000}, 'p2': {'stockQty': 17, 'totalCostCents': 25500}}
        # NINGÚN movimiento de productos: las ventas no escriben product_movements
        assert all(c[0][0] != 'product_movements' for c in mock.create_document.call_args_list)

    def test_super_admin_without_business_id_inherits_from_product(self, make_client, auth_header):
        """super_admin sin businessId en payload: la venta hereda negocio/sede del producto.

        Regresión: antes quedaba con businessId=None y los reportes no la veían.
        """
        mock = create_mock_service(role='super_admin')
        mock.get_document.side_effect = lambda coll, doc_id: (
            _product(id='p1', stockQty=10, salePriceCents=2500,
                     businessId='biz-9', branchId='branch-9')
            if coll == 'products' else None
        )
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 1}], 'method': 'cash'},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert record['businessId'] == 'biz-9'
        assert record['branchId'] == 'branch-9'

    def test_mixed_business_items_rejected_400(self, make_client, auth_header):
        """No se puede vender en una sola venta productos de negocios distintos."""
        mock = create_mock_service(role='super_admin')
        products = {
            'p1': _product(id='p1', businessId='biz-1'),
            'p2': _product(id='p2', businessId='biz-2'),
        }
        mock.get_document.side_effect = lambda coll, doc_id: (
            products.get(doc_id) if coll == 'products' else None
        )
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={
                'items': [
                    {'productId': 'p1', 'qty': 1},
                    {'productId': 'p2', 'qty': 1},
                ],
                'method': 'cash',
            },
            headers=auth_header,
        )

        assert response.status_code == 400
        assert 'mismo negocio' in response.get_json()['error']['message']
        mock.create_document.assert_not_called()

    def test_oversell_rejects_whole_sale_400_no_writes(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.get_document.side_effect = lambda coll, doc_id: (
            _product(id='p1', name='Proteína', stockQty=2, salePriceCents=2500)
            if coll == 'products' else None
        )
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 5}], 'method': 'cash'},
            headers=auth_header,
        )

        assert response.status_code == 400
        assert 'Stock insuficiente' in response.get_json()['error']['message']
        assert 'Proteína' in response.get_json()['error']['message']
        mock.create_document.assert_not_called()
        mock.update_document.assert_not_called()

    def test_receipt_sequential_count_plus_one(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.count_firestore.return_value = 4
        mock.get_document.return_value = _product(stockQty=10, salePriceCents=2500)
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 1}], 'method': 'cash'},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert RECEIPT_RE.match(record['receiptNumber'])
        assert record['receiptNumber'].endswith('-005')
        mock.count_firestore.assert_called_once_with(
            'sales',
            filters=[{'field': 'businessId', 'operator': '==', 'value': 'biz-1'}]
        )

    def test_walk_in_sale_null_client(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=10, salePriceCents=2500)
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 1}], 'method': 'cash'},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert record['clientId'] is None
        assert record['clientName'] is None

    def test_with_client_and_payment_account(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=10, salePriceCents=2500)
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={
                'items': [{'productId': 'p1', 'qty': 1}],
                'method': 'zelle',
                'paymentAccountId': 'acc-zelle-1',
                'clientId': 'c1',
                'clientName': 'Juan Pérez',
            },
            headers=auth_header,
        )

        assert response.status_code == 201
        _, record = mock.create_document.call_args[0]
        assert record['method'] == 'zelle'
        assert record['paymentAccountId'] == 'acc-zelle-1'
        assert record['clientId'] == 'c1'
        assert record['clientName'] == 'Juan Pérez'

    @pytest.mark.parametrize('account_method', ['zelle', 'pago_movil', 'binance'])
    def test_account_method_without_account_rejected_400(self, make_client, auth_header, account_method):
        """Zelle/Pago Móvil/Binance exigen cuenta destino; sin ella → 400 y sin escrituras."""
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=10, salePriceCents=2500)
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 1}], 'method': account_method},
            headers=auth_header,
        )

        assert response.status_code == 400
        assert 'cuenta destino' in response.get_json()['error']['message']
        mock.create_document.assert_not_called()
        mock.update_document.assert_not_called()

    def test_cash_does_not_require_account(self, make_client, auth_header):
        """Efectivo no requiere cuenta destino."""
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=10, salePriceCents=2500)
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 1}], 'method': 'cash'},
            headers=auth_header,
        )

        assert response.status_code == 201

    def test_boundary_stock_never_negative(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=2, salePriceCents=2500)
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 2}], 'method': 'cash'},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, doc_id, update = mock.update_document.call_args[0]
        assert update == {'stockQty': 0, 'totalCostCents': 0}

    def test_missing_product_400_no_writes(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.get_document.return_value = None
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'ghost', 'qty': 1}], 'method': 'cash'},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_empty_items_400(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        client = make_client(mock)

        response = client.post('/api/sales', json={'items': [], 'method': 'cash'}, headers=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_invalid_method_400(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 1}], 'method': 'bitcoin'},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()


# ============================================================================
# GET /api/sales  (list)
# ============================================================================

class TestListSales:

    def test_list_sorts_date_desc_and_meta(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.return_value = [
            _sale(id='s1', date='2026-10-01', receiptNumber='V-20261001-001', createdAt='2026-10-01T10:00:00Z'),
            _sale(id='s3', date='2026-10-15', receiptNumber='V-20261015-001', createdAt='2026-10-15T10:00:00Z'),
            _sale(id='s2', date='2026-10-10', receiptNumber='V-20261010-001', createdAt='2026-10-10T10:00:00Z'),
        ]
        client = make_client(mock)

        response = client.get('/api/sales', headers=auth_header)

        assert response.status_code == 200
        body = response.get_json()
        assert [s['id'] for s in body['data']] == ['s3', 's2', 's1']
        assert body['meta'] == {'total': 3, 'page': 1, 'limit': 20, 'pages': 1}
        filters = mock.query_firestore.call_args[1]['filters']
        assert filters == [{'field': 'businessId', 'operator': '==', 'value': 'biz-1'}]

    def test_list_filters_by_date_range_and_client(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.return_value = [
            _sale(id='in', date='2026-10-10', clientName='Ana Ruiz'),
            _sale(id='out_date', date='2026-09-01', clientName='Ana Ruiz'),
            _sale(id='other_client', date='2026-10-10', clientName='Luis Gómez'),
        ]
        client = make_client(mock)

        response = client.get(
            '/api/sales?startDate=2026-10-01&endDate=2026-10-31&clientName=ana',
            headers=auth_header,
        )

        assert [s['id'] for s in response.get_json()['data']] == ['in']

    def test_list_branch_scoped_user_filters_own_branch(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-1')
        mock.query_firestore.return_value = [
            _sale(id='a', branchId='branch-1'),
            _sale(id='b', branchId='branch-2'),
        ]
        client = make_client(mock)

        response = client.get('/api/sales', headers=auth_header)

        assert [s['id'] for s in response.get_json()['data']] == ['a']

    def test_list_empty_returns_empty_data(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.return_value = []
        client = make_client(mock)

        body = client.get('/api/sales', headers=auth_header).get_json()

        assert body['data'] == []
        assert body['meta']['total'] == 0


# ============================================================================
# GET /api/sales/<id>  (detalle/recibo)
# ============================================================================

class TestGetSale:

    def test_get_sale_200(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _sale()
        client = make_client(mock)

        response = client.get('/api/sales/s1', headers=auth_header)

        assert response.status_code == 200
        assert response.get_json()['data']['id'] == 's1'
        mock.get_document.assert_called_once_with('sales', 's1')

    def test_get_sale_missing_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = None
        client = make_client(mock)

        assert client.get('/api/sales/ghost', headers=auth_header).status_code == 404

    def test_get_sale_out_of_scope_403(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-2')
        mock.get_document.return_value = _sale()  # branch-1
        client = make_client(mock)

        assert client.get('/api/sales/s1', headers=auth_header).status_code == 403


# ============================================================================
# Permisos
# ============================================================================

class TestPermissions:

    def test_cashier_can_create_sale_201(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=10, salePriceCents=2500)
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 1}], 'method': 'cash'},
            headers=auth_header,
        )

        assert response.status_code == 201

    def test_trainer_cannot_create_sale_403(self, make_client, auth_header):
        mock = create_mock_service(role='trainer', business_id='biz-1')
        client = make_client(mock)

        response = client.post(
            '/api/sales',
            json={'items': [{'productId': 'p1', 'qty': 1}], 'method': 'cash'},
            headers=auth_header,
        )

        assert response.status_code == 403
        mock.create_document.assert_not_called()

    @pytest.mark.parametrize('role', ['super_admin', 'admin', 'branch_admin', 'cashier', 'trainer'])
    def test_all_roles_can_list_and_detail_200(self, make_client, auth_header, role):
        mock = create_mock_service(role=role, business_id='biz-1')
        mock.query_firestore.return_value = []
        mock.get_document.return_value = _sale(businessId='biz-1')
        client = make_client(mock)

        assert client.get('/api/sales', headers=auth_header).status_code == 200
        assert client.get('/api/sales/s1', headers=auth_header).status_code == 200

    @pytest.mark.parametrize('method,path', [
        ('get', '/api/sales'),
        ('get', '/api/sales/s1'),
        ('post', '/api/sales'),
    ])
    def test_unauth_returns_401(self, make_client, method, path):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = getattr(client, method)(path, json={} if method == 'post' else None)

        assert response.status_code == 401
