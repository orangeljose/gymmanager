"""
Tests de POST /api/uploads.

Cubre dos niveles:
- Ruta: roles, resolución de businessId y mapeo de errores a códigos HTTP.
- Servicio: validaciones de archivo/carpeta y mapeo de la respuesta de Cloudinary.
"""
import io

import pytest
from unittest.mock import MagicMock, patch

from services import storage_service


@pytest.fixture(scope='module', autouse=True)
def reset_singleton():
    from services import firebase_service
    firebase_service.FirebaseService._reset()
    yield
    firebase_service.FirebaseService._reset()


def create_mock_service(role='admin', uid='user-123', business_id='biz-1'):
    user_data = {
        'uid': uid,
        'email': f'{role}@test.com',
        'name': f'{role.title()} Test',
        'role': role,
        'businessId': None if role == 'super_admin' else business_id,
        'branchId': None if role == 'super_admin' else 'branch-1',
        'permissions': ['*'] if role == 'super_admin' else [],
        'isActive': True,
    }
    mock = MagicMock()
    mock.verify_token.return_value = {'uid': uid}
    mock.get_user_by_uid.return_value = user_data
    mock.query_firestore.return_value = []
    mock.get_document.return_value = None
    return mock


def _post_upload(mock, form_data, headers=None):
    with patch('services.firebase_service.FirebaseService', return_value=mock), \
         patch('middleware.auth_middleware.FirebaseService', return_value=mock):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()
        return client.post(
            '/api/uploads',
            data=form_data,
            content_type='multipart/form-data',
            headers=headers or {'Authorization': 'Bearer test-token'},
        )


def _file():
    return (io.BytesIO(b'fake-image-bytes'), 'foto.jpg')


# ============================================================================
# RUTA
# ============================================================================

class TestUploadRoute:

    def test_admin_upload_returns_201_and_url(self):
        mock = create_mock_service(role='admin', business_id='biz-1')
        result = {'url': 'https://cdn.test/x.jpg', 'publicId': 'gymmanager/biz-1/clients/x'}

        with patch('routes.uploads.storage_service.upload_image', return_value=result) as upload:
            response = _post_upload(mock, {'folder': 'clients', 'file': _file()})

        assert response.status_code == 201
        body = response.get_json()
        assert body['success'] is True
        assert body['data']['url'] == 'https://cdn.test/x.jpg'
        # El negocio sale del token, no del formulario.
        upload.assert_called_once()
        assert upload.call_args[0][1] == 'biz-1'
        assert upload.call_args[0][2] == 'clients'

    def test_super_admin_without_business_returns_400(self):
        mock = create_mock_service(role='super_admin')

        with patch('routes.uploads.storage_service.upload_image') as upload:
            response = _post_upload(mock, {'folder': 'clients', 'file': _file()})

        assert response.status_code == 400
        assert 'negocio' in response.get_json()['error']['message'].lower()
        upload.assert_not_called()

    def test_super_admin_uses_form_business_id(self):
        mock = create_mock_service(role='super_admin')

        with patch('routes.uploads.storage_service.upload_image',
                   return_value={'url': 'u', 'publicId': 'p'}) as upload:
            response = _post_upload(
                mock,
                {'folder': 'products', 'businessId': 'biz-9', 'file': _file()},
            )

        assert response.status_code == 201
        assert upload.call_args[0][1] == 'biz-9'

    def test_cashier_is_forbidden(self):
        mock = create_mock_service(role='cashier', business_id='biz-1')

        with patch('routes.uploads.storage_service.upload_image') as upload:
            response = _post_upload(mock, {'folder': 'clients', 'file': _file()})

        assert response.status_code == 403
        upload.assert_not_called()

    def test_storage_not_configured_returns_503(self):
        mock = create_mock_service(role='admin')

        with patch('routes.uploads.storage_service.upload_image',
                   side_effect=storage_service.StorageUnavailableError()):
            response = _post_upload(mock, {'folder': 'clients', 'file': _file()})

        assert response.status_code == 503

    def test_invalid_image_returns_400(self):
        mock = create_mock_service(role='admin')

        with patch('routes.uploads.storage_service.upload_image',
                   side_effect=storage_service.InvalidImageError('Formato no permitido')):
            response = _post_upload(mock, {'folder': 'clients', 'file': _file()})

        assert response.status_code == 400
        assert 'Formato' in response.get_json()['error']['message']


# ============================================================================
# SERVICIO
# ============================================================================

class TestStorageServiceValidation:

    def _file_storage(self, filename='foto.jpg', content=b'x', content_type='image/jpeg'):
        from werkzeug.datastructures import FileStorage
        return FileStorage(stream=io.BytesIO(content), filename=filename,
                           content_type=content_type)

    def test_invalid_folder_rejected(self):
        with pytest.raises(storage_service.InvalidImageError):
            storage_service._validate(self._file_storage(), 'biz-1', 'hackers')

    def test_missing_business_rejected(self):
        with pytest.raises(storage_service.InvalidImageError):
            storage_service._validate(self._file_storage(), '', 'clients')

    def test_invalid_extension_rejected(self):
        with pytest.raises(storage_service.InvalidImageError):
            storage_service._validate(self._file_storage(filename='virus.exe'), 'biz-1', 'clients')

    def test_oversized_file_rejected(self, monkeypatch):
        monkeypatch.setattr(storage_service, 'MAX_BYTES', 10)
        with pytest.raises(storage_service.InvalidImageError):
            storage_service._validate(
                self._file_storage(content=b'x' * 11), 'biz-1', 'clients'
            )

    def test_valid_file_passes(self):
        storage_service._validate(self._file_storage(), 'biz-1', 'clients')


class TestStorageServiceUpload:

    def test_upload_maps_cloudinary_response(self, monkeypatch):
        monkeypatch.setenv('CLOUDINARY_CLOUD_NAME', 'demo')
        monkeypatch.setenv('CLOUDINARY_API_KEY', 'key')
        monkeypatch.setenv('CLOUDINARY_API_SECRET', 'secret')

        fake = {
            'secure_url': 'https://res.cloudinary.com/demo/x.jpg',
            'public_id': 'gymmanager/biz-1/clients/abc',
            'width': 800, 'height': 600, 'format': 'jpg', 'bytes': 1234,
        }
        from werkzeug.datastructures import FileStorage

        with patch('services.storage_service.cloudinary.uploader.upload', return_value=fake) as up:
            result = storage_service.upload_image(
                FileStorage(stream=io.BytesIO(b'x'), filename='foto.jpg',
                            content_type='image/jpeg'),
                'biz-1', 'clients',
            )

        assert result['url'] == fake['secure_url']
        assert result['publicId'] == fake['public_id']
        assert up.call_args.kwargs['folder'] == 'gymmanager/biz-1/clients'
        # El asset almacenado debe quedar sin EXIF/IPTC/XMP (incluye GPS).
        assert up.call_args.kwargs['flags'] == 'force_strip'

    def test_delete_without_config_returns_false(self, monkeypatch):
        for key in storage_service.ENV_KEYS:
            monkeypatch.delenv(key, raising=False)
        assert storage_service.delete_image('abc') is False
