"""
Modelos y validaciones para Clientes
"""
from typing import Optional, Dict, Any
from datetime import datetime
import re

class ClientModel:
    """Modelo de cliente para Firestore"""
    
    # Campos requeridos
    REQUIRED_FIELDS = ['name', 'email', 'phone', 'branchId', 'businessId', 'membershipPlanId']
    
    # Campos opcionales
    OPTIONAL_FIELDS = ['documentId', 'notes']
    
    @staticmethod
    def validate_create_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para crear cliente"""
        errors = []
        
        # Validar campos requeridos
        for field in ClientModel.REQUIRED_FIELDS:
            if field not in data or not data[field]:
                errors.append(f"El campo '{field}' es requerido")
        
        # Validar formato de email
        if 'email' in data:
            email = data['email'].strip()
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                errors.append("El email no tiene un formato válido")
            data['email'] = email.lower()
        
        # Validar teléfono (formato básico)
        if 'phone' in data:
            phone = data['phone'].strip()
            if not re.match(r'^[\d\s\-\+\(\)]+$', phone):
                errors.append("El teléfono solo puede contener dígitos, espacios, guiones y +")
            data['phone'] = phone
        
        # Validar nombre
        if 'name' in data:
            name = data['name'].strip()
            if len(name) < 3:
                errors.append("El nombre debe tener al menos 3 caracteres")
            if len(name) > 100:
                errors.append("El nombre no puede exceder 100 caracteres")
            data['name'] = name
        
        # Validar notas (si existen)
        if 'notes' in data and data['notes']:
            notes = data['notes'].strip()
            if len(notes) > 500:
                errors.append("Las notas no pueden exceder 500 caracteres")
            data['notes'] = notes
        
        if errors:
            raise ValueError({"errors": errors})
        
        # Agregar campos automáticos
        data['isActive'] = True
        data['status'] = 'active'
        
        return data
    
    @staticmethod
    def validate_update_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para actualizar cliente"""
        errors = []
        
        # Campos permitidos para actualizar
        allowed_fields = ['name', 'email', 'phone', 'documentId', 'notes', 'status']
        
        # Filtrar campos no permitidos
        invalid_fields = [field for field in data.keys() if field not in allowed_fields]
        if invalid_fields:
            errors.append(f"Campos no permitidos para actualización: {', '.join(invalid_fields)}")
        
        # Validar status si está presente
        if 'status' in data:
            valid_statuses = ['active', 'expired', 'suspended']
            if data['status'] not in valid_statuses:
                errors.append(f"Status debe ser uno de: {', '.join(valid_statuses)}")
        
        # Reutilizar validaciones de create
        if 'email' in data:
            email = data['email'].strip()
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                errors.append("El email no tiene un formato válido")
            data['email'] = email.lower()
        
        if 'phone' in data:
            phone = data['phone'].strip()
            if not re.match(r'^[\d\s\-\+\(\)]+$', phone):
                errors.append("El teléfono solo puede contener dígitos, espacios, guiones y +")
            data['phone'] = phone
        
        if 'name' in data:
            name = data['name'].strip()
            if len(name) < 3:
                errors.append("El nombre debe tener al menos 3 caracteres")
            if len(name) > 100:
                errors.append("El nombre no puede exceder 100 caracteres")
            data['name'] = name
        
        if errors:
            raise ValueError({"errors": errors})
        
        return data
    
    @staticmethod
    def from_firestore(doc_data: Dict[str, Any], doc_id: str) -> Dict[str, Any]:
        """Convierte documento de Firestore a modelo de cliente"""
        client = doc_data.copy()
        client['id'] = doc_id
        
        # Convertir timestamps a strings si es necesario
        for field in ['membershipStart', 'membershipEnd', 'createdAt']:
            if field in client and hasattr(client[field], 'isoformat'):
                client[field] = client[field].isoformat()
        
        return client
    
    @staticmethod
    def to_firestore(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte modelo de cliente a formato Firestore"""
        firestore_data = data.copy()
        
        # Eliminar campos que no se guardan en Firestore
        firestore_data.pop('id', None)
        
        return firestore_data

class ClientCreateSchema:
    """Schema para creación de clientes"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = ClientModel.validate_create_data(data)
    
    def to_dict(self) -> Dict[str, Any]:
        return self.data

class ClientUpdateSchema:
    """Schema para actualización de clientes"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = ClientModel.validate_update_data(data)
    
    def to_dict(self) -> Dict[str, Any]:
        return self.data
