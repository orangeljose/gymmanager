/**
 * Helpers de fechas para membresías.
 *
 * Normaliza fechas a medianoche LOCAL para calcular días de forma consistente,
 * sin mezclar la zona UTC del backend con la hora local del navegador.
 * Un pago registrado con paymentDate "2026-09-01" produce
 * membershipEnd "2026-10-01T00:00:00+00:00" (UTC); en Venezuela (UTC-4) eso
 * sería 30/09 20:00 local, lo que hacía que el conteo de días restantes
 * arrancara un día antes. Truncar a medianoche local lo corrige.
 */

/**
 * Convierte una fecha (string ISO, Date, timestamp de Firestore) a un Date
 * local de medianoche (00:00:00) — descarta la hora y la zona horaria.
 */
export const toLocalMidnight = (d: string | Date | null | undefined): Date => {
  const date = d instanceof Date ? d : d ? new Date(d) : new Date();
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
};

/**
 * Calcula los días restantes de una membresía usando fechas de medianoche local.
 * - > 0: días por vencer
 * -   0: vence hoy
 * - < 0: días vencido
 * - null si no hay membershipEnd (cliente sin membresía)
 */
export const getDaysRemaining = (membershipEnd: string | Date | null | undefined): number | null => {
  if (!membershipEnd) return null;
  const today = toLocalMidnight(new Date());
  const end = toLocalMidnight(membershipEnd);
  return Math.round((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
};

/**
 * Formatea una fecha para mostrar, en la zona local del navegador.
 */
export const formatDate = (d: string | Date | null | undefined): string => {
  if (!d) return '-';
  return new Date(d).toLocaleDateString('es-VE', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};