import type { PaymentMethod } from '@/types';

/**
 * Métodos permitidos para compras de mercancía (egresos de dinero).
 * Debe coincidir con PURCHASE_METHODS en backend/routes/products.py.
 */
export const PURCHASE_METHODS: PaymentMethod[] = ['zelle', 'cash', 'pago_movil', 'binance'];

/** Métodos que exigen una cuenta destino registrada. */
export const ACCOUNT_REQUIRED_METHODS: PaymentMethod[] = ['zelle', 'pago_movil', 'binance'];

export const PURCHASE_METHOD_LABELS: Record<string, string> = {
  zelle: 'Zelle',
  cash: 'Efectivo',
  pago_movil: 'Pago Móvil',
  binance: 'Binance',
};
