"""
Script de recálculo de membresías afectadas por el bug de anchor de fecha.

El bug: al registrar un pago con paymentDate retroactivo (ej: ayer), el cálculo
de la fecha de fin de suscripción usaba "now" (hoy) en vez de la fecha del pago.

Este script recalcula las membresías de los clientes que tienen pagos con
paymentDate (o createdAt fallback) >= 2026-09-04, usando la lógica corregida
(anchor en la fecha del pago).

USO:
  python recalc_memberships_from_20240904.py            # dry-run (no modifica)
  python recalc_memberships_from_20240904.py --apply    # aplica los cambios
"""

import os
import sys
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

# Cargar .env (FIREBASE_CREDENTIALS_JSON)
load_dotenv()

from services.membership_service import MembershipService
from services.firebase_service import FirebaseService

CUTOFF_DATE = datetime(2026, 9, 4, tzinfo=timezone.utc)
APPLY = '--apply' in sys.argv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_payment_date(payment) -> datetime:
    """paymentDate con fallback a createdAt (misma lógica que MembershipService)."""
    raw = payment.get('paymentDate') or payment.get('createdAt')
    if raw is None:
        return datetime.now(timezone.utc)
    if isinstance(raw, str):
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    elif hasattr(raw, 'to_datetime'):
        dt = raw.to_datetime()
    elif isinstance(raw, datetime):
        dt = raw
    else:
        return datetime.now(timezone.utc)
    # Normalizar a timezone-aware UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main():
    if not os.environ.get('FIREBASE_CREDENTIALS_JSON'):
        logger.error("FIREBASE_CREDENTIALS_JSON no está configurado en .env")
        sys.exit(1)

    firebase = FirebaseService()
    membership = MembershipService()

    # 1. Buscar pagos REGISTRADOS desde el cutoff (createdAt >= 04/09) para
    # identificar clientes afectados. El bug afecta pagos con paymentDate
    # retroactivo pero registrados recientemente.
    logger.info(f"Buscando pagos REGISTRADOS desde {CUTOFF_DATE.isoformat()} (createdAt)...")
    all_payments = firebase.query_firestore('payments')

    affected_clients = set()
    recent_payments = []
    for p in all_payments:
        if p.get('isDeleted', False):
            continue
        # Usar createdAt (cuándo se registró) como criterio del cutoff
        created = parse_payment_date({'createdAt': p.get('createdAt')})
        if created >= CUTOFF_DATE:
            affected_clients.add(p.get('clientId'))
            recent_payments.append(p)

    if not affected_clients:
        logger.info("No hay clientes con pagos desde el 04/09/2026. Nada que recalcular.")
        return

    logger.info(f"Clientes afectados ({len(affected_clients)}): {sorted(affected_clients)}")
    logger.info(f"Pagos recientes encontrados: {len(recent_payments)}")

    # 2. Recalcular membresía de cada cliente afectado
    changed = []
    for client_id in sorted(affected_clients):
        if not client_id:
            continue
        client = firebase.get_document('clients', client_id)
        if not client:
            logger.warning(f"Cliente {client_id} no encontrado, se omite.")
            continue

        old_end = client.get('membershipEnd')

        if APPLY:
            result = membership.recalculate_membership(client_id)
            if result:
                new_end = result.get('membershipEnd')
                logger.info(
                    f"✓ {client.get('name', client_id)}: "
                    f"membershipEnd {old_end} → {new_end} ({result.get('status')})"
                )
                changed.append({'clientId': client_id, 'oldEnd': old_end, 'newEnd': new_end})
            else:
                logger.error(f"✗ Falló recálculo de {client_id}")
        else:
            # Dry-run: mostrar lo que se recalcularía (sin tocar)
            logger.info(f"[dry-run] {client.get('name', client_id)}: membershipEnd actual = {old_end}")

    if not APPLY:
        logger.info("\nDRY-RUN: no se modificó nada. Ejecuta con --apply para aplicar.")

    logger.info(f"\nTotal clientes recalculados: {len(changed)}")
    logger.info("Listo.")


if __name__ == '__main__':
    main()