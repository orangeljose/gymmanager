"""
Ruta de subida de imágenes.

POST /api/uploads  (multipart/form-data)
  file    -> archivo (JPG/PNG/WebP, <= 5 MB)
  folder  -> clients | products | machines | businesses
  businessId -> solo super_admin (negocio seleccionado en el header)

La respuesta es { success, data: { url, publicId, width, height, format, bytes } }.
"""
import logging

from flask import Blueprint, g, jsonify, request

from middleware.auth_middleware import require_auth, require_role
from services import storage_service

logger = logging.getLogger(__name__)

uploads_bp = Blueprint('uploads', __name__, url_prefix='/api/uploads')

UPLOAD_ROLES = ['super_admin', 'admin', 'branch_admin']


def _error(code: int, message: str):
    return jsonify({'success': False, 'error': {'code': code, 'message': message}}), code


@uploads_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(UPLOAD_ROLES)
def upload_image():
    """Sube una imagen y devuelve su URL pública."""
    file = request.files.get('file')
    folder = (request.form.get('folder') or '').strip()

    role = g.current_user.get('role')
    business_id = g.current_user.get('businessId')
    if role == 'super_admin':
        # super_admin no tiene negocio propio: usa el seleccionado en el header.
        business_id = (request.form.get('businessId') or '').strip() or None

    if not business_id:
        return _error(400, 'Selecciona un negocio antes de subir imágenes')

    try:
        result = storage_service.upload_image(file, business_id, folder)
    except storage_service.StorageUnavailableError:
        logger.error('Intento de subida sin Cloudinary configurado')
        return _error(503, 'La subida de imágenes no está configurada')
    except storage_service.InvalidImageError as exc:
        return _error(400, str(exc))
    except Exception as exc:
        logger.error('Error subiendo imagen: %s', exc, exc_info=True)
        return _error(500, 'No se pudo subir la imagen')

    return jsonify({'success': True, 'data': result}), 201
