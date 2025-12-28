"use client";

interface ImageLightboxProps {
  isOpen: boolean;
  src: string;
  alt: string;
  onClose: () => void;
}

export function ImageLightbox({
  isOpen,
  src,
  alt,
  onClose,
}: ImageLightboxProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative h-full w-full flex items-center justify-center p-4">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-md bg-black/70 px-3 py-1 text-sm text-white hover:bg-black/80"
          aria-label="Close image preview"
        >
          Close
        </button>
        <img
          src={src}
          alt={alt}
          className="max-h-[90vh] max-w-[95vw] object-contain rounded-lg shadow-2xl"
          draggable={false}
        />
      </div>
    </div>
  );
}
