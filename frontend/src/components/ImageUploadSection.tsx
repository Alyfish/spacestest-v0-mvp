import { getProjectImageUrl, useUploadProjectImage } from "@/lib/api";
import { ImageLightbox } from "@/components/ImageLightbox";
import Image from "next/image";
import { useRef, useState } from "react";

interface ImageUploadSectionProps {
  projectId: string;
  status: string;
  context: Record<string, any>;
}

export function ImageUploadSection({
  projectId,
  status,
  context,
}: ImageUploadSectionProps) {
  const uploadImageMutation = useUploadProjectImage();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [lightboxImage, setLightboxImage] = useState<{
    src: string;
    alt: string;
  } | null>(null);

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Upload Room Image
      </h2>

      {status === "NEW" && (
        <div className="space-y-4">
          <p className="text-gray-600 dark:text-gray-300">
            Upload an image of your room or space to get started with AI
            interior design recommendations.
          </p>

          <div className="flex items-center space-x-4">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  uploadImageMutation.mutate({ projectId, file });
                }
              }}
            />

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadImageMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploadImageMutation.isPending ? "Uploading..." : "Choose Image"}
            </button>

            {uploadImageMutation.isSuccess && (
              <span className="text-green-600 dark:text-green-400 text-sm">
                Image uploaded successfully!
              </span>
            )}

            {uploadImageMutation.isError && (
              <span className="text-red-600 dark:text-red-400 text-sm">
                Error: {uploadImageMutation.error?.message}
              </span>
            )}
          </div>
        </div>
      )}

      {status !== "NEW" && (
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-green-600 dark:text-green-400 font-medium">
              Base image uploaded successfully
            </span>
          </div>

          {context.base_image && (
            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Uploaded Image
              </h3>
              <div className="space-y-4">
                <div
                  className="relative w-full h-64 bg-gray-200 dark:bg-gray-600 rounded-lg overflow-hidden cursor-zoom-in"
                  onClick={() =>
                    setLightboxImage({
                      src: getProjectImageUrl(projectId),
                      alt: "Uploaded room image",
                    })
                  }
                >
                  <Image
                    src={getProjectImageUrl(projectId)}
                    alt="Uploaded room image"
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                  />
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  <p>
                    <strong>File path:</strong> {context.base_image}
                  </p>
                  {context.is_base_image_empty_room !== undefined && (
                    <p>
                      <strong>Room analysis:</strong>{" "}
                      {context.is_base_image_empty_room
                        ? "Empty room"
                        : "Room with furniture/decorations"}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      <ImageLightbox
        isOpen={Boolean(lightboxImage)}
        src={lightboxImage?.src || ""}
        alt={lightboxImage?.alt || "Image preview"}
        onClose={() => setLightboxImage(null)}
      />
    </div>
  );
}
