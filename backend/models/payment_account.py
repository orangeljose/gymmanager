"""
Modelos y validaciones para Cuentas de Pago Destino
"""
from typing import Dict, Any, List


class PaymentAccountModel:
    """Modelo de cuenta de pago destino para Firestore"""

    VALID_TYPES = ['zelle', 'pago_movil', 'bank']

    REQUIRED_FIELDS = ['type', 'identifier', 'businessId']

    @staticmethod
    def validate_create_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para crear una cuenta de pago"""
        errors = []

        for field in PaymentAccountModel.REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                errors.append(f"El campo '{field}' es requerido")

        acct_type = data.get('type')
        if acct_type not in PaymentAccountModel.VALID_TYPES:
            errors.append(f"Tipo de cuenta debe ser uno de: {', '.join(PaymentAccountModel.VALID_TYPES)}")

        identifier = data.get('identifier')
        if not identifier or not identifier.strip():
            errors.append("El identificador es requerido")
        else:
            identifier = identifier.strip()

            if acct_type == 'zelle':
                if '@' not in identifier or '.' not in identifier:
                    errors.append("El email de Zelle no es válido")
                data['identifier'] = identifier.lower()

            elif acct_type == 'pago_movil':
                clean_phone = identifier.replace('+', '').replace(' ', '').replace('-', '')
                if not clean_phone.isdigit() or len(clean_phone) < 10:
                    errors.append("El número de teléfono para pago móvil no es válido")
                data['identifier'] = identifier

            elif acct_type == 'bank':
                if len(identifier) < 4:
                    errors.append("El número de cuenta bancaria no es válido")
                data['identifier'] = identifier

        label = data.get('label')
        if label:
            label = label.strip()
            if len(label) > 50:
                errors.append("El alias no puede exceder 50 caracteres")
            data['label'] = label
        else:
            if identifier and acct_type == 'zelle':
                data['label'] = identifier.split('@')[0] if '@' in identifier else identifier
            elif identifier and acct_type == 'pago_movil':
                data['label'] = identifier
            elif identifier and acct_type == 'bank':
                data['label'] = 'Cuenta bancaria'
            else:
                data['label'] = 'Cuenta sin nombre'

        if 'description' in data and data['description']:
            desc = data['description'].strip()
            if len(desc) > 200:
                errors.append("La descripción no puede exceder 200 caracteres")
            data['description'] = desc

        if errors:
            raise ValueError({"errors": errors})

        data.setdefault('isActive', True)

        return data

    @staticmethod
    def validate_update_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para actualizar una cuenta"""
        errors = []

        allowed_fields = ['identifier', 'label', 'description', 'isActive']
        invalid_fields = [field for field in data.keys() if field not in allowed_fields]
        if invalid_fields:
            errors.append(f"Campos no permitidos: {', '.join(invalid_fields)}")

        identifier = data.get('identifier')
        if identifier:
            identifier = identifier.strip()
            data['identifier'] = identifier

        label = data.get('label')
        if label:
            label = label.strip()
            if len(label) > 50:
                errors.append("El alias no puede exceder 50 caracteres")
            data['label'] = label

        if 'description' in data and data['description']:
            desc = data['description'].strip()
            if len(desc) > 200:
                errors.append("La descripción no puede exceder 200 caracteres")
            data['description'] = desc

        if 'isActive' in data:
            if not isinstance(data['isActive'], bool):
                errors.append("isActive debe ser un valor booleano")

        if errors:
            raise ValueError({"errors": errors})

        return data

    @staticmethod
    def from_firestore(doc_data: Dict[str, Any], doc_id: str) -> Dict[str, Any]:
        """Convierte documento de Firestore a modelo"""
        account = doc_data.copy()
        account['id'] = doc_id
        if 'createdAt' in account and hasattr(account['createdAt'], 'isoformat'):
            account['createdAt'] = account['createdAt'].isoformat()
        return account


class PaymentAccountCreateSchema:
    def __init__(self, data: Dict[str, Any]):
        self.data = PaymentAccountModel.validate_create_data(data)

    def to_dict(self) -> Dict[str, Any]:
        return self.data


class PaymentAccountUpdateSchema:
    def __init__(self, data: Dict[str, Any]):
        self.data = PaymentAccountModel.validate_update_data(data)

    def to_dict(self) -> Dict[str, Any]:
        return self.data