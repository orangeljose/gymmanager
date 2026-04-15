"""
Validadores de datos para GymManager
"""
import re
from typing import Dict, Any, List

def validate_email(email: str) -> bool:
    """
    Valida formato de email
    
    Args:
        email: Email a validar
        
    Returns:
        True si el formato es válido
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip().lower()))

def validate_phone(phone: str) -> bool:
    """
    Valida formato de teléfono (básico)
    
    Args:
        phone: Teléfono a validar
        
    Returns:
        True si el formato es válido
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Permitir dígitos, espacios, guiones, paréntesis y +
    pattern = r'^[\d\s\-\+\(\)]+$'
    return bool(re.match(pattern, phone.strip()))

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    Valida que todos los campos requeridos estén presentes y no vacíos
    
    Args:
        data: Diccionario de datos
        required_fields: Lista de campos requeridos
        
    Returns:
        Lista de errores (vacía si todo es válido)
    """
    errors = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            errors.append(f"El campo '{field}' es requerido")
    
    return errors

def validate_length(value: str, field_name: str, min_length: int = 0, max_length: int = 255) -> List[str]:
    """
    Valida longitud de un campo de texto
    
    Args:
        value: Valor a validar
        field_name: Nombre del campo (para mensajes de error)
        min_length: Longitud mínima
        max_length: Longitud máxima
        
    Returns:
        Lista de errores (vacía si todo es válido)
    """
    errors = []
    
    if not isinstance(value, str):
        errors.append(f"El campo '{field_name}' debe ser texto")
        return errors
    
    value = value.strip()
    
    if len(value) < min_length:
        errors.append(f"El campo '{field_name}' debe tener al menos {min_length} caracteres")
    
    if len(value) > max_length:
        errors.append(f"El campo '{field_name}' no puede exceder {max_length} caracteres")
    
    return errors

def validate_positive_integer(value: Any, field_name: str) -> List[str]:
    """
    Valida que un valor sea un entero positivo
    
    Args:
        value: Valor a validar
        field_name: Nombre del campo (para mensajes de error)
        
    Returns:
        Lista de errores (vacía si todo es válido)
    """
    errors = []
    
    if not isinstance(value, int):
        errors.append(f"El campo '{field_name}' debe ser un número entero")
        return errors
    
    if value <= 0:
        errors.append(f"El campo '{field_name}' debe ser un número positivo")
    
    return errors

def validate_choice(value: str, field_name: str, choices: List[str]) -> List[str]:
    """
    Valida que un valor esté en una lista de opciones válidas
    
    Args:
        value: Valor a validar
        field_name: Nombre del campo (para mensajes de error)
        choices: Lista de opciones válidas
        
    Returns:
        Lista de errores (vacía si todo es válido)
    """
    errors = []
    
    if value not in choices:
        errors.append(f"El campo '{field_name}' debe ser uno de: {', '.join(choices)}")
    
    return errors

def validate_date_format(date_str: str, field_name: str) -> List[str]:
    """
    Valida formato de fecha YYYY-MM-DD
    
    Args:
        date_str: Fecha en formato string
        field_name: Nombre del campo (para mensajes de error)
        
    Returns:
        Lista de errores (vacía si todo es válido)
    """
    errors = []
    
    if not isinstance(date_str, str):
        errors.append(f"El campo '{field_name}' debe ser texto")
        return errors
    
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str.strip()):
        errors.append(f"El campo '{field_name}' debe tener formato YYYY-MM-DD")
    
    return errors

def sanitize_string(value: str) -> str:
    """
    Limpia y sanitiza un string
    
    Args:
        value: String a limpiar
        
    Returns:
        String limpio
    """
    if not isinstance(value, str):
        return value
    
    # Eliminar espacios extra
    value = ' '.join(value.split())
    
    # Eliminar caracteres potencialmente peligrosos (básico)
    dangerous_chars = ['<', '>', '"', "'", '&', 'script', 'javascript']
    for char in dangerous_chars:
        value = value.replace(char, '')
    
    return value.strip()

def validate_pagination(page: int = None, limit: int = None) -> Dict[str, Any]:
    """
    Valida parámetros de paginación
    
    Args:
        page: Número de página
        limit: Límite de resultados
        
    Returns:
        Dict con valores validados y por defecto
    """
    # Valores por defecto
    validated_page = 1
    validated_limit = 20
    
    # Validar página
    if page is not None:
        if isinstance(page, int) and page > 0:
            validated_page = page
    
    # Validar límite
    if limit is not None:
        if isinstance(limit, int) and 0 < limit <= 100:
            validated_limit = limit
    
    # Calcular offset
    offset = (validated_page - 1) * validated_limit
    
    return {
        'page': validated_page,
        'limit': validated_limit,
        'offset': offset
    }
