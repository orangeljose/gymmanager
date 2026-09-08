/**
 * Helpers de fechas para membresías.
 *
 * PROBLEMA DE ZONA HORARIA:
 * El backend guarda las fechas como ISO UTC (ej: "2026-09-01T00:00:00+00:00").
 * Si el navegador está en Venezuela (UTC-4), `new Date("2026-09-01T00:00:00+00:00")`
 * produce 31/08 20:00 LOCAL → se muestra "31 ago" en vez de "1 sep".
 *
 * SOLUCIÓN: extraer la parte calendario (YYYY-MM-DD) directamente de la string
 * y construir un Date local de medianoche. La app es de negocio local, lo que
 * importa es el día calendario, no el instante UTC.
 */

/**
 * Extrae el día calendario de una string ISO o Date, sin conversión de timezone.
 * - "2026-09-01T00:00:00+00:00" → Date local 2026-09-01 00:00
 * - "2026-09-01" → Date local 2026-09-01 00:00
 * - Date → usa sus componentes calendario
 * - null/undefined → hoy local
 */
export const toCalendarDate = (d: string | Date | null | undefined): Date => {
  if (!d) return new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());
  if (typeof d === 'string') {
    // "2026-09-01" o "2026-09-01T..." → extraer Y-M-D
    const m = d.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  }
  const date = d instanceof Date ? d : new Date(d);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
};

/**
 * Convierte a Date local de medianoche (alias de toCalendarDate).
 */
export const toLocalMidnight = (d: string | Date | null | undefined): Date => toCalendarDate(d);

/**
 * Calcula los días restantes de una membresía usando fechas de medianoche local.
 * - > 0: días por vencer
 * -   0: vence hoy
 * - < 0: días vencido
 * - null si no hay membershipEnd (cliente sin membresía)
 */
export const getDaysRemaining = (membershipEnd: string | Date | null | undefined): number | null => {
  if (!membershipEnd) return null;
  const today = toCalendarDate(new Date());
  const end = toCalendarDate(membershipEnd);
  return Math.round((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
};

/**
 * Formatea una fecha para mostrar, usando el día calendario (sin timezone shift).
 */
export const formatDate = (d: string | Date | null | undefined): string => {
  if (!d) return '-';
  const date = toCalendarDate(d);
  return date.toLocaleDateString('es-VE', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};