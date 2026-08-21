"""
Tests unitarios para MembershipService.recalculate_membership y _advance_end.

Cubre la paridad con extend_membership (misma primitiva _advance_end) y los
escenarios de recálculo: sin pagos, único pago, acumulativo, gap con re-anclaje,
monthsPaid, exclusión de eliminados y fallback paymentDate -> createdAt.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from services.membership_service import MembershipService

UTC = timezone.utc


def dt(y, m, d):
    return datetime(y, m, d, tzinfo=UTC)


def iso(value):
    return value.isoformat()


def make_service(firebase_mock):
    with patch('services.membership_service.FirebaseService', return_value=firebase_mock):
        return MembershipService()


def plan(duration_days=30):
    return {'id': 'plan-1', 'name': 'Mensual', 'price': 35000, 'durationDays': duration_days}


def payment(pid, payment_date, plan_id='plan-1', months_paid=1, is_deleted=False, created_at=None):
    p = {'id': pid, 'clientId': 'c1', 'membershipPlanId': plan_id, 'monthsPaid': months_paid}
    if payment_date is not None:
        p['paymentDate'] = payment_date
    if created_at is not None:
        p['createdAt'] = created_at
    if is_deleted:
        p['isDeleted'] = True
    return p


class TestAdvanceEnd:
    """Primitiva compartida por extend_membership y recalculate_membership."""

    def test_none_end_anchors(self):
        svc = make_service(MagicMock())
        assert svc._advance_end(None, 30, dt(2026, 1, 1)) == dt(2026, 1, 31)

    def test_past_end_reanchors(self):
        svc = make_service(MagicMock())
        assert svc._advance_end(dt(2026, 1, 1), 30, dt(2026, 1, 15)) == dt(2026, 2, 14)

    def test_future_end_extends_cumulatively(self):
        svc = make_service(MagicMock())
        assert svc._advance_end(dt(2026, 1, 10), 30, dt(2026, 1, 1)) == dt(2026, 2, 9)


class TestCalculateNewEndDatePreservesBehavior:
    """Verifica que el refactor a _advance_end no cambió extend_membership."""

    def test_future_end_extends(self):
        svc = make_service(MagicMock())
        future = datetime.now(UTC) + timedelta(days=10)
        assert svc.calculate_new_end_date(future, 30) == future + timedelta(days=30)

    def test_none_end_anchors_to_now(self):
        svc = make_service(MagicMock())
        before = datetime.now(UTC)
        result = svc.calculate_new_end_date(None, 30)
        after = datetime.now(UTC)
        assert result > before + timedelta(days=29)
        assert result < after + timedelta(days=31)


class TestRecalculateMembership:
    """Paridad de recálculo con la regla acumulativa de extend_membership."""

    def _setup(self, payments):
        firebase = MagicMock()
        firebase.get_document.return_value = {'id': 'c1', 'isActive': True}
        firebase.query_firestore.return_value = payments
        firebase.update_document.return_value = True
        svc = make_service(firebase)
        svc.get_plan_by_id = lambda pid: plan() if pid == 'plan-1' else None
        return svc, firebase

    def test_no_payments_expires(self):
        svc, firebase = self._setup([])
        result = svc.recalculate_membership('c1')
        assert result['isActive'] is False
        assert result['status'] == 'expired'
        assert result['membershipStart'] is None
        assert result['membershipEnd'] is None
        assert result['membershipPlanId'] is None
        update = firebase.update_document.call_args[0][2]
        assert update['isActive'] is False
        assert update['status'] == 'expired'

    def test_single_payment(self):
        svc, _ = self._setup([payment('p1', iso(dt(2026, 1, 1)))])
        result = svc.recalculate_membership('c1')
        assert result['membershipStart'] == iso(dt(2026, 1, 1))
        assert result['membershipEnd'] == iso(dt(2026, 1, 31))

    def test_multiple_cumulative(self):
        svc, _ = self._setup([
            payment('p1', iso(dt(2026, 1, 1))),
            payment('p2', iso(dt(2026, 1, 20))),
        ])
        result = svc.recalculate_membership('c1')
        assert result['membershipStart'] == iso(dt(2026, 1, 1))
        # running end: max(Jan31, Jan20) + 30 = Jan31 + 30 = Mar2
        assert result['membershipEnd'] == iso(dt(2026, 3, 2))

    def test_gap_reanchors(self):
        svc, _ = self._setup([
            payment('p1', iso(dt(2026, 1, 1))),
            payment('p2', iso(dt(2026, 3, 15))),
        ])
        result = svc.recalculate_membership('c1')
        assert result['membershipStart'] == iso(dt(2026, 1, 1))
        # p1 ends Jan31 (< Mar15) -> re-anchor Mar15 -> Apr14
        assert result['membershipEnd'] == iso(dt(2026, 4, 14))

    def test_months_paid_multiplies_duration(self):
        svc, _ = self._setup([payment('p1', iso(dt(2026, 1, 1)), months_paid=2)])
        result = svc.recalculate_membership('c1')
        assert result['membershipEnd'] == iso(dt(2026, 3, 2))

    def test_excludes_deleted_payments(self):
        svc, _ = self._setup([
            payment('p1', iso(dt(2026, 1, 1))),
            payment('p2', iso(dt(2026, 2, 1)), is_deleted=True),
        ])
        result = svc.recalculate_membership('c1')
        assert result['membershipEnd'] == iso(dt(2026, 1, 31))

    def test_fallback_to_created_at_when_payment_date_missing(self):
        svc, _ = self._setup([payment('p1', None, created_at=dt(2026, 2, 1))])
        result = svc.recalculate_membership('c1')
        assert result['membershipStart'] == iso(dt(2026, 2, 1))
        assert result['membershipEnd'] == iso(dt(2026, 3, 3))

    def test_sort_prefers_payment_date_over_created_at(self):
        p1 = payment('p1', iso(dt(2026, 2, 1)), created_at=dt(2026, 1, 1))
        p2 = payment('p2', iso(dt(2026, 1, 1)), created_at=dt(2026, 2, 1))
        svc, _ = self._setup([p1, p2])
        result = svc.recalculate_membership('c1')
        # sorted by paymentDate -> p2 (Jan1) primero
        assert result['membershipStart'] == iso(dt(2026, 1, 1))
        # Jan1+30=Jan31; luego max(Jan31, Feb1)+30 = Feb1+30 = Mar3
        assert result['membershipEnd'] == iso(dt(2026, 3, 3))

    def test_active_when_end_in_future(self):
        future = datetime.now(UTC) + timedelta(days=60)
        svc, _ = self._setup([payment('p1', future.isoformat())])
        result = svc.recalculate_membership('c1')
        assert result['isActive'] is True
        assert result['status'] == 'active'

    def test_expired_when_end_in_past(self):
        past = datetime.now(UTC) - timedelta(days=60)
        svc, _ = self._setup([payment('p1', past.isoformat())])
        result = svc.recalculate_membership('c1')
        assert result['isActive'] is False
        assert result['status'] == 'expired'
