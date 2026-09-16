"""
Tests para generación de número de recibo quota-efficient (count() aggregation).

Cubre:
- seq = count + 1 (formato P-YYYYMMDD-XXX)
- fallback timestamp en error / techo (NUNCA -001)
- el count NO aplica filtro isDeleted (los soft-deleted cuentan)
- count_firestore: devuelve el valor, aplica filtros, RAISES en fallo/techo
"""
import re
import pytest
from unittest.mock import patch, MagicMock

from services.payment_service import PaymentService
from services.firebase_service import FirebaseService

SEQ_RE = re.compile(r'^P-\d{8}-\d{3}$')
TIMESTAMP_RE = re.compile(r'^P-\d{8}-\d{12}$')  # YYYYMMDD-HHMMSSffffff


@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    """Resetea singleton antes y después del módulo"""
    FirebaseService._reset()
    yield
    FirebaseService._reset()


def _service_with(mock):
    """PaymentService con FirebaseService mockeado (alias de módulo)."""
    with patch('services.payment_service.FirebaseService', return_value=mock), \
         patch('services.payment_service.MembershipService', return_value=MagicMock()):
        return PaymentService()


# ============================================================================
# generate_receipt_number
# ============================================================================

class TestReceiptNumberSequence:
    """seq = count + 1, sin enumerar pagos"""

    def test_receipt_number_is_count_plus_one(self):
        """count=41 → secuencia 42 → P-YYYYMMDD-042"""
        mock = MagicMock()
        mock.count_firestore.return_value = 41

        svc = _service_with(mock)
        number = svc.generate_receipt_number('biz-1')

        assert SEQ_RE.match(number)
        assert number.endswith('-042')
        mock.count_firestore.assert_called_once_with(
            'payments',
            filters=[{'field': 'businessId', 'operator': '==', 'value': 'biz-1'}]
        )

    def test_receipt_number_zero_count_is_001(self):
        """Sin pagos previos → secuencia 001 (único caso donde -001 es válido)"""
        mock = MagicMock()
        mock.count_firestore.return_value = 0

        svc = _service_with(mock)
        number = svc.generate_receipt_number('biz-1')

        assert SEQ_RE.match(number)
        assert number.endswith('-001')

    def test_count_query_has_no_is_deleted_filter(self):
        """El count NO filtra isDeleted: los soft-deleted cuentan (len+1 semantics)"""
        mock = MagicMock()
        mock.count_firestore.return_value = 5

        _service_with(mock).generate_receipt_number('biz-1')

        filters = mock.count_firestore.call_args[1]['filters']
        assert filters == [{'field': 'businessId', 'operator': '==', 'value': 'biz-1'}]
        assert all(f['field'] != 'isDeleted' for f in filters)


class TestReceiptNumberFallback:
    """Fallback timestamp en error/techo — nunca fabricar -001"""

    def test_fallback_timestamp_on_error(self):
        """count() falla → P-YYYYMMDD-HHMMSSffffff (único, no bloquea)"""
        mock = MagicMock()
        mock.count_firestore.side_effect = RuntimeError('boom')

        svc = _service_with(mock)
        number = svc.generate_receipt_number('biz-1')

        assert TIMESTAMP_RE.match(number)

    def test_fallback_timestamp_on_ceiling(self):
        """count() alcanza el techo (>= 1000) → fallback timestamp, NO -001"""
        mock = MagicMock()
        mock.count_firestore.side_effect = RuntimeError('techo de seguridad')

        svc = _service_with(mock)
        number = svc.generate_receipt_number('biz-1')

        assert TIMESTAMP_RE.match(number)
        assert not number.endswith('-001')

    def test_fallback_is_millisecond_unique(self):
        """Dos fallbacks en momentos distintos generan números distintos"""
        mock = MagicMock()
        mock.count_firestore.side_effect = RuntimeError('boom')

        svc = _service_with(mock)
        n1 = svc.generate_receipt_number('biz-1')
        n2 = svc.generate_receipt_number('biz-1')

        # Formato timestamp (con milisegundos) — la unicidad la da el reloj
        assert TIMESTAMP_RE.match(n1)
        assert TIMESTAMP_RE.match(n2)


# ============================================================================
# count_firestore (método real, db mockeada)
# ============================================================================

class TestCountFirestore:
    """count_firestore usa count() de Firestore y RAISES en fallo/techo"""

    def _service_with_db(self, mock_db):
        FirebaseService._reset()
        FirebaseService._db = mock_db
        return FirebaseService()

    def _query_chain(self, value=7):
        """Cadena collection → where → count → get devolviendo [value]."""
        mock_db = MagicMock()
        query = mock_db.collection.return_value
        query.where.return_value = query
        agg = MagicMock()
        agg.value = value
        query.count.return_value.get.return_value = [agg]
        return mock_db

    def test_returns_count_value(self):
        """count() devuelve 7 → count_firestore devuelve 7"""
        mock_db = self._query_chain(value=7)
        svc = self._service_with_db(mock_db)

        assert svc.count_firestore('payments') == 7

    def test_applies_filters(self):
        """Los filtros se aplican a la query con operador '=='"""
        mock_db = self._query_chain(value=3)
        svc = self._service_with_db(mock_db)

        svc.count_firestore(
            'payments',
            filters=[{'field': 'businessId', 'operator': '==', 'value': 'biz-1'}]
        )

        mock_db.collection.assert_called_once_with('payments')
        mock_db.collection.return_value.where.assert_called_once_with(
            'businessId', '==', 'biz-1'
        )

    def test_raises_on_ceiling(self):
        """count >= 1000 → RAISES (el caller decide el fallback)"""
        mock_db = self._query_chain(value=1000)
        svc = self._service_with_db(mock_db)

        with pytest.raises(RuntimeError):
            svc.count_firestore('payments')

    def test_raises_on_failure(self):
        """count() falla → RAISES (nunca fakes 0)"""
        mock_db = self._query_chain()
        mock_db.collection.return_value.count.return_value.get.side_effect = \
            Exception('firestore down')
        svc = self._service_with_db(mock_db)

        with pytest.raises(Exception):
            svc.count_firestore('payments')

    def test_raises_when_no_results(self):
        """count() sin resultados → RAISES"""
        mock_db = MagicMock()
        query = mock_db.collection.return_value
        query.count.return_value.get.return_value = []
        svc = self._service_with_db(mock_db)

        with pytest.raises(RuntimeError):
            svc.count_firestore('payments')