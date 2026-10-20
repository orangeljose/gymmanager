"""
Tests para las rutas de Productos/Inventario (/api/products)

Patrón de mock (idéntico a test_expenses.py / test_machines.py): las rutas
importan `FirebaseService` a nivel de módulo, por lo que se parchea el símbolo en
`routes.products` y en `middleware.auth_middleware`, además del módulo
`services.firebase_service` que usa `app.py` al inicializar. Cada request se
ejecuta DENTRO de los patches para que cada test use SU mock y no dependa del
orden de ejecución entre archivos.

Cubre: CRUD + validación, detalle GET /<id> (200/404/403), soft-delete +
auditoría, scope (business/branch), list (filtros/paginación + meta), summary
(conteos con UNA query), movimientos (compra incrementa + costo, compra por
cashier 403, `type:'sale'` → 400, inmutabilidad, purchase NO escribe expenses +
meta paginación), reporte (DOS queries: `sales` + `product_movements`) y la
matriz de permisos.
"""
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ============================================================================
# FACTORY
# ============================================================================

def create_mock_service(role='admin', uid='user-123', business_id='biz-1', branch_id='branch-1'):
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
    mock.create_document.return_value = {'id': 'new-doc-id'}
    mock.update_document.return_value = True
    return mock


def _product(**overrides):
    base = {
        'id': 'p1', 'name': 'Proteína Whey', 'category': 'supplement',
        'costPriceCents': 1500, 'salePriceCents': 2500, 'stockQty': 10,
        'lowStockThreshold': 5, 'businessId': 'biz-1', 'branchId': 'branch-1',
        'isActive': True, 'registeredBy': 'user-123', 'registeredByName': 'Admin Test',
        'createdAt': '2026-10-10T10:00:00+00:00',
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
        ctx2 = patch('routes.products.FirebaseService', return_value=mock)
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
# GET /api/products  (list)
# ============================================================================

class TestListProducts:

    def _products(self):
        return [
            _product(id='p1', name='Agua', category='drink', stockQty=20, lowStockThreshold=5),
            _product(id='p2', name='Jugo', category='drink', stockQty=3, lowStockThreshold=5),
            _product(id='p3', name='Camiseta', category='apparel', stockQty=0, lowStockThreshold=5),
            _product(id='p4', name='Borrado', category='drink', isActive=False),
        ]

    def test_list_filters_category_and_lowstock_and_meta(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.return_value = self._products()
        client = make_client(mock)

        response = client.get(
            '/api/products?category=drink&lowStock=true&page=1&limit=20',
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.get_json()
        # p2 es drink con stock bajo (0 < 3 <= 5); p1 no es bajo, p4 borrado, p3 otra categoría
        assert [p['id'] for p in data['data']] == ['p2']
        assert data['meta'] == {'total': 1, 'page': 1, 'limit': 20, 'pages': 1}
        # Solo igualdad de businessId en Firestore (máximo 1 filtro)
        filters = mock.query_firestore.call_args[1]['filters']
        assert filters == [{'field': 'businessId', 'operator': '==', 'value': 'biz-1'}]

    def test_list_excludes_deleted_and_sorts_by_name(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = self._products()
        client = make_client(mock)

        response = client.get('/api/products', headers=auth_header)

        ids = [p['id'] for p in response.get_json()['data']]
        assert 'p4' not in ids                 # isActive:false → excluido
        assert ids == ['p1', 'p3', 'p2']       # Agua, Camiseta, Jugo (nombre ASC)

    def test_list_search_by_name(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = self._products()
        client = make_client(mock)

        response = client.get('/api/products?search=jug', headers=auth_header)

        assert [p['id'] for p in response.get_json()['data']] == ['p2']

    def test_list_pagination(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = [
            _product(id=f'p{i}', name=f'Producto {i}', businessId='biz-1', branchId='branch-1')
            for i in range(5)
        ]
        client = make_client(mock)

        response = client.get('/api/products?page=2&limit=2', headers=auth_header)

        data = response.get_json()
        assert len(data['data']) == 2
        assert data['meta'] == {'total': 5, 'page': 2, 'limit': 2, 'pages': 3}

    def test_branch_scoped_user_filters_own_branch(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-1')
        mock.query_firestore.return_value = [
            _product(id='a', businessId='biz-1', branchId='branch-1'),
            _product(id='b', businessId='biz-1', branchId='branch-2'),
        ]
        client = make_client(mock)

        response = client.get('/api/products', headers=auth_header)

        assert [p['id'] for p in response.get_json()['data']] == ['a']


# ============================================================================
# POST /api/products
# ============================================================================

class TestCreateProduct:

    def test_create_valid_201(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.create_document.return_value = {'id': 'new-1', 'name': 'Proteína'}
        client = make_client(mock)

        response = client.post(
            '/api/products',
            json={'name': 'Proteína', 'category': 'supplement',
                  'costPriceCents': 1500, 'salePriceCents': 2500, 'branchId': 'branch-1'},
            headers=auth_header,
        )

        assert response.status_code == 201
        assert response.get_json()['success'] is True
        collection, record = mock.create_document.call_args[0]
        assert collection == 'products'
        assert record['category'] == 'supplement'
        assert record['stockQty'] == 0
        assert record['lowStockThreshold'] == 5
        assert record['businessId'] == 'biz-1'
        assert record['branchId'] == 'branch-1'
        assert record['isActive'] is True
        assert record['registeredBy'] == 'user-123'
        assert {
            'name', 'category', 'costPriceCents', 'salePriceCents', 'stockQty',
            'lowStockThreshold', 'businessId', 'branchId', 'isActive',
            'registeredBy', 'registeredByName', 'createdAt',
        } <= set(record)

    def test_create_with_initial_stock_creates_purchase_movement(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.create_document.return_value = {'id': 'new-1', 'name': 'Proteína'}
        client = make_client(mock)

        response = client.post(
            '/api/products',
            json={'name': 'Proteína', 'category': 'supplement', 'costPriceCents': 1500,
                  'salePriceCents': 2500, 'stockQty': 10},
            headers=auth_header,
        )

        assert response.status_code == 201
        assert mock.create_document.call_count == 2
        first = mock.create_document.call_args_list[0][0]
        second = mock.create_document.call_args_list[1][0]
        assert first[0] == 'products'
        assert second[0] == 'product_movements'
        movement = second[1]
        assert movement['type'] == 'purchase'
        assert movement['qty'] == 10
        assert movement['unitPriceCents'] == 1500
        assert movement['totalCents'] == 15000
        assert movement['productId'] == 'new-1'

    def test_create_without_stock_no_movement(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.create_document.return_value = {'id': 'new-1'}
        client = make_client(mock)

        response = client.post(
            '/api/products',
            json={'name': 'Proteína', 'category': 'supplement', 'costPriceCents': 1500,
                  'salePriceCents': 2500, 'stockQty': 0},
            headers=auth_header,
        )

        assert response.status_code == 201
        assert mock.create_document.call_count == 1
        assert mock.create_document.call_args[0][0] == 'products'

    def test_create_invalid_category_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post(
            '/api/products',
            json={'name': 'Comida', 'category': 'food', 'costPriceCents': 100, 'salePriceCents': 200},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    @pytest.mark.parametrize('payload', [
        {'category': 'supplement', 'costPriceCents': 100, 'salePriceCents': 200},          # sin name
        {'name': 'X', 'category': 'supplement', 'costPriceCents': 100, 'salePriceCents': 0},  # sale 0
        {'name': 'X', 'category': 'supplement', 'costPriceCents': -1, 'salePriceCents': 200}, # cost -1
        {'name': 'X', 'category': 'supplement', 'costPriceCents': 100, 'salePriceCents': 200,
         'stockQty': -1},                                                                    # stock -1
    ])
    def test_create_invalid_input_400(self, make_client, auth_header, payload):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = client.post('/api/products', json=payload, headers=auth_header)

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_create_cross_branch_403(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-1')
        client = make_client(mock)

        response = client.post(
            '/api/products',
            json={'name': 'X', 'category': 'supplement', 'costPriceCents': 100,
                  'salePriceCents': 200, 'branchId': 'branch-2'},
            headers=auth_header,
        )

        assert response.status_code == 403
        mock.create_document.assert_not_called()


# ============================================================================
# PUT / DELETE /api/products/<id>
# ============================================================================

class TestUpdateAndDeleteProduct:

    def test_update_fields_200(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = _product()
        client = make_client(mock)

        response = client.put(
            '/api/products/p1',
            json={'name': 'Proteína Premium', 'salePriceCents': 3000},
            headers=auth_header,
        )

        assert response.status_code == 200
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'products'
        assert doc_id == 'p1'
        assert update == {'name': 'Proteína Premium', 'salePriceCents': 3000}

    def test_update_invalid_sale_price_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = _product()
        client = make_client(mock)

        response = client.put('/api/products/p1', json={'salePriceCents': 0}, headers=auth_header)

        assert response.status_code == 400
        mock.update_document.assert_not_called()

    def test_update_missing_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = None
        client = make_client(mock)

        response = client.put('/api/products/ghost', json={'name': 'X'}, headers=auth_header)

        assert response.status_code == 404
        mock.update_document.assert_not_called()

    def test_update_deleted_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = _product(isActive=False)
        client = make_client(mock)

        response = client.put('/api/products/p1', json={'name': 'X'}, headers=auth_header)

        assert response.status_code == 404
        mock.update_document.assert_not_called()

    def test_update_cross_branch_403(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-2')
        mock.get_document.return_value = _product()  # branch-1
        client = make_client(mock)

        response = client.put('/api/products/p1', json={'name': 'X'}, headers=auth_header)

        assert response.status_code == 403
        mock.update_document.assert_not_called()

    def test_soft_delete_audit_preserved(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = _product()
        client = make_client(mock)

        response = client.delete('/api/products/p1', headers=auth_header)

        assert response.status_code == 200
        collection, doc_id, update = mock.update_document.call_args[0]
        assert collection == 'products'
        assert doc_id == 'p1'
        assert update['isActive'] is False
        assert update['deletedBy'] == 'user-123'
        assert update['deletedAt']
        mock.delete_document.assert_not_called()

    def test_delete_missing_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.get_document.return_value = None
        client = make_client(mock)

        assert client.delete('/api/products/ghost', headers=auth_header).status_code == 404

    def test_deleted_product_excluded_from_list_and_summary(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = [
            _product(id='p1', stockQty=10, costPriceCents=1000),
            _product(id='p2', stockQty=99, costPriceCents=1000, isActive=False),
        ]
        client = make_client(mock)

        listed = client.get('/api/products', headers=auth_header).get_json()['data']
        summary = client.get('/api/products/summary', headers=auth_header).get_json()['data']

        assert [p['id'] for p in listed] == ['p1']
        assert summary['totalProducts'] == 1
        assert summary['totalStockValue'] == 10000


# ============================================================================
# GET /api/products/summary
# ============================================================================

class TestProductsSummary:

    def test_summary_counters_one_query(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = [
            _product(id='ok', stockQty=20, lowStockThreshold=5, costPriceCents=1000),   # normal
            _product(id='low', stockQty=3, lowStockThreshold=5, costPriceCents=2000),   # bajo
            _product(id='out', stockQty=0, lowStockThreshold=5, costPriceCents=500),    # agotado
            _product(id='del', stockQty=50, isActive=False),                            # borrado
        ]
        client = make_client(mock)

        response = client.get('/api/products/summary', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['totalProducts'] == 3
        assert data['totalStockValue'] == 20 * 1000 + 3 * 2000 + 0 * 500  # 26000
        assert data['lowStockCount'] == 1
        assert data['outOfStockCount'] == 1

        # UNA sola query scoped a products
        calls = mock.query_firestore.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == 'products'
        assert calls[0][1]['filters'] == [
            {'field': 'businessId', 'operator': '==', 'value': 'biz-1'}
        ]

    def test_summary_empty_returns_zeroes(self, make_client, auth_header):
        mock = create_mock_service(role='admin')
        mock.query_firestore.return_value = []
        client = make_client(mock)

        data = client.get('/api/products/summary', headers=auth_header).get_json()['data']

        assert data == {
            'totalProducts': 0, 'totalStockValue': 0,
            'lowStockCount': 0, 'outOfStockCount': 0,
        }


# ============================================================================
# GET /api/products/<id>
# ============================================================================

class TestGetProduct:

    def test_get_product_200(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product(id='p1')
        client = make_client(mock)

        response = client.get('/api/products/p1', headers=auth_header)

        assert response.status_code == 200
        body = response.get_json()
        assert body['success'] is True
        assert body['data']['id'] == 'p1'
        assert body['data']['name'] == 'Proteína Whey'
        mock.get_document.assert_called_once_with('products', 'p1')

    def test_get_product_missing_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = None
        client = make_client(mock)

        response = client.get('/api/products/ghost', headers=auth_header)

        assert response.status_code == 404
        assert response.get_json()['success'] is False

    def test_get_product_soft_deleted_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product(isActive=False)
        client = make_client(mock)

        assert client.get('/api/products/p1', headers=auth_header).status_code == 404

    def test_get_product_out_of_scope_403(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-2')
        mock.get_document.return_value = _product()  # branch-1
        client = make_client(mock)

        assert client.get('/api/products/p1', headers=auth_header).status_code == 403

    @pytest.mark.parametrize('role', ['super_admin', 'admin', 'branch_admin', 'cashier', 'trainer'])
    def test_all_roles_can_get_detail_200(self, make_client, auth_header, role):
        mock = create_mock_service(role=role, business_id='biz-1')
        mock.get_document.return_value = _product(businessId='biz-1')
        client = make_client(mock)

        assert client.get('/api/products/p1', headers=auth_header).status_code == 200


# ============================================================================
# Movimientos (/api/products/<id>/movement[s])
# ============================================================================

class TestMovements:

    def test_purchase_with_method_and_payment_account(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=0)
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'purchase', 'qty': 4, 'unitPriceCents': 900,
                  'method': 'transfer', 'paymentAccountId': 'acc-bank-1'},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, movement = mock.create_document.call_args[0]
        assert movement['type'] == 'purchase'
        assert movement['method'] == 'transfer'
        assert movement['paymentAccountId'] == 'acc-bank-1'

    def test_purchase_default_method_cash(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=0)
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'purchase', 'qty': 1, 'unitPriceCents': 100},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, movement = mock.create_document.call_args[0]
        assert movement['method'] == 'cash'
        assert movement['paymentAccountId'] is None

    def test_invalid_method_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=0)
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'purchase', 'qty': 1, 'unitPriceCents': 100, 'method': 'bitcoin'},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_purchase_increases_stock_and_updates_cost(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=0, costPriceCents=1500)
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'purchase', 'qty': 10, 'unitPriceCents': 1500, 'updateCostPrice': True},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, movement = mock.create_document.call_args[0]
        assert movement['type'] == 'purchase'
        assert movement['unitPriceCents'] == 1500
        _, doc_id, update = mock.update_document.call_args[0]
        assert doc_id == 'p1'
        assert update == {'stockQty': 10, 'costPriceCents': 1500, 'totalCostCents': 15000}

    def test_purchase_without_cost_update_keeps_product_cost(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=0, costPriceCents=1500)
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'purchase', 'qty': 4, 'unitPriceCents': 900},
            headers=auth_header,
        )

        assert response.status_code == 201
        _, _, update = mock.update_document.call_args[0]
        assert update == {'stockQty': 4, 'totalCostCents': 3600}

    def test_cashier_cannot_purchase_403(self, make_client, auth_header):
        mock = create_mock_service(role='cashier', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=0)
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'purchase', 'qty': 1, 'unitPriceCents': 100},
            headers=auth_header,
        )

        assert response.status_code == 403
        mock.create_document.assert_not_called()

    def test_trainer_cannot_purchase_403(self, make_client, auth_header):
        mock = create_mock_service(role='trainer', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=0)
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'purchase', 'qty': 1, 'unitPriceCents': 100},
            headers=auth_header,
        )

        assert response.status_code == 403

    def test_purchase_requires_unit_price_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=0)
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'purchase', 'qty': 2},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    @pytest.mark.parametrize('mtype', ['sale', 'loss'])
    def test_invalid_type_400(self, make_client, auth_header, mtype):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': mtype, 'qty': 1},
            headers=auth_header,
        )

        assert response.status_code == 400

    def test_sale_type_rejected_400(self, make_client, auth_header):
        """Las ventas ya no son movimientos: `type:'sale'` → 400 (usar POST /api/sales)."""
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'sale', 'qty': 1, 'unitPriceCents': 2500},
            headers=auth_header,
        )

        assert response.status_code == 400
        mock.create_document.assert_not_called()

    def test_movement_missing_product_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = None
        client = make_client(mock)

        response = client.post(
            '/api/products/ghost/movement',
            json={'type': 'purchase', 'qty': 1, 'unitPriceCents': 100},
            headers=auth_header,
        )

        assert response.status_code == 404

    def test_movements_are_immutable_405(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product()
        client = make_client(mock)

        put = client.put('/api/products/p1/movement', json={'qty': 1}, headers=auth_header)
        delete = client.delete('/api/products/p1/movement', headers=auth_header)

        assert put.status_code in (404, 405)
        assert delete.status_code in (404, 405)

    def test_purchase_does_not_write_expenses(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product(stockQty=0)
        client = make_client(mock)

        response = client.post(
            '/api/products/p1/movement',
            json={'type': 'purchase', 'qty': 5, 'unitPriceCents': 1000},
            headers=auth_header,
        )

        assert response.status_code == 201
        # Ninguna escritura debe apuntar a la colección `expenses`.
        write_collections = (
            [c[0][0] for c in mock.create_document.call_args_list]
            + [c[0][0] for c in mock.update_document.call_args_list]
        )
        assert 'expenses' not in write_collections

    def test_movements_history_date_desc(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = _product()
        mock.query_firestore.return_value = [
            {'id': 'mv1', 'productId': 'p1', 'type': 'purchase', 'qty': 1,
             'date': '2026-10-01', 'businessId': 'biz-1'},
            {'id': 'mv2', 'productId': 'p1', 'type': 'purchase', 'qty': 5,
             'date': '2026-10-10', 'businessId': 'biz-1'},
        ]
        client = make_client(mock)

        response = client.get('/api/products/p1/movements', headers=auth_header)

        assert response.status_code == 200
        body = response.get_json()
        assert [m['id'] for m in body['data']] == ['mv2', 'mv1']
        assert body['meta'] == {'total': 2, 'page': 1, 'limit': 20, 'pages': 1}

    def test_movements_history_missing_product_404(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.get_document.return_value = None
        client = make_client(mock)

        assert client.get('/api/products/ghost/movements', headers=auth_header).status_code == 404


# ============================================================================
# GET /api/products/report
# ============================================================================

class TestProductsReport:

    def test_report_reads_sales_and_purchases_two_queries(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')

        def q(collection, filters=None, **kwargs):
            if collection == 'sales':
                return [
                    {'id': 's1', 'totalCents': 5000, 'date': '2026-10-01',
                     'businessId': 'biz-1', 'branchId': 'branch-1'},
                    {'id': 's2', 'totalCents': 2500, 'date': '2026-10-02',
                     'businessId': 'biz-1', 'branchId': 'branch-1'},
                    # fuera de rango → excluido
                    {'id': 's3', 'totalCents': 9999, 'date': '2026-09-01',
                     'businessId': 'biz-1', 'branchId': 'branch-1'},
                ]
            if collection == 'product_movements':
                return [
                    {'id': 'm1', 'type': 'purchase', 'totalCents': 15000, 'date': '2026-10-01',
                     'businessId': 'biz-1', 'branchId': 'branch-1'},
                    {'id': 'm2', 'type': 'purchase', 'totalCents': 3000, 'date': '2026-10-02',
                     'businessId': 'biz-1', 'branchId': 'branch-1'},
                    # legacy sale en movements → ignorado (las ventas viven en `sales`)
                    {'id': 'm3', 'type': 'sale', 'totalCents': 99999, 'date': '2026-10-01',
                     'businessId': 'biz-1', 'branchId': 'branch-1'},
                ]
            return []

        mock.query_firestore.side_effect = q
        client = make_client(mock)

        response = client.get(
            '/api/products/report?startDate=2026-10-01&endDate=2026-10-31',
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['sales'] == {'count': 2, 'totalCents': 7500}
        assert data['purchases'] == {'count': 2, 'totalCents': 18000}
        assert data['net'] == 7500 - 18000
        assert data['daily'] == [
            {'date': '2026-10-01', 'salesCents': 5000, 'purchasesCents': 15000},
            {'date': '2026-10-02', 'salesCents': 2500, 'purchasesCents': 3000},
        ]
        # DOS queries scoped: `sales` + `product_movements`
        calls = mock.query_firestore.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == 'sales'
        assert calls[1][0][0] == 'product_movements'
        assert calls[0][1]['filters'] == [
            {'field': 'businessId', 'operator': '==', 'value': 'biz-1'}
        ]
        assert calls[1][1]['filters'] == [
            {'field': 'businessId', 'operator': '==', 'value': 'biz-1'}
        ]

    def test_report_empty_returns_zeroes(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        mock.query_firestore.return_value = []
        client = make_client(mock)

        data = client.get('/api/products/report', headers=auth_header).get_json()['data']

        assert data == {
            'sales': {'count': 0, 'totalCents': 0},
            'purchases': {'count': 0, 'totalCents': 0},
            'net': 0,
            'daily': [],
        }

    def test_report_invalid_date_400(self, make_client, auth_header):
        mock = create_mock_service(role='admin', business_id='biz-1')
        client = make_client(mock)

        response = client.get('/api/products/report?startDate=01-2026', headers=auth_header)

        assert response.status_code == 400
        mock.query_firestore.assert_not_called()

    def test_report_branch_scoped_user_filters_own_branch(self, make_client, auth_header):
        mock = create_mock_service(role='branch_admin', business_id='biz-1', branch_id='branch-1')

        def q(collection, filters=None, **kwargs):
            if collection == 'sales':
                return [
                    {'id': 'a', 'totalCents': 1000, 'date': '2026-10-01',
                     'businessId': 'biz-1', 'branchId': 'branch-1'},
                    {'id': 'b', 'totalCents': 99999, 'date': '2026-10-01',
                     'businessId': 'biz-1', 'branchId': 'branch-2'},
                ]
            return []

        mock.query_firestore.side_effect = q
        client = make_client(mock)

        data = client.get('/api/products/report', headers=auth_header).get_json()['data']

        assert data['sales'] == {'count': 1, 'totalCents': 1000}


# ============================================================================
# Permisos
# ============================================================================

class TestPermissions:

    @pytest.mark.parametrize('method,path', [
        ('post', '/api/products'),
        ('put', '/api/products/p1'),
        ('delete', '/api/products/p1'),
    ])
    @pytest.mark.parametrize('role', ['cashier', 'trainer'])
    def test_non_admin_catalog_writes_403(self, make_client, auth_header, method, path, role):
        mock = create_mock_service(role=role)
        client = make_client(mock)

        response = getattr(client, method)(path, headers=auth_header, json={})

        assert response.status_code == 403
        assert response.get_json()['success'] is False

    @pytest.mark.parametrize('role', ['super_admin', 'admin', 'branch_admin', 'cashier', 'trainer'])
    def test_all_roles_can_list_and_summary_200(self, make_client, auth_header, role):
        mock = create_mock_service(role=role, business_id='biz-1')
        mock.query_firestore.return_value = []
        client = make_client(mock)

        assert client.get('/api/products', headers=auth_header).status_code == 200
        assert client.get('/api/products/summary', headers=auth_header).status_code == 200
        assert client.get('/api/products/report', headers=auth_header).status_code == 200

    @pytest.mark.parametrize('method,path', [
        ('get', '/api/products'),
        ('get', '/api/products/summary'),
        ('get', '/api/products/report'),
        ('get', '/api/products/p1'),
        ('post', '/api/products'),
        ('put', '/api/products/p1'),
        ('delete', '/api/products/p1'),
        ('post', '/api/products/p1/movement'),
    ])
    def test_unauth_returns_401(self, make_client, method, path):
        mock = create_mock_service(role='admin')
        client = make_client(mock)

        response = getattr(client, method)(path, json={})

        assert response.status_code == 401
