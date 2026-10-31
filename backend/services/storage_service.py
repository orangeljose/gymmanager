"""
Servicio de almacenamiento de imágenes (Cloudinary).

Responsabilidades:
- Configurar el SDK desde variables de entorno.
- Validar tipo y tamaño del archivo.
- Subir imágenes organizadas por negocio y sección.
- Eliminar imágenes por public_id (best-effort).

Las credenciales NUNCA salen del backend: el frontend solo recibe la URL final.
"""
import logging
import os
import re
import uuid

import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)

# Secciones permitidas -> evita rutas arbitrarias en el bucket.
ALLOWED_FOLDERS = {'clients', 'products', 'machines', 'businesses'}
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_WIDTH = 1600  # se guarda una sola versión acotada; las variantes se piden por URL

ENV_KEYS = ('CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET')


class InvalidImageError(ValueError):
    """Archivo rechazado por tipo, tamaño o carpeta."""


class StorageUnavailableError(RuntimeError):
    """Cloudinary no está configurado en el entorno."""


def is_configured() -> bool:
    """True si las tres credenciales de Cloudinary están presentes."""
    return all(os.environ.get(key) for key in ENV_KEYS)


def _ensure_configured() -> None:
    if not is_configured():
        raise StorageUnavailableError('La subida de imágenes no está configurada')
    cloudinary.config(
        cloud_name=os.environ['CLOUDINARY_CLOUD_NAME'],
        api_key=os.environ['CLOUDINARY_API_KEY'],
        api_secret=os.environ['CLOUDINARY_API_SECRET'],
        secure=True,
    )


def _file_size(file) -> int:
    stream = file.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    return size


def _validate(file, business_id: str, folder: str) -> None:
    if not business_id:
        raise InvalidImageError('No se pudo determinar el negocio')
    if folder not in ALLOWED_FOLDERS:
        raise InvalidImageError(
            f'Carpeta inválida. Usá una de: {", ".join(sorted(ALLOWED_FOLDERS))}'
        )
    if not file or not file.filename:
        raise InvalidImageError('Se requiere un archivo')

    extension = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if extension not in ALLOWED_EXTENSIONS:
        raise InvalidImageError('Formato no permitido. Usá JPG, PNG o WebP')

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidImageError('Formato no permitido. Usá JPG, PNG o WebP')

    if _file_size(file) > MAX_BYTES:
        raise InvalidImageError('La imagen supera el máximo de 5 MB')


def upload_image(file, business_id: str, folder: str) -> dict:
    """
    Sube una imagen a Cloudinary y devuelve sus datos públicos.

    Args:
        file: FileStorage de Flask.
        business_id: negocio dueño de la imagen (sale del token, no del body).
        folder: una de ALLOWED_FOLDERS.

    Returns:
        dict con url, publicId, width, height, format y bytes.

    Raises:
        StorageUnavailableError: credenciales ausentes.
        InvalidImageError: archivo inválido.
    """
    _ensure_configured()
    _validate(file, business_id, folder)

    result = cloudinary.uploader.upload(
        file.stream,
        folder=f'gymmanager/{business_id}/{folder}',
        public_id=uuid.uuid4().hex,
        resource_type='image',
        overwrite=False,
        # Una sola versión acotada a 1600px de ancho; las miniaturas se piden por URL.
        transformation=[{'width': MAX_WIDTH, 'crop': 'limit'}],
        # Borra EXIF/IPTC/XMP del asset almacenado (incluye GPS). Las
        # transformaciones de entrega ya los quitan, pero la URL original
        # también debe quedar limpia.
        flags='force_strip',
    )

    return {
        'url': result.get('secure_url'),
        'publicId': result.get('public_id'),
        'width': result.get('width'),
        'height': result.get('height'),
        'format': result.get('format'),
        'bytes': result.get('bytes'),
    }


def delete_image(public_id: str) -> bool:
    """Elimina una imagen de Cloudinary. No lanza: devuelve False si falla."""
    if not public_id or not is_configured():
        return False
    try:
        _ensure_configured()
        cloudinary.uploader.destroy(public_id, invalidate=True)
        return True
    except Exception as exc:  # best-effort: no debe romper el flujo principal
        logger.warning('No se pudo eliminar la imagen %s: %s', public_id, exc)
        return False


def public_id_from_url(url: str) -> str | None:
    """
    Extrae el public_id de una URL de Cloudinary.

    Acepta tanto la URL base como cualquier variante transformada:
      .../image/upload/v123/gymmanager/biz/clients/abc.jpg
      .../image/upload/w_240,h_240,c_fill/v123/gymmanager/biz/clients/abc.jpg

    Devuelve None si la URL no es de nuestro árbol (gymmanager/...).
    """
    if not url or 'res.cloudinary.com' not in url or '/image/upload/' not in url:
        return None

    tail = url.split('/image/upload/', 1)[1]
    parts = tail.split('/')

    try:
        start = parts.index('gymmanager')
    except ValueError:
        return None

    public_id = '/'.join(parts[start:])
    # Cloudinary no usa la extensión en el public_id.
    public_id = re.sub(r'\.[A-Za-z0-9]+$', '', public_id)
    return public_id or None


def delete_image_for_url(url: str) -> bool:
    """Borra el asset asociado a una URL de Cloudinary (best-effort)."""
    public_id = public_id_from_url(url)
    if not public_id:
        return False
    return delete_image(public_id)
