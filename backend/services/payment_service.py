"""
Servicio para gestión de pagos y sincronización
"""
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from .firebase_service import FirebaseService
from .membership_service import MembershipService

logger = logging.getLogger(__name__)

class PaymentService:
    """Servicio para lógica de pagos"""
    
    def __init__(self):
        self.firebase_service = FirebaseService()
        self.membership_service = MembershipService()
    
    def generate_receipt_number(self, business_id: str) -> str:
        """
        Genera número de recibo único con formato P-YYYYMMDD-XXX
        
        Args:
            business_id: ID del negocio
            
        Returns:
            Número de recibo único
        """
        try:
            # Obtener fecha actual
            today = datetime.now()
            date_str = today.strftime('%Y%m%d')
            
            # Buscar pagos de hoy para este negocio
            filters = [
                {'field': 'businessId', 'operator': '==', 'value': business_id},
                {'field': 'receiptNumber', 'operator': '>=', 'value': f'P-{date_str}'},
                {'field': 'receiptNumber', 'operator': '<', 'value': f'P-{date_str}ZZZ'}
            ]
            
            today_payments = self.firebase_service.query_firestore(
                'payments', 
                filters=filters,
                order_by='receiptNumber',
                direction='DESC'
            )
            
            # Calcular siguiente número
            if today_payments:
                # Extraer el número más alto de hoy
                last_receipt = today_payments[0].get('receiptNumber', f'P-{date_str}-000')
                last_number = int(last_receipt.split('-')[-1])
                next_number = last_number + 1
            else:
                next_number = 1
            
            # Formatear con 3 dígitos
            receipt_number = f'P-{date_str}-{next_number:03d}'
            
            logger.info(f"Receipt number generado: {receipt_number} para negocio {business_id}")
            return receipt_number
            
        except Exception as e:
            logger.error(f"Error generando receipt number: {str(e)}")
            # Fallback a timestamp simple
            timestamp = int(datetime.now().timestamp())
            return f'P-{timestamp}'
    
    def register_payment(self, data: Dict[str, Any], current_user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Registra un nuevo pago con toda la lógica de negocio
        
        Args:
            data: Datos del pago
            current_user: Información del usuario autenticado
            
        Returns:
            Dict con datos del pago creado o None si hay error
        """
        try:
            # Validaciones previas
            client_id = data.get('clientId')
            amount = data.get('amount')
            plan_id = data.get('membershipPlanId')
            branch_id = data.get('branchId')
            
            # Validar cliente existente y activo
            client = self.firebase_service.get_document('clients', client_id)
            if not client:
                logger.error(f"Cliente no encontrado: {client_id}")
                return None
            
            if not client.get('isActive', False):
                logger.error(f"Cliente inactivo: {client_id}")
                return None
            
            # Validar monto contra plan
            if not self.membership_service.validate_payment_amount(client_id, amount, plan_id):
                return None
            
            # Validar que la sede pertenezca al negocio del usuario
            user_business_id = current_user.get('businessId')
            user_branch_id = current_user.get('branchId')
            
            # Validar acceso a la sede
            if current_user.get('role') != 'super_admin':
                if branch_id != user_branch_id:
                    logger.error(f"Usuario no tiene acceso a la sede: {branch_id}")
                    return None
            
            # Obtener información del cliente para denormalización
            client_name = client.get('name', 'Cliente Desconocido')
            
            # Extender membresía del cliente
            months_paid = data.get('monthsPaid', 1)
            membership_update = self.membership_service.extend_membership(
                client_id, plan_id, months_paid
            )
            
            if not membership_update:
                logger.error(f"No se pudo extender membresía para cliente {client_id}")
                return None
            
            # Generar número de recibo
            receipt_number = self.generate_receipt_number(user_business_id)
            
            # Preparar datos del pago
            payment_data = {
                'clientId': client_id,
                'clientName': client_name,
                'amount': amount,
                'method': data.get('method'),
                'methodDetails': data.get('methodDetails', {}),
                'membershipPlanId': plan_id,
                'monthsPaid': months_paid,
                'startDate': membership_update.get('membershipStart'),
                'endDate': membership_update.get('membershipEnd'),
                'branchId': branch_id,
                'businessId': user_business_id,
                'registeredBy': current_user.get('uid'),
                'registeredByName': current_user.get('name', 'Usuario'),
                'receiptNumber': receipt_number,
                'syncedAt': None  # Para pagos online es null inicialmente
            }
            
            # Crear pago en Firestore
            created_payment = self.firebase_service.create_document('payments', payment_data)
            
            if created_payment:
                logger.info(f"Pago registrado exitosamente: {receipt_number}")
                return created_payment
            else:
                logger.error("No se pudo registrar el pago")
                return None
                
        except Exception as e:
            logger.error(f"Error registrando pago: {str(e)}")
            return None
    
    def sync_offline_payments(
        self, 
        payments_list: List[Dict[str, Any]], 
        current_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sincroniza múltiples pagos registrados offline
        
        Args:
            payments_list: Lista de pagos offline
            current_user: Información del usuario autenticado
            
        Returns:
            Dict con resultados de sincronización
        """
        try:
            results = {
                'synced': 0,
                'failed': 0,
                'results': []
            }
            
            for payment_data in payments_list:
                local_id = payment_data.get('localId')
                registered_at = payment_data.get('registeredAt')
                
                try:
                    # Preparar datos para registro normal
                    sync_data = payment_data.copy()
                    
                    # Agregar información del usuario actual
                    sync_data['registeredBy'] = current_user.get('uid')
                    sync_data['registeredByName'] = current_user.get('name', 'Usuario')
                    
                    # Validar que el pago no exista ya
                    client_id = sync_data.get('clientId')
                    existing_payments = self.firebase_service.query_firestore(
                        'payments',
                        filters=[
                            {'field': 'clientId', 'operator': '==', 'value': client_id},
                            {'field': 'registeredAt', 'operator': '>=', 'value': registered_at}
                        ]
                    )
                    
                    # Si ya existe un pago para este cliente después de esta fecha, es conflicto
                    conflict = False
                    for existing in existing_payments:
                        if (existing.get('clientId') == client_id and 
                            existing.get('createdAt') > registered_at):
                            conflict = True
                            break
                    
                    if conflict:
                        results['results'].append({
                            'localId': local_id,
                            'status': 'conflict',
                            'message': 'El cliente ya tiene un pago registrado después de esta fecha'
                        })
                        results['failed'] += 1
                        continue
                    
                    # Registrar pago
                    created_payment = self.register_payment(sync_data, current_user)
                    
                    if created_payment:
                        # Marcar como sincronizado
                        payment_id = created_payment.get('id')
                        self.firebase_service.update_document(
                            'payments', 
                            payment_id, 
                            {'syncedAt': datetime.now()}
                        )
                        
                        results['results'].append({
                            'localId': local_id,
                            'serverId': payment_id,
                            'status': 'success'
                        })
                        results['synced'] += 1
                    else:
                        results['results'].append({
                            'localId': local_id,
                            'status': 'error',
                            'message': 'Error al registrar pago'
                        })
                        results['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error sincronizando pago {local_id}: {str(e)}")
                    results['results'].append({
                        'localId': local_id,
                        'status': 'error',
                        'message': str(e)
                    })
                    results['failed'] += 1
            
            logger.info(f"Sincronización completada: {results['synced']} exitosos, {results['failed']} fallidos")
            return results
            
        except Exception as e:
            logger.error(f"Error en sincronización de pagos: {str(e)}")
            return {
                'synced': 0,
                'failed': len(payments_list),
                'results': []
            }
    
    def get_client_payments(self, client_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de pagos de un cliente
        
        Args:
            client_id: ID del cliente
            limit: Límite de resultados
            
        Returns:
            Lista de pagos del cliente
        """
        try:
            payments = self.firebase_service.query_firestore(
                'payments',
                filters=[{'field': 'clientId', 'operator': '==', 'value': client_id}],
                order_by='createdAt',
                direction='DESC',
                limit=limit
            )
            
            logger.info(f"Obtenidos {len(payments)} pagos para cliente {client_id}")
            return payments
            
        except Exception as e:
            logger.error(f"Error obteniendo pagos del cliente {client_id}: {str(e)}")
            return []
    
    def get_payment_report(
        self, 
        start_date: str, 
        end_date: str, 
        branch_id: str = None,
        method: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Genera reporte de pagos con filtros
        
        Args:
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
            branch_id: ID de sede (opcional)
            method: Método de pago (opcional)
            
        Returns:
            Dict con resumen del reporte
        """
        try:
            # Construir filtros
            filters = [
                {'field': 'createdAt', 'operator': '>=', 'value': start_date},
                {'field': 'createdAt', 'operator': '<=', 'value': end_date + 'T23:59:59'}
            ]
            
            if branch_id:
                filters.append({'field': 'branchId', 'operator': '==', 'value': branch_id})
            
            if method:
                filters.append({'field': 'method', 'operator': '==', 'value': method})
            
            # Obtener pagos
            payments = self.firebase_service.query_firestore(
                'payments',
                filters=filters,
                order_by='createdAt',
                direction='ASC'
            )
            
            # Calcular resumen
            total_amount = sum(p.get('amount', 0) for p in payments)
            total_payments = len(payments)
            average_amount = total_amount // total_payments if total_payments > 0 else 0
            
            # Agrupar por método
            by_method = {}
            for payment in payments:
                method = payment.get('method', 'other')
                by_method[method] = by_method.get(method, 0) + payment.get('amount', 0)
            
            result = {
                'summary': {
                    'totalAmount': total_amount,
                    'totalPayments': total_payments,
                    'averageAmount': average_amount
                },
                'byMethod': by_method,
                'payments': payments
            }
            
            logger.info(f"Reporte generado: {total_payments} pagos, total ${total_amount/100:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error generando reporte de pagos: {str(e)}")
            return None
