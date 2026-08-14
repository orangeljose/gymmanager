"""
Modelos y validaciones para Planes de Membresía
"""
from typing import Dict, Any, List


class PlanModel:
    """Modelo de plan de membresía para Firestore"""

    REQUIRED_FIELDS = ['name', 'price', 'durationDays', 'businessId']

    @staticmethod
    def validate_create_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para crear un plan"""
        errors = []

        for field in PlanModel.REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                errors.append(f"El campo '{field}' es requerido")

        if 'name' in data:
            name = data['name'].strip()
            if len(name) < 2:
                errors.append("El nombre debe tener al menos 2 caracteres")
            if len(name) > 100:
                errors.append("El nombre no puede exceder 100 caracteres")
            data['name'] = name

        if 'price' in data:
            price = data['price']
            if not isinstance(price, int) or price <= 0:
                errors.append("El precio debe ser un número entero positivo en cents")
            elif price > 100000000:
                errors.append("El precio no puede exceder 1,000,000 de cents ($10,000)")

        if 'durationDays' in data:
            duration = data['durationDays']
            if not isinstance(duration, int) or duration <= 0:
                errors.append("La duración debe ser un número entero positivo de días")
            elif duration > 3650:
                errors.append("La duración no puede exceder 3650 días (10 años)")

        if 'description' in data and data['description']:
            desc = data['description'].strip()
            if len(desc) > 500:
                errors.append("La descripción no puede exceder 500 caracteres")
            data['description'] = desc

        if 'benefits' in data and data['benefits']:
            if not isinstance(data['benefits'], list):
                errors.append("Benefits debe ser una lista")
            else:
                cleaned_benefits = []
                for b in data['benefits']:
                    if isinstance(b, str) and b.strip():
                        cleaned_benefits.append(b.strip())
                if len(cleaned_benefits) > 20:
                    errors.append("No puede tener más de 20 beneficios")
                data['benefits'] = cleaned_benefits

        # Validar precios por método (opcional)
        if 'pricesByMethod' in data and data['pricesByMethod']:
            if not isinstance(data['pricesByMethod'], dict):
                errors.append("pricesByMethod debe ser un objeto")
            else:
                valid_methods = ['cash', 'card', 'transfer', 'zelle', 'pago_movil', 'binance', 'other']
                cleaned_prices = {}
                for method, p in data['pricesByMethod'].items():
                    if method not in valid_methods:
                        errors.append(f"Método de pago inválido: {method}")
                        continue
                    if p is None or p == '':
                        continue
                    if not isinstance(p, int) or p <= 0:
                        errors.append(f"El precio para {method} debe ser un número entero positivo en cents")
                        continue
                    cleaned_prices[method] = p
                data['pricesByMethod'] = cleaned_prices

        if errors:
            raise ValueError({"errors": errors})

        data.setdefault('isActive', True)
        data.setdefault('benefits', [])

        return data

    @staticmethod
    def validate_update_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para actualizar un plan"""
        errors = []

        allowed_fields = ['name', 'price', 'durationDays', 'description', 'benefits', 'isActive', 'pricesByMethod']
        invalid_fields = [field for field in data.keys() if field not in allowed_fields]
        if invalid_fields:
            errors.append(f"Campos no permitidos: {', '.join(invalid_fields)}")

        if 'name' in data:
            name = data['name'].strip()
            if len(name) < 2:
                errors.append("El nombre debe tener al menos 2 caracteres")
            if len(name) > 100:
                errors.append("El nombre no puede exceder 100 caracteres")
            data['name'] = name

        if 'price' in data:
            price = data['price']
            if not isinstance(price, int) or price <= 0:
                errors.append("El precio debe ser un número entero positivo en cents")

        if 'durationDays' in data:
            duration = data['durationDays']
            if not isinstance(duration, int) or duration <= 0:
                errors.append("La duración debe ser un número entero positivo de días")

        if 'description' in data:
            desc = data['description'].strip() if data['description'] else None
            if desc and len(desc) > 500:
                errors.append("La descripción no puede exceder 500 caracteres")
            data['description'] = desc

        if 'benefits' in data:
            if not isinstance(data['benefits'], list):
                errors.append("Benefits debe ser una lista")
            else:
                data['benefits'] = [b.strip() for b in data['benefits'] if isinstance(b, str) and b.strip()]

        if 'isActive' in data:
            if not isinstance(data['isActive'], bool):
                errors.append("isActive debe ser un valor booleano")

        if errors:
            raise ValueError({"errors": errors})

        return data

    @staticmethod
    def from_firestore(doc_data: Dict[str, Any], doc_id: str) -> Dict[str, Any]:
        """Convierte documento de Firestore a modelo de plan"""
        plan = doc_data.copy()
        plan['id'] = doc_id
        if 'createdAt' in plan and hasattr(plan['createdAt'], 'isoformat'):
            plan['createdAt'] = plan['createdAt'].isoformat()
        return plan


class PlanCreateSchema:
    def __init__(self, data: Dict[str, Any]):
        self.data = PlanModel.validate_create_data(data)

    def to_dict(self) -> Dict[str, Any]:
        return self.data


class PlanUpdateSchema:
    def __init__(self, data: Dict[str, Any]):
        self.data = PlanModel.validate_update_data(data)

    def to_dict(self) -> Dict[str, Any]:
        return self.data