"""
Servicio para gestión de membresías y planes
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .firebase_service import FirebaseService

logger = logging.getLogger(__name__)

class MembershipService:
    """Servicio para lógica de membresías"""
    
    def __init__(self):
        self.firebase_service = FirebaseService()
    
    def get_plan_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un plan de membresía por ID
        
        Args:
            plan_id: ID del plan
            
        Returns:
            Dict con datos del plan o None si no existe
        """
        try:
            plan = self.firebase_service.get_document('membership_plans', plan_id)
            
            if plan:
                logger.info(f"Plan encontrado: {plan_id}")
            else:
                logger.warning(f"Plan no encontrado: {plan_id}")
            
            return plan
            
        except Exception as e:
            logger.error(f"Error obteniendo plan {plan_id}: {str(e)}")
            return None
    
    def validate_payment_amount(self, client_id: str, amount: int, plan_id: str) -> bool:
        """
        Valida que el monto del pago coincida con el precio del plan
        
        Args:
            client_id: ID del cliente
            amount: Monto del pago en cents
            plan_id: ID del plan
            
        Returns:
            True si el monto es correcto
        """
        try:
            # Obtener plan
            plan = self.get_plan_by_id(plan_id)
            if not plan:
                logger.error(f"Plan no encontrado para validación: {plan_id}")
                return False
            
            # Validar monto
            expected_amount = plan.get('price', 0)
            if amount != expected_amount:
                logger.warning(
                    f"Monto incorrecto para cliente {client_id}: "
                    f"esperado {expected_amount}, recibido {amount}"
                )
                return False
            
            logger.info(f"Monto validado correctamente para cliente {client_id}: {amount}")
            return True
            
        except Exception as e:
            logger.error(f"Error validando monto para cliente {client_id}: {str(e)}")
            return False
    
    def calculate_new_end_date(
        self, 
        current_end: Optional[datetime] = None, 
        duration_days: int = 30
    ) -> datetime:
        """
        Calcula la nueva fecha de vencimiento
        
        Args:
            current_end: Fecha actual de vencimiento (None para usar hoy)
            duration_days: Días de duración del plan
            
        Returns:
            Nueva fecha de vencimiento
        """
        try:
            # Usar fecha actual si no hay fecha de vencimiento
            if current_end is None:
                start_date = datetime.now()
            else:
                # Si la membresía ya venció, empezar desde hoy
                if current_end < datetime.now():
                    start_date = datetime.now()
                else:
                    start_date = current_end
            
            # Calcular nueva fecha
            new_end = start_date + timedelta(days=duration_days)
            
            logger.info(f"Nueva fecha de vencimiento calculada: {new_end}")
            return new_end
            
        except Exception as e:
            logger.error(f"Error calculando nueva fecha de vencimiento: {str(e)}")
            raise
    
    def extend_membership(
        self, 
        client_id: str, 
        plan_id: str, 
        months_paid: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Extiende la membresía de un cliente
        
        Args:
            client_id: ID del cliente
            plan_id: ID del plan
            months_paid: Meses pagados (para planes de múltiples meses)
            
        Returns:
            Dict con nuevas fechas o None si hay error
        """
        try:
            # Obtener cliente actual
            client = self.firebase_service.get_document('clients', client_id)
            if not client:
                logger.error(f"Cliente no encontrado para extender membresía: {client_id}")
                return None
            
            # Obtener plan
            plan = self.get_plan_by_id(plan_id)
            if not plan:
                logger.error(f"Plan no encontrado para extender membresía: {plan_id}")
                return None
            
            # Calcular duración total en días
            duration_days = plan.get('durationDays', 30) * months_paid
            
            # Obtener fecha actual de vencimiento
            current_end_str = client.get('membershipEnd')
            current_end = None
            if current_end_str:
                # Convertir string a datetime si es necesario
                if isinstance(current_end_str, str):
                    current_end = datetime.fromisoformat(current_end_str.replace('Z', '+00:00'))
                else:
                    current_end = current_end_str
            
            # Calcular nueva fecha de vencimiento
            new_end = self.calculate_new_end_date(current_end, duration_days)
            
            # Preparar datos de actualización
            update_data = {
                'membershipPlanId': plan_id,
                'membershipEnd': new_end,
                'status': 'active',
                'isActive': True
            }
            
            # Si es una nueva membresía o estaba vencida, actualizar start
            if current_end is None or current_end < datetime.now():
                update_data['membershipStart'] = datetime.now()
            
            # Actualizar cliente
            success = self.firebase_service.update_document('clients', client_id, update_data)
            
            if success:
                logger.info(f"Membresía extendida para cliente {client_id}")
                return {
                    'membershipStart': update_data.get('membershipStart'),
                    'membershipEnd': new_end,
                    'status': 'active'
                }
            else:
                logger.error(f"No se pudo extender membresía para cliente {client_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error extendiendo membresía para cliente {client_id}: {str(e)}")
            return None
    
    def get_client_membership_status(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado actual de la membresía de un cliente
        
        Args:
            client_id: ID del cliente
            
        Returns:
            Dict con información del estado o None si hay error
        """
        try:
            client = self.firebase_service.get_document('clients', client_id)
            if not client:
                return None
            
            # Obtener fecha de vencimiento
            membership_end_str = client.get('membershipEnd')
            if not membership_end_str:
                return {
                    'status': 'no_membership',
                    'days_overdue': None,
                    'is_active': False
                }
            
            # Convertir fecha
            if isinstance(membership_end_str, str):
                membership_end = datetime.fromisoformat(membership_end_str.replace('Z', '+00:00'))
            else:
                membership_end = membership_end_str
            
            # Calcular estado
            now = datetime.now()
            is_active = membership_end > now
            
            if is_active:
                days_overdue = 0
                status = 'active'
            else:
                days_overdue = (now - membership_end).days
                status = 'expired'
            
            return {
                'status': status,
                'days_overdue': days_overdue,
                'is_active': is_active,
                'membership_end': membership_end
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de membresía para cliente {client_id}: {str(e)}")
            return None
