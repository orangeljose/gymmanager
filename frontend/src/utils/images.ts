/**
 * Utilidades de imágenes (Cloudinary).
 *
 * Guardamos UNA sola URL por entidad y pedimos variantes al CDN.
 * Cloudinary cachea cada transformación: la genera una vez y la reutiliza.
 */

export type ImageVariant = 'avatar' | 'thumb' | 'tile' | 'card' | 'banner' | 'logo';

const TRANSFORMS: Record<ImageVariant, string> = {
  // Clientes: recorte centrado en el rostro.
  avatar: 'w_120,h_120,c_fill,g_face,q_auto,f_auto',
  // Listados compactos.
  thumb: 'w_160,h_160,c_pad,b_white,q_auto,f_auto',
  // Tarjetas 4:3 (equipamiento).
  tile: 'w_600,h_450,c_fill,q_auto,f_auto',
  // Tarjetas de producto / máquina.
  card: 'w_400,h_400,c_pad,b_white,q_auto,f_auto',
  // Encabezados anchos.
  banner: 'w_800,h_400,c_fill,q_auto,f_auto',
  // Logos: sin recorte, fondo respetado.
  logo: 'w_400,h_400,c_pad,q_auto,f_auto',
};

const CLOUDINARY_MARKER = '/upload/';

/**
 * Devuelve la URL transformada para la variante pedida.
 * Si la URL no es de Cloudinary (o no existe), se devuelve tal cual.
 */
export function imageUrl(
  url: string | null | undefined,
  variant: ImageVariant = 'card',
): string | undefined {
  if (!url) return undefined;
  if (!url.includes('res.cloudinary.com') || !url.includes(CLOUDINARY_MARKER)) {
    return url;
  }

  const [head, tail] = url.split(CLOUDINARY_MARKER);
  // Si ya trae una transformación en el path, la respetamos como está.
  const startsWithVersion = /^v\d+\//.test(tail);
  const alreadyTransformed = !startsWithVersion && tail.split('/').length > 1 && /[,_]/.test(tail.split('/')[0]);
  if (alreadyTransformed) return url;

  return `${head}${CLOUDINARY_MARKER}${TRANSFORMS[variant]}/${tail}`;
}

/** Iniciales para el fallback de avatares de clientes. */
export function initials(name?: string | null): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part.charAt(0).toUpperCase()).join('') || '?';
}
