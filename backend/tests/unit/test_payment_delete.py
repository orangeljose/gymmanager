"""
Tests unitarios para PaymentService.delete_payment y filtrado isDeleted.

Cubre: status envelope (not_found/forbidden/success), verificación de sede en
línea, persistencia de monthsPaid/isDeleted en register_payment y filtrado de
pagos eliminados en get_client_payments / get_payment_report.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch, MagicMock

from services.payment_service import PaymentService


def make_service(firebase_mock, membership_mock=None):
    membership_mock = membership_mock or MagicMock()
    with patch('services.payment_service.FirebaseService', return_value=firebase_mock), \
         patch('services.payment_service.MembershipService', return_value=membership_mock):
        svc = PaymentService()
    svc.membership_service = membership_mock
    return svc, membership_mock


def user(role='super_admin', branch_id=None):
    return {
        'uid': 'u1',
        'role': role,
        'branchId': branch_id,
        'businessId': 'biz-1',
        'name': 'Test User',
    }


class TestDeletePayment:
    def test_not_found_when_missing(self):
        firebase = MagicMock()
        firebase.get_document.return_value = None
        svc, _ = make_service(firebase)
        result = svc.delete_payment('p1', user())
        assert result['status'] == 'not_found'
        firebase.update_document.assert_not_called()

    def test_not_found_when_already_deleted(self):
        firebase = MagicMock()
        firebase.get_document.return_value = {'id': 'p1', 'isDeleted': True}
        svc, _ = make_service(firebase)
        result = svc.delete_payment('p1', user())
        assert result['status'] == 'not_found'
        firebase.update_document.assert_not_called()

    def test_forbidden_cross_branch(self):
        firebase = MagicMock()
        firebase.get_document.return_value = {'id': 'p1', 'branchId': 'branch-1', 'clientId': 'c1'}
        svc, _ = make_service(firebase)
        result = svc.delete_payment('p1', user(role='branch_admin', branch_id='branch-2'))
        assert result['status'] == 'forbidden'
        firebase.update_document.assert_not_called()

    def test_success_super_admin(self):
        firebase = MagicMock()
        firebase.get_document.return_value = {'id': 'p1', 'branchId': 'branch-1', 'clientId': 'c1'}
        firebase.update_document.return_value = True
        membership = MagicMock()
        membership.recalculate_membership.return_value = {'clientId': 'c1', 'isActive': False, 'status': 'expired'}
        svc, membership = make_service(firebase, membership)
        result = svc.delete_payment('p1', user())
        assert result['status'] == 'success'
        firebase.update_document.assert_called_once_with('payments', 'p1', {'isDeleted': True})
        membership.recalculate_membership.assert_called_once_with('c1')

    def test_success_admin_without_branch_cross_branch(self):
        firebase = MagicMock()
        firebase.get_document.return_value = {'id': 'p1', 'branchId': 'branch-1', 'clientId': 'c1'}
        firebase.update_document.return_value = True
        svc, _ = make_service(firebase)
        result = svc.delete_payment('p1', user(role='admin', branch_id=None))
        assert result['status'] == 'success'
        firebase.update_document.assert_called_once_with('payments', 'p1', {'isDeleted': True})


class TestIsDeletedFiltering:
    def test_get_client_payments_filters_deleted(self):
        firebase = MagicMock()
        firebase.query_firestore.return_value = [
            {'id': 'p1', 'isDeleted': True},
            {'id': 'p2', 'isDeleted': False},
            {'id': 'p3'},  # campo ausente -> activo
        ]
        svc, _ = make_service(firebase)
        result = svc.get_client_payments('c1')
        assert [p['id'] for p in result] == ['p2', 'p3']

    def test_get_payment_report_filters_deleted(self):
        firebase = MagicMock()
        firebase.query_firestore.return_value = [
            {'id': 'p1', 'isDeleted': True, 'amount': 100},
            {'id': 'p2', 'amount': 200},
        ]
        svc, _ = make_service(firebase)
        result = svc.get_payment_report('2026-01-01', '2026-01-31')
        assert result['summary']['totalPayments'] == 1
        assert result['summary']['totalAmount'] == 200


class TestRegisterPaymentPersistence:
    def _register(self, data, current_user):
        firebase = MagicMock()
        firebase.get_document.return_value = {'id': 'c1', 'isActive': True, 'businessId': 'biz-1', 'name': 'Juan'}
        firebase.query_firestore.return_value = []
        firebase.create_document.return_value = {'id': 'p1'}
        membership = MagicMock()
        membership.validate_payment_amount.return_value = True
        membership.extend_membership.return_value = {
            'membershipStart': '2026-01-01T00:00:00+00:00',
            'membershipEnd': '2026-01-31T00:00:00+00:00',
            'planName': 'Mensual',
            'planPrice': 35000,
        }
        svc, _ = make_service(firebase, membership)
        svc.register_payment(data, current_user)
        return firebase.create_document.call_args[0][1]

    def _base_data(self):
        return {
            'clientId': 'c1',
            'amount': 35000,
            'method': 'cash',
            'membershipPlanId': 'plan-1',
            'branchId': 'branch-1',
        }

    def test_persists_months_paid(self):
        data = self._base_data()
        data['monthsPaid'] = 2
        payment_data = self._register(data, user())
        assert payment_data['monthsPaid'] == 2

    def test_defaults_months_paid_to_one(self):
        payment_data = self._register(self._base_data(), user())
        assert payment_data['monthsPaid'] == 1

    def test_persists_is_deleted_false(self):
        payment_data = self._register(self._base_data(), user())
        assert payment_data['isDeleted'] is False
