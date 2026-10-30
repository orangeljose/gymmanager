import React, { useRef, useState } from 'react';
import { Camera, ImagePlus, Loader2, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiService } from '@/services/api';
import { imageUrl, type ImageVariant } from '@/utils/images';

export type ImageFolder = 'clients' | 'products' | 'machines' | 'businesses';

interface ImageUploadProps {
  /** URL actual (la que se guarda en Firestore). */
  value?: string | null;
  /** Se llama con la nueva URL o null al quitar. */
  onChange: (url: string | null) => void;
  /** Carpeta destino en Cloudinary. */
  folder: ImageFolder;
  /** Requerido solo para super_admin (negocio seleccionado). */
  businessId?: string;
  /** Variante usada para el preview. */
  variant?: ImageVariant;
  /** Forma del preview. */
  shape?: 'circle' | 'square' | 'wide';
  /** Tamaño del preview. */
  size?: 'sm' | 'md' | 'lg';
  /** Alineación del bloque (preview + acciones). */
  align?: 'left' | 'center';
  /** Texto sobre el dropzone vacío. */
  label?: string;
  /** Texto de ayuda debajo. */
  hint?: string;
  disabled?: boolean;
  /** Iniciales para el fallback circular (clientes). */
  fallbackInitials?: string;
}

const SHAPE_RADIUS: Record<NonNullable<ImageUploadProps['shape']>, string> = {
  circle: 'rounded-full',
  square: 'rounded-xl',
  wide: 'rounded-xl',
};

const SIZE_CLASSES: Record<NonNullable<ImageUploadProps['size']>, Record<NonNullable<ImageUploadProps['shape']>, string>> = {
  sm: { circle: 'h-20 w-20', square: 'h-20 w-20', wide: 'h-24 w-full' },
  md: { circle: 'h-24 w-24', square: 'h-24 w-24', wide: 'h-32 w-full' },
  lg: { circle: 'h-40 w-40', square: 'h-40 w-40', wide: 'h-48 w-full' },
};

const MAX_BYTES = 5 * 1024 * 1024;

export const ImageUpload: React.FC<ImageUploadProps> = ({
  value,
  onChange,
  folder,
  businessId,
  variant = 'card',
  shape = 'square',
  size = 'md',
  align = 'left',
  label = 'Subir imagen',
  hint = 'JPG, PNG o WebP · máximo 5 MB',
  disabled = false,
  fallbackInitials,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);

  const preview = imageUrl(value, variant);
  const shapeClass = `${SIZE_CLASSES[size][shape]} ${SHAPE_RADIUS[shape]}`;
  const centered = align === 'center';

  const handleFile = async (file: File) => {
    if (!file.type.startsWith('image/')) {
      toast.error('Selecciona un archivo de imagen');
      return;
    }
    if (file.size > MAX_BYTES) {
      toast.error('La imagen supera el máximo de 5 MB');
      return;
    }

    setUploading(true);
    try {
      const response = await apiService.uploadImage(file, folder, businessId);
      if (response.success && response.data?.url) {
        onChange(response.data.url);
        toast.success('Imagen actualizada');
      } else {
        toast.error(response.error?.message || 'No se pudo subir la imagen');
      }
    } catch (err: any) {
      toast.error(err.message || 'No se pudo subir la imagen');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setDragging(false);
    if (disabled || uploading) return;
    const file = event.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const openPicker = () => {
    if (!disabled && !uploading) inputRef.current?.click();
  };

  return (
    <div className={shape === 'wide' ? 'w-full' : centered ? 'inline-flex flex-col items-center' : 'inline-block'}>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />

      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        onClick={openPicker}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openPicker();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled && !uploading) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        aria-label={label}
        className={`
          group relative overflow-hidden cursor-pointer select-none
          border-2 border-dashed transition-all duration-200
          ${shapeClass}
          ${dragging
            ? 'border-primary-500 bg-primary-50 scale-[1.02]'
            : 'border-gray-300 bg-gray-50 hover:border-primary-400 hover:bg-primary-50/40'}
          ${disabled ? 'opacity-60 cursor-not-allowed' : ''}
        `}
      >
        {preview ? (
          <>
            <img
              src={preview}
              alt={label}
              className="h-full w-full object-cover"
              loading="lazy"
            />
            <div className="absolute inset-0 flex items-center justify-center gap-3 bg-black/0 opacity-0 transition-all duration-200 group-hover:bg-black/45 group-hover:opacity-100">
              <Camera className="h-5 w-5 text-white drop-shadow" />
              <span className="text-xs font-medium text-white drop-shadow">Cambiar</span>
            </div>
          </>
        ) : shape === 'circle' && fallbackInitials ? (
          <div className="flex h-full w-full items-center justify-center bg-primary-100 text-xl font-semibold text-primary-700">
            {fallbackInitials}
          </div>
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-1 px-2 text-center">
            <ImagePlus className="h-6 w-6 text-gray-400" />
            <span className="text-xs font-medium text-gray-500">{label}</span>
          </div>
        )}

        {uploading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80">
            <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
          </div>
        )}
      </div>

      <div className={`mt-2 flex items-center gap-3 ${centered ? 'justify-center' : ''}`}>
        <button
          type="button"
          onClick={openPicker}
          disabled={disabled || uploading}
          className="text-xs font-medium text-primary-600 hover:text-primary-700 disabled:opacity-50"
        >
          {value ? 'Cambiar imagen' : label}
        </button>
        {value && (
          <button
            type="button"
            onClick={() => onChange(null)}
            disabled={disabled || uploading}
            className="inline-flex items-center gap-1 text-xs font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" /> Quitar
          </button>
        )}
      </div>
      <p className={`mt-1 text-xs text-gray-400 ${centered ? 'text-center' : ''}`}>{hint}</p>
    </div>
  );
};
