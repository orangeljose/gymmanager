"""
Backup + eliminación definitiva de clientes borrados (isDeleted: true) y sus pagos.

PASO 1: exporta a JSON los clientes isDeleted=true + sus pagos (backup)
PASO 2: elimina físicamente esos documentos de Firestore (IRREVERSIBLE)

USO:
  python cleanup_deleted_clients.py            # dry-run (solo muestra)
  python cleanup_deleted_clients.py --backup   # hace backup a JSON, no borra
  python cleanup_deleted_clients.py --apply    # backup + elimina
"""
import os
import sys
import json
import logging
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from services.firebase_service import FirebaseService

APPLY = '--apply' in sys.argv
BACKUP_ONLY = '--backup' in sys.argv and not APPLY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')


def main():
    if not os.environ.get('FIREBASE_CREDENTIALS_JSON'):
        logger.error("FIREBASE_CREDENTIALS_JSON no está configurado")
        sys.exit(1)

    firebase = FirebaseService()

    # 1. Clientes borrados
    all_clients = firebase.query_firestore('clients')
    deleted_clients = [c for c in all_clients if c.get('isDeleted', False)]
    deleted_ids = {c['id'] for c in deleted_clients}

    # 2. Pagos de esos clientes
    all_payments = firebase.query_firestore('payments')
    orphan_payments = [p for p in all_payments if p.get('clientId') in deleted_ids]

    logger.info(f"Clientes a eliminar: {len(deleted_clients)}")
    logger.info(f"Pagos a eliminar: {len(orphan_payments)}")

    if not deleted_clients and not orphan_payments:
        logger.info("Nada que limpiar.")
        return

    # 3. Backup siempre (dry-run, --backup, y --apply)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'cleanup_deleted_clients_{timestamp}.json')
    backup_data = {
        'createdAt': datetime.now().isoformat(),
        'deletedClients': deleted_clients,
        'orphanPayments': orphan_payments
    }
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Backup guardado en: {backup_path}")

    if BACKUP_ONLY:
        logger.info("Modo --backup: NO se eliminó nada. Ejecuta con --apply para borrar.")
        return

    if not APPLY:
        logger.info("DRY-RUN: no se eliminó nada. Ejecuta con --apply para borrar.")
        return

    # 4. Eliminar (solo con --apply)
    logger.info("Eliminando pagos de clientes borrados...")
    for p in orphan_payments:
        ok = firebase.delete_document('payments', p['id'])
        logger.info(f"  {'✓' if ok else '✗'} pago {p['id']} (cliente {p.get('clientId')})")

    logger.info("Eliminando clientes borrados...")
    for c in deleted_clients:
        ok = firebase.delete_document('clients', c['id'])
        logger.info(f"  {'✓' if ok else '✗'} cliente {c['id']} ({c.get('name')})")

    logger.info("Limpieza completada.")


if __name__ == '__main__':
    main()