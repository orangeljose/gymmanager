"""
Utilidades de zona horaria del negocio.

El "día" del negocio se define en su zona local (BUSINESS_TIMEZONE),
no en UTC: si se usa UTC, después de las 20:00 en Venezuela el dashboard
salta al día siguiente y los totales de "hoy" se van a cero.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from config import Config

# Respaldo de offset fijo si el entorno no tiene tzdata instalada.
_TZ_FALLBACK_OFFSETS = {
    'America/Caracas': -4,
    'America/Bogota': -5,
    'America/Mexico_City': -6,
    'America/Lima': -5,
    'America/Santiago': -4,
    'America/Argentina/Buenos_Aires': -3,
    'America/Sao_Paulo': -3,
    'America/New_York': -5,
    'America/Los_Angeles': -8,
    'Europe/Madrid': 1,
}


def business_tz():
    """tzinfo del negocio, con respaldo de offset fijo si falta tzdata."""
    try:
        return ZoneInfo(Config.TIMEZONE)
    except Exception:
        offset = _TZ_FALLBACK_OFFSETS.get(Config.TIMEZONE, 0)
        return timezone(timedelta(hours=offset))


def business_now() -> datetime:
    """Ahora en la zona horaria del negocio (datetime con tzinfo)."""
    return datetime.now(business_tz())


def business_day_start(moment: datetime | None = None) -> datetime:
    """Inicio del día del negocio (00:00 local) para `moment` o ahora."""
    moment = moment or business_now()
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)
