"""
Modelos y validaciones para Pagos
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import re

class PaymentModel:
    """Modelo de pago para Firestore"""
    
    # Campos requeridos
    REQUIRED_FIELDS = ['clientId', 'amount', 'method', 'membershipPlanId', 'branchId']
    
    # Métodos de pago válidos
    VALID_METHODS = ['cash', 'card', 'transfer', 'other']
    
    @staticmethod
    def validate_create_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para crear pago"""
        errors = []
        
        # Validar campos requeridos
        for field in PaymentModel.REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                errors.append(f"El campo '{field}' es requerido")
        
        # Validar monto (debe ser en cents, entero positivo)
        if 'amount' in data:
            amount = data['amount']
            if not isinstance(amount, int) or amount <= 0:
                errors.append("El monto debe ser un número entero positivo en cents")
        
        # Validar método de pago
        if 'method' in data:
            method = data['method']
            if method not in PaymentModel.VALID_METHODS:
                errors.append(f"Método de pago debe ser uno de: {', '.join(PaymentModel.VALID_METHODS)}")
        
        # Validar methodDetails según método
        if 'methodDetails' in data and data['methodDetails']:
            method_details = data['methodDetails']
            method = data.get('method', 'cash')
            
            if method == 'card':
                # Para tarjeta: cardLast4, transactionId, authorizationCode
                required_card_fields = ['cardLast4']
                for field in required_card_fields:
                    if field not in method_details:
                        errors.append(f"Para pago con tarjeta se requiere '{field}'")
                
                # Validar cardLast4
                if 'cardLast4' in method_details:
                    card_last4 = method_details['cardLast4']
                    if not re.match(r'^\d{4}$', card_last4):
                        errors.append("cardLast4 debe tener exactamente 4 dígitos")
            
            elif method == 'transfer':
                # Para transferencia: reference, bank
                required_transfer_fields = ['reference']
                for field in required_transfer_fields:
                    if field not in method_details:
                        errors.append(f"Para pago por transferencia se requiere '{field}'")
        
        # Validar monthsPaid si está presente
        if 'monthsPaid' in data:
            months_paid = data['monthsPaid']
            if not isinstance(months_paid, int) or months_paid <= 0:
                errors.append("monthsPaid debe ser un número entero positivo")
        
        if errors:
            raise ValueError({"errors": errors})
        
        # Agregar valores por defecto
        data.setdefault('monthsPaid', 1)
        data.setdefault('methodDetails', {})
        
        return data
    
    @staticmethod
    def validate_sync_data(payments_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valida datos para sincronización de pagos offline"""
        errors = []
        validated_payments = []
        
        for i, payment_data in enumerate(payments_list):
            try:
                # Validar cada pago individualmente
                validated_payment = PaymentModel.validate_create_data(payment_data)
                
                # Validar campos adicionales para sync
                if 'localId' not in payment_data:
                    errors.append(f"Pago #{i+1}: 'localId' es requerido para sincronización")
                
                if 'registeredAt' not in payment_data:
                    errors.append(f"Pago #{i+1}: 'registeredAt' es requerido para sincronización")
                
                validated_payment['localId'] = payment_data.get('localId')
                validated_payment['registeredAt'] = payment_data.get('registeredAt')
                
                validated_payments.append(validated_payment)
                
            except ValueError as e:
                error_detail = e.args[0] if e.args else {"errors": ["Error de validación"]}
                if "errors" in error_detail:
                    for error in error_detail["errors"]:
                        errors.append(f"Pago #{i+1}: {error}")
        
        if errors:
            raise ValueError({"errors": errors})
        
        return validated_payments
    
    @staticmethod
    def from_firestore(doc_data: Dict[str, Any], doc_id: str) -> Dict[str, Any]:
        """Convierte documento de Firestore a modelo de pago"""
        payment = doc_data.copy()
        payment['id'] = doc_id
        
        # Convertir timestamps a strings si es necesario
        for field in ['startDate', 'endDate', 'createdAt', 'syncedAt']:
            if field in payment and hasattr(payment[field], 'isoformat'):
                payment[field] = payment[field].isoformat()
        
        return payment
    
    @staticmethod
    def to_firestore(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte modelo de pago a formato Firestore"""
        firestore_data = data.copy()
        
        # Eliminar campos que no se guardan en Firestore
        firestore_data.pop('id', None)
        firestore_data.pop('localId', None)  # Solo para sync
        
        return firestore_data

class PaymentCreateSchema:
    """Schema para creación de pagos"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = PaymentModel.validate_create_data(data)
    
    def to_dict(self) -> Dict[str, Any]:
        return self.data

class PaymentSyncSchema:
    """Schema para sincronización de pagos offline"""
    
    def __init__(self, payments_list: List[Dict[str, Any]]):
        self.data = PaymentModel.validate_sync_data(payments_list)
    
    def to_list(self) -> List[Dict[str, Any]]:
        return self.data
