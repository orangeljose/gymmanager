"""
Tests de PUT /api/clients/<id>: foto, sede y campos no editables.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    from services import firebase_service
    firebase_service.FirebaseService._reset()
    yield
    firebase_service.FirebaseService._reset()


def create_mock_service(role='admin', business_id='biz-1', branch_id='branch-1'):
    user_data = {
        'uid': 'user-1',
        'email': f'{role}@test.com',
        'name': 'Test User',
        'role': role,
        'businessId': None if role == 'super_admin' else business_id,
        'branchId': None if role == 'super_admin' else branch_id,
        'permissions': ['*'] if role == 'super_admin' else [],
        'isActive': True,
    }

    def _get_document(collection, doc_id):
        if collection == 'clients':
            return {
                'id': doc_id,
                'name': 'Juan',
                'businessId': business_id,
                'branchId': branch_id,
                'isDeleted': False,
            }
        if collection == 'branches':
            if doc_id == 'branch-2':
                return {'id': 'branch-2', 'businessId': business_id, 'name': 'Sede 2'}
            return None
        return None

    mock = MagicMock()
    mock.verify_token.return_value = {'uid': 'user-1'}
    mock.get_user_by_uid.return_value = user_data
    mock.get_document.side_effect = _get_document
    mock.update_document.return_value = True
    mock.query_firestore.return_value = []
    return mock


def _put(mock, body, headers=None):
    with patch('services.firebase_service.FirebaseService', return_value=mock), \
         patch('middleware.auth_middleware.FirebaseService', return_value=mock), \
         patch('routes.clients.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()
        return client.put(
            '/api/clients/c1',
            json=body,
            headers=headers or {'Authorization': 'Bearer test-token'},
        )


class TestUpdateClient:

    def test_update_photo_url(self):
        mock = create_mock_service(role='admin')
        response = _put(mock, {'name': 'Juan', 'photoUrl': 'https://res.cloudinary.com/demo/x.jpg'})

        assert response.status_code == 200
        collection, doc_id, data = mock.update_document.call_args[0]
        assert collection == 'clients'
        assert data['photoUrl'] == 'https://res.cloudinary.com/demo/x.jpg'

    def test_update_rejects_invalid_photo_url(self):
        mock = create_mock_service(role='admin')
        response = _put(mock, {'name': 'Juan', 'photoUrl': 'no-es-url'})

        assert response.status_code == 400
        mock.update_document.assert_not_called()

    def test_update_rejects_membership_plan(self):
        mock = create_mock_service(role='admin')
        response = _put(mock, {'name': 'Juan', 'membershipPlanId': 'plan-1'})

        assert response.status_code == 400
        assert 'membershipPlanId' in response.get_json()['error']['message']

    def test_super_admin_can_change_branch(self):
        mock = create_mock_service(role='super_admin')
        response = _put(mock, {'name': 'Juan', 'branchId': 'branch-2'})

        assert response.status_code == 200
        _, _, data = mock.update_document.call_args[0]
        assert data['branchId'] == 'branch-2'

    def test_change_to_missing_branch_returns_400(self):
        mock = create_mock_service(role='super_admin')
        response = _put(mock, {'name': 'Juan', 'branchId': 'branch-x'})

        assert response.status_code == 400
        assert 'no existe' in response.get_json()['error']['message']
        mock.update_document.assert_not_called()

    def test_branch_admin_is_pinned_to_own_branch(self):
        mock = create_mock_service(role='branch_admin', branch_id='branch-1')
        response = _put(mock, {'name': 'Juan', 'branchId': 'branch-2'})

        assert response.status_code == 200
        _, _, data = mock.update_document.call_args[0]
        assert data['branchId'] == 'branch-1'


class TestPhotoReplacementCleanup:
    """Al reemplazar la foto se borra el asset anterior en Cloudinary."""

    def test_replacing_photo_deletes_previous_asset(self):
        mock = create_mock_service(role='admin')
        old_url = 'https://res.cloudinary.com/demo/image/upload/v1/gymmanager/biz-1/clients/old.jpg'
        new_url = 'https://res.cloudinary.com/demo/image/upload/v2/gymmanager/biz-1/clients/new.jpg'

        # El cliente existente ya tiene una foto.
        def _get_document(collection, doc_id):
            if collection == 'clients':
                return {'id': doc_id, 'name': 'Juan', 'businessId': 'biz-1',
                        'branchId': 'branch-1', 'isDeleted': False, 'photoUrl': old_url}
            if collection == 'branches':
                return {'id': doc_id, 'businessId': 'biz-1', 'name': 'Sede'}
            return None

        mock.get_document.side_effect = _get_document

        with patch('routes.clients.storage_service.delete_image_for_url') as cleanup:
            response = _put(mock, {'name': 'Juan', 'photoUrl': new_url})

        assert response.status_code == 200
        cleanup.assert_called_once_with(old_url)

    def test_removing_photo_deletes_previous_asset(self):
        mock = create_mock_service(role='admin')
        old_url = 'https://res.cloudinary.com/demo/image/upload/v1/gymmanager/biz-1/clients/old.jpg'

        def _get_document(collection, doc_id):
            if collection == 'clients':
                return {'id': doc_id, 'name': 'Juan', 'businessId': 'biz-1',
                        'branchId': 'branch-1', 'isDeleted': False, 'photoUrl': old_url}
            if collection == 'branches':
                return {'id': doc_id, 'businessId': 'biz-1', 'name': 'Sede'}
            return None

        mock.get_document.side_effect = _get_document

        with patch('routes.clients.storage_service.delete_image_for_url') as cleanup:
            response = _put(mock, {'name': 'Juan', 'photoUrl': None})

        assert response.status_code == 200
        cleanup.assert_called_once_with(old_url)
