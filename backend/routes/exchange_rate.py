"""
Rutas de tipo de cambio BCV para GymManager
"""
import logging
import os
import time
import re
from flask import Blueprint, jsonify
import requests

logger = logging.getLogger(__name__)

exchange_bp = Blueprint('exchange', __name__, url_prefix='/api/exchange-rate')

CACHE_DURATION_SECONDS = 3600
_cached_rate = None
_cache_timestamp = 0


def _fetch_bcv_rate():
    """
    Obtiene la tasa BCV del día desde API pública.
    Cachea el resultado por CACHE_DURATION_SECONDS.
    """
    global _cached_rate, _cache_timestamp

    current_time = time.time()
    if _cached_rate is not None and (current_time - _cache_timestamp) < CACHE_DURATION_SECONDS:
        return _cached_rate

    try:
        response = requests.get(
            'https://bcv-api.vercel.app/v1/dollar',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            rate = data.get('dolares', [{}])[0].get('precio', None)
            if rate:
                numeric_rate = float(re.sub(r'[^\d.]', '', str(rate)))
                _cached_rate = numeric_rate
                _cache_timestamp = current_time
                logger.info(f"Tasa BCV actualizada: {numeric_rate}")
                return numeric_rate
    except Exception as e:
        logger.warning(f"Error fetching BCV rate: {str(e)}")

    if _cached_rate is not None:
        return _cached_rate

    _cached_rate = 0.0
    return _cached_rate


@exchange_bp.route('', methods=['GET', 'OPTIONS'])
def get_exchange_rate():
    """
    Obtiene la tasa BCV del día
    GET /api/exchange-rate

    Response (200):
    {
        "success": true,
        "data": {
            "rate": 45.20,
            "currency": "Bs/USD",
            "source": "BCV",
            "cached": false
        }
    }
    """
    try:
        cached = _cached_rate is not None and (time.time() - _cache_timestamp) < CACHE_DURATION_SECONDS

        if not cached:
            rate = _fetch_bcv_rate()
        else:
            rate = _cached_rate

        return jsonify({
            'success': True,
            'data': {
                'rate': rate,
                'currency': 'Bs/USD',
                'source': 'BCV',
                'cached': cached
            }
        }), 200

    except Exception as e:
        logger.error(f"Error en exchange rate: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'code': 500, 'message': 'Error interno del servidor'}
        }), 500