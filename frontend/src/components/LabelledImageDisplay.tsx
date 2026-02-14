import { getProjectLabelledImageUrl, ImprovementMarker } from "@/lib/api";
import { ImageLightbox } from "@/components/ImageLightbox";
import Image from "next/image";
import { useState } from "react";

interface LabelledImageDisplayProps {
  projectId: string;
  markers: ImprovementMarker[];
}

export function LabelledImageDisplay({
  projectId,
  markers,
}: LabelledImageDisplayProps) {
  const [lightboxImage, setLightboxImage] = useState<{
    src: string;
    alt: string;
  } | null>(null);

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Labelled Image with Improvement Markers
      </h2>

      <div className="space-y-4">
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Image with Visual Markers
          </h3>
          <div
            className="relative w-full h-96 bg-gray-200 dark:bg-gray-600 rounded-lg overflow-hidden cursor-zoom-in"
            onClick={() =>
              setLightboxImage({
                src: getProjectLabelledImageUrl(projectId),
                alt: "Room image with improvement markers",
              })
            }
          >
            <Image
              src={getProjectLabelledImageUrl(projectId)}
              alt="Room image with improvement markers"
              fill
              className="object-contain"
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            />
          </div>
        </div>

        {markers.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Improvement Markers ({markers.length})
            </h3>
            <div className="grid gap-3">
              {markers.map((marker, index) => (
                <div
                  key={marker.id}
                  className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div
                    className={`w-4 h-4 rounded-full ${
                      marker.color === "red"
                        ? "bg-red-500"
                        : marker.color === "green"
                        ? "bg-green-500"
                        : marker.color === "blue"
                        ? "bg-blue-500"
                        : marker.color === "purple"
                        ? "bg-purple-500"
                        : marker.color === "orange"
                        ? "bg-orange-500"
                        : "bg-gray-500"
                    }`}
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        Marker {index + 1}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                        {marker.color} marker
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                      {marker.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <ImageLightbox
        isOpen={Boolean(lightboxImage)}
        src={lightboxImage?.src || ""}
        alt={lightboxImage?.alt || "Image preview"}
        onClose={() => setLightboxImage(null)}
      />
    </div>
  );
}
