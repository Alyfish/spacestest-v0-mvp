"use client";

import {
  getProjectImageUrl,
  ImprovementMarker,
  useSaveImprovementMarkers,
} from "@/lib/api";
import Image from "next/image";
import { useRef, useState } from "react";

interface ImageMarkerInterfaceProps {
  projectId: string;
}

// 5 distinct colors for the 5 markers
const MARKER_COLORS = [
  "bg-red-500", // Red
  "bg-green-500", // Green
  "bg-blue-500", // Blue
  "bg-purple-500", // Purple
  "bg-orange-500", // Orange
];

const MAX_MARKERS = 5;

export function ImageMarkerInterface({ projectId }: ImageMarkerInterfaceProps) {
  const [markers, setMarkers] = useState<ImprovementMarker[]>([]);
  const [isPlacingMarker, setIsPlacingMarker] = useState(false);
  const [editingMarkerId, setEditingMarkerId] = useState<string | null>(null);
  const [editingDescription, setEditingDescription] = useState("");

  const imageRef = useRef<HTMLDivElement>(null);
  const saveMarkersMutation = useSaveImprovementMarkers();

  const handleImageClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!isPlacingMarker || !imageRef.current || markers.length >= MAX_MARKERS)
      return;

    const rect = imageRef.current.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;

    // Ensure coordinates are within bounds
    const clampedX = Math.max(0, Math.min(1, x));
    const clampedY = Math.max(0, Math.min(1, y));

    const newMarker: ImprovementMarker = {
      id: `marker_${Date.now()}`,
      position: { x: clampedX, y: clampedY },
      description: "",
      color: ["red", "green", "blue", "purple", "orange"][markers.length % 5],
    };

    setMarkers([...markers, newMarker]);
    setEditingMarkerId(newMarker.id);
    setEditingDescription("");
    setIsPlacingMarker(false);
  };

  const handleMarkerClick = (markerId: string) => {
    const marker = markers.find((m) => m.id === markerId);
    if (marker) {
      setEditingMarkerId(markerId);
      setEditingDescription(marker.description);
    }
  };

  const handleSaveDescription = () => {
    if (!editingMarkerId) return;

    setMarkers(
      markers.map((marker) =>
        marker.id === editingMarkerId
          ? { ...marker, description: editingDescription }
          : marker
      )
    );
    setEditingMarkerId(null);
    setEditingDescription("");
  };

  const handleDeleteMarker = (markerId: string) => {
    setMarkers(markers.filter((marker) => marker.id !== markerId));
    if (editingMarkerId === markerId) {
      setEditingMarkerId(null);
      setEditingDescription("");
    }
  };

  const handleSaveMarkers = () => {
    if (markers.length === 0) return;

    saveMarkersMutation.mutate({
      projectId,
      markers: markers.filter((marker) => marker.description.trim() !== ""),
    });
  };

  const getMarkerColor = (index: number) => {
    return MARKER_COLORS[index % MARKER_COLORS.length];
  };

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Mark Areas for Improvement
      </h2>

      <div className="space-y-6">
        {/* Instructions */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-blue-800 dark:text-blue-200 text-sm">
            Click on areas of your room that you'd like to improve. You can add
            up to 5 markers. Add a description for each marker to explain what
            you want to change.
          </p>
        </div>

        {/* Interactive Image */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Room Image
            </h3>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {markers.length}/{MAX_MARKERS} markers
              </div>
              <button
                onClick={() => setIsPlacingMarker(!isPlacingMarker)}
                disabled={markers.length >= MAX_MARKERS}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  isPlacingMarker
                    ? "bg-blue-600 text-white"
                    : markers.length >= MAX_MARKERS
                    ? "bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed"
                    : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                }`}
              >
                {isPlacingMarker ? "Cancel" : "Place Marker"}
              </button>
            </div>
          </div>

          <div className="relative bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden">
            <div
              ref={imageRef}
              onClick={handleImageClick}
              className={`relative w-full h-96 cursor-pointer ${
                isPlacingMarker ? "cursor-crosshair" : ""
              }`}
            >
              <Image
                src={getProjectImageUrl(projectId)}
                alt="Room image for marking improvements"
                fill
                className="object-contain"
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
              />

              {/* Render existing markers */}
              {markers.map((marker, index) => (
                <div
                  key={marker.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleMarkerClick(marker.id);
                  }}
                  className={`absolute w-6 h-6 rounded-full border-2 border-white shadow-lg cursor-pointer transition-transform hover:scale-110 ${getMarkerColor(
                    index
                  )}`}
                  style={{
                    left: `${marker.position.x * 100}%`,
                    top: `${marker.position.y * 100}%`,
                    transform: "translate(-50%, -50%)",
                  }}
                >
                  <div className="flex items-center justify-center text-white text-xs font-bold">
                    {index + 1}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {isPlacingMarker && (
            <div className="text-sm text-gray-600 dark:text-gray-400 text-center">
              Click on the image to place marker {markers.length + 1}
            </div>
          )}

          {markers.length >= MAX_MARKERS && (
            <div className="text-sm text-orange-600 dark:text-orange-400 text-center">
              Maximum of 5 markers reached
            </div>
          )}
        </div>

        {/* Marker List */}
        {markers.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Improvement Markers ({markers.length})
            </h3>
            <div className="space-y-2">
              {markers.map((marker, index) => (
                <div
                  key={marker.id}
                  className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div
                    className={`w-4 h-4 rounded-full ${getMarkerColor(index)}`}
                  />
                  <div className="flex-1">
                    {editingMarkerId === marker.id ? (
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={editingDescription}
                          onChange={(e) =>
                            setEditingDescription(e.target.value)
                          }
                          placeholder="Describe what you want to change..."
                          className="flex-1 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white"
                          onKeyPress={(e) =>
                            e.key === "Enter" && handleSaveDescription()
                          }
                        />
                        <button
                          onClick={handleSaveDescription}
                          className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-700 dark:text-gray-300">
                          {marker.description || "Click to add description"}
                        </span>
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() => handleMarkerClick(marker.id)}
                            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteMarker(marker.id)}
                            className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Save Button */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {markers.length} marker{markers.length !== 1 ? "s" : ""} placed
          </div>
          <button
            onClick={handleSaveMarkers}
            disabled={
              saveMarkersMutation.isPending ||
              markers.length === 0 ||
              markers.some((marker) => !marker.description.trim())
            }
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saveMarkersMutation.isPending ? "Saving..." : "Save Markers"}
          </button>
        </div>

        {/* Status Messages */}
        {saveMarkersMutation.isSuccess && (
          <div className="text-green-600 dark:text-green-400 text-sm">
            Markers saved successfully! Your project is ready for AI
            recommendations.
          </div>
        )}

        {saveMarkersMutation.isError && (
          <div className="text-red-600 dark:text-red-400 text-sm">
            Error: {saveMarkersMutation.error?.message}
          </div>
        )}
      </div>
    </div>
  );
}
