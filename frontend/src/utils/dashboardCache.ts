import type { DashboardData } from '@/types';

/**
 * Cache en memoria del dashboard con TTL de 5 minutos.
 *
 * Reduce las lecturas de Firestore: la pantalla de Inicio lee ~170 clientes en
 * CADA carga. Con este cache, las recargas dentro de 5 minutos reutilizan los
 * datos ya obtenidos en lugar de golpear la red (y la cuota de Firestore).
 *
 * El cache es un singleton a nivel de módulo: una sola entrada { data, timestamp }.
 * Las mutaciones que cambian datos del dashboard (pago, cliente) deben llamar
 * `invalidateDashboardCache()` para forzar la próxima recarga.
 */

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutos

interface DashboardCacheEntry {
  data: DashboardData;
  timestamp: number;
}

let cache: DashboardCacheEntry | null = null;

/**
 * Devuelve los datos cacheados si tienen menos de 5 minutos, o `null` si no hay
 * cache o expiró (en cuyo caso también limpia la entrada expirada).
 */
export function getCachedDashboard(): DashboardData | null {
  if (!cache) return null;

  if (Date.now() - cache.timestamp >= CACHE_TTL_MS) {
    cache = null;
    return null;
  }

  return cache.data;
}

/**
 * Almacena los datos del dashboard junto con el timestamp actual.
 */
export function setCachedDashboard(data: DashboardData): void {
  cache = { data, timestamp: Date.now() };
}

/**
 * Limpia el cache. Llamar después de cualquier mutación que altere los datos
 * que el dashboard muestra (registrar/eliminar pagos, crear/actualizar/eliminar
 * clientes).
 */
export function invalidateDashboardCache(): void {
  cache = null;
}
