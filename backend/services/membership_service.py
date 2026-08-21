"""
Servicio para gestión de membresías y planes
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
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
    
    @staticmethod
    def _coerce_datetime(value: Any) -> Optional[datetime]:
        """
        Convierte un valor de fecha (str, Firestore Timestamp o datetime)
        a un datetime timezone-aware en UTC.

        Args:
            value: Valor crudo a convertir

        Returns:
            datetime timezone-aware o None si no se pudo convertir
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        elif hasattr(value, 'to_datetime'):
            # Firestore Timestamp
            dt = value.to_datetime()
        else:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _advance_end(
        self, 
        end_date: Optional[datetime], 
        duration_days: int, 
        anchor_date: datetime
    ) -> datetime:
        """
        Calcula un nuevo fin de membresía con re-anclaje.

        Regla compartida por extend_membership y recalculate_membership:
        el nuevo fin es max(end_date, anchor_date) + duration_days. Si el fin
        actual no existe o ya pasó, la extensión re-ancla en anchor_date.

        Args:
            end_date: Fecha de vencimiento actual (None si no hay)
            duration_days: Días a sumar
            anchor_date: Fecha de anclaje (ahora o la fecha del pago)

        Returns:
            Nueva fecha de vencimiento
        """
        anchor = self._coerce_datetime(anchor_date) or datetime.now(timezone.utc)
        if end_date is None:
            base = anchor
        else:
            end = self._coerce_datetime(end_date) or anchor
            base = max(end, anchor)
        return base + timedelta(days=duration_days)

    def _parse_payment_date(self, payment: Dict[str, Any]) -> datetime:
        """
        Obtiene la fecha efectiva de un pago: paymentDate con fallback a createdAt.

        Args:
            payment: Documento del pago

        Returns:
            datetime timezone-aware (UTC) representativo del pago
        """
        raw = payment.get('paymentDate') or payment.get('createdAt')
        dt = self._coerce_datetime(raw)
        if dt is None:
            dt = datetime.now(timezone.utc)
        return dt

    def calculate_new_end_date(
        self, 
        current_end: Optional[datetime] = None, 
        duration_days: int = 30
    ) -> datetime:
        """
        Calcula la nueva fecha de vencimiento re-anclando en "ahora"
        cuando la membresía ya venció.

        Args:
            current_end: Fecha actual de vencimiento (None para usar hoy)
            duration_days: Días de duración del plan

        Returns:
            Nueva fecha de vencimiento
        """
        try:
            now = datetime.now(timezone.utc)
            new_end = self._advance_end(current_end, duration_days, now)

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
            current_end_raw = client.get('membershipEnd')
            current_end = None
            if current_end_raw:
                # Convertir a datetime timezone-aware
                if isinstance(current_end_raw, str):
                    current_end = datetime.fromisoformat(current_end_raw.replace('Z', '+00:00'))
                elif hasattr(current_end_raw, 'to_datetime'):
                    # Firestore Timestamp
                    current_end = current_end_raw.to_datetime()
                else:
                    current_end = current_end_raw
                # Asegurar timezone-aware
                if current_end and current_end.tzinfo is None:
                    current_end = current_end.replace(tzinfo=timezone.utc)
            
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
            now = datetime.now(timezone.utc)
            if current_end is None:
                update_data['membershipStart'] = now.isoformat()
            else:
                if hasattr(current_end, 'tzinfo') and current_end.tzinfo is not None:
                    if current_end < now:
                        update_data['membershipStart'] = now.isoformat()
                else:
                    if current_end.replace(tzinfo=timezone.utc) < now:
                        update_data['membershipStart'] = now.isoformat()
            
            # Actualizar cliente
            success = self.firebase_service.update_document('clients', client_id, update_data)
            
            if success:
                logger.info(f"Membresía extendida para cliente {client_id}")
                return {
                    'membershipStart': update_data.get('membershipStart'),
                    'membershipEnd': new_end,
                    'status': 'active',
                    'planName': plan.get('name', 'Plan'),
                    'planPrice': plan.get('price', 0)
                }
            else:
                logger.error(f"No se pudo extender membresía para cliente {client_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error extendiendo membresía para cliente {client_id}: {str(e)}")
            return None
    
    def recalculate_membership(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Reconstruye las fechas de membresía de un cliente desde sus pagos
        no eliminados, ordenados cronológicamente (paymentDate → createdAt).

        Aplica la misma regla acumulativa que extend_membership vía
        _advance_end. Si no quedan pagos, deja al cliente sin membresía
        (isActive: False, status: 'expired').

        Args:
            client_id: ID del cliente

        Returns:
            Dict con la membresía recalculada o None si hay error
        """
        try:
            client = self.firebase_service.get_document('clients', client_id)
            if not client:
                logger.error(f"Cliente no encontrado para recalcular membresía: {client_id}")
                return None

            payments = self.firebase_service.query_firestore(
                'payments',
                filters=[{'field': 'clientId', 'operator': '==', 'value': client_id}]
            )

            active = [p for p in payments if not p.get('isDeleted', False)]

            if not active:
                update_data = {
                    'membershipStart': None,
                    'membershipEnd': None,
                    'membershipPlanId': None,
                    'isActive': False,
                    'status': 'expired'
                }
                self.firebase_service.update_document('clients', client_id, update_data)
                logger.info(f"Membresía recalculada (sin pagos) para cliente {client_id}")
                return {'clientId': client_id, **update_data}

            # Ordenar cronológicamente por fecha del pago (fallback createdAt)
            active.sort(key=self._parse_payment_date)

            running_end = None
            last_plan_id = None
            for payment in active:
                plan_id = payment.get('membershipPlanId')
                plan = self.get_plan_by_id(plan_id) if plan_id else None
                if plan:
                    duration_days = plan.get('durationDays', 30) * payment.get('monthsPaid', 1)
                else:
                    logger.warning(
                        f"Plan no encontrado al recalcular ({plan_id}); usando 30 días por defecto"
                    )
                    duration_days = 30 * payment.get('monthsPaid', 1)
                running_end = self._advance_end(
                    running_end, duration_days, self._parse_payment_date(payment)
                )
                last_plan_id = plan_id

            now = datetime.now(timezone.utc)
            is_active = running_end > now
            membership_start = self._parse_payment_date(active[0])

            update_data = {
                'membershipStart': membership_start.isoformat(),
                'membershipEnd': running_end.isoformat(),
                'membershipPlanId': last_plan_id,
                'isActive': is_active,
                'status': 'active' if is_active else 'expired'
            }
            self.firebase_service.update_document('clients', client_id, update_data)
            logger.info(f"Membresía recalculada para cliente {client_id}: {update_data['status']}")
            return {'clientId': client_id, **update_data}

        except Exception as e:
            logger.error(f"Error recalculando membresía para cliente {client_id}: {str(e)}")
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
