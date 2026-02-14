"use client";

import { useGenerateInspirationRedesign, useRetryRedesign, SelectedTrendingProduct } from "@/lib/api";
import { ImageLightbox } from "@/components/ImageLightbox";
import { useState } from "react";
import { FurnitureIdentificationPanel } from "./FurnitureIdentificationPanel";

interface InspirationRedesignDisplayProps {
  projectId: string;
  generatedImageBase64?: string;
  inspirationPrompt?: string;
  hasRecommendations: boolean;
  selectedTrendingProducts?: SelectedTrendingProduct[];
  modelUsed?: string;
}

export function InspirationRedesignDisplay({
  projectId,
  generatedImageBase64,
  inspirationPrompt,
  hasRecommendations,
  selectedTrendingProducts = [],
  modelUsed,
}: InspirationRedesignDisplayProps) {
  const generateRedesign = useGenerateInspirationRedesign();
  const retryRedesign = useRetryRedesign();
  const [imageError, setImageError] = useState(false);
  const [showFurniturePanel, setShowFurniturePanel] = useState(false);
  const [lightboxImage, setLightboxImage] = useState<{
    src: string;
    alt: string;
  } | null>(null);
  const [showRetryInput, setShowRetryInput] = useState(false);
  const [retryFeedback, setRetryFeedback] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const handleGenerate = () => {
    setActionError(null);
    generateRedesign.mutate(
      { projectId },
      {
        onError: (error) => {
          console.error("Failed to generate inspiration redesign:", error);
          setActionError(
            error instanceof Error
              ? error.message
              : "Failed to generate inspiration redesign. Please try again."
          );
        },
      }
    );
  };

  const handleRetry = () => {
    if (!retryFeedback.trim()) {
      setActionError("Please describe what you'd like to change.");
      return;
    }
    setActionError(null);
    retryRedesign.mutate(
      { projectId, feedback: retryFeedback.trim() },
      {
        onSuccess: () => {
          setShowRetryInput(false);
          setRetryFeedback("");
          setActionError(null);
        },
        onError: (error) => {
          console.error("Failed to apply edit:", error);
          setActionError(
            error instanceof Error
              ? error.message
              : "Failed to edit the image. Please try again."
          );
        },
      }
    );
  };

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Inspiration-based Redesign
      </h2>

      {!generatedImageBase64 && (
        <div className="space-y-4">
          <p className="text-gray-600 dark:text-gray-300">
            Generate a new image that applies your inspiration recommendations to
            the original room image while preserving its structure.
          </p>

          {/* Show selected trending products that will be included */}
          {selectedTrendingProducts.length > 0 && (
            <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <h4 className="font-semibold text-purple-900 dark:text-purple-200 mb-3 flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Products to Include in Design:
              </h4>
              <div className="flex flex-wrap gap-3">
                {selectedTrendingProducts.map((product, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-lg p-2 pr-3 shadow-sm"
                  >
                    <img
                      src={product.image_url}
                      alt={product.title}
                      className="w-12 h-12 rounded object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = `https://images.weserv.nl/?url=${encodeURIComponent(product.image_url)}&w=48&h=48&fit=cover`;
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[150px]">
                        {product.title}
                      </p>
                      <p className="text-xs text-purple-600 dark:text-purple-400">
                        {product.category}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={
              generateRedesign.isPending || !hasRecommendations
            }
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generateRedesign.isPending
              ? "Generating..."
              : "Generate Inspiration Redesign"}
          </button>
          {!hasRecommendations && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Add inspiration images and generate recommendations first.
            </p>
          )}
          {actionError && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
              {actionError}
            </p>
          )}
        </div>
      )}

      {generatedImageBase64 && (
        <div className="mt-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
            AI Redesigned Room
          </h3>
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            {!imageError ? (
              <img
                src={generatedImageBase64?.startsWith('http') ? generatedImageBase64 : `data:image/png;base64,${generatedImageBase64}`}
                alt="Inspiration Redesign"
                className="w-full h-64 object-cover rounded-lg mb-3 cursor-zoom-in"
                onError={() => setImageError(true)}
                onClick={(event) =>
                  setLightboxImage({
                    src: event.currentTarget.src,
                    alt: "Inspiration Redesign",
                  })
                }
              />
            ) : (
              <div className="w-full h-64 bg-gray-200 dark:bg-gray-600 rounded-lg mb-3 flex items-center justify-center">
                <div className="text-center">
                  <svg
                    className="w-12 h-12 text-gray-400 mx-auto mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <p className="text-gray-500 dark:text-gray-400 text-sm">
                    Failed to load redesign image
                  </p>
                </div>
              </div>
            )}
            <div className="flex items-center justify-between">
              <p className="font-medium text-gray-900 dark:text-white text-sm">
                Generated by Gemini AI using your inspiration
              </p>
              {modelUsed && (
                <span className="text-xs px-2 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full">
                  {modelUsed}
                </span>
              )}
            </div>

            {/* Action Buttons */}
            <div className="mt-3 flex flex-wrap gap-2">
              {/* Regenerate Button */}
              <button
                onClick={handleGenerate}
                disabled={generateRedesign.isPending || retryRedesign.isPending}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center gap-2"
              >
                {generateRedesign.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Regenerating...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Regenerate</span>
                  </>
                )}
              </button>

              {/* Retry Button */}
              <button
                onClick={() => setShowRetryInput(!showRetryInput)}
                disabled={generateRedesign.isPending || retryRedesign.isPending}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                <span>Retry</span>
              </button>
            </div>

            {/* Retry Input */}
            {showRetryInput && (
              <div className="mt-3 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                <label className="block text-sm font-medium text-purple-900 dark:text-purple-200 mb-2">
                  What would you like to change?
                </label>
                <textarea
                  value={retryFeedback}
                  onChange={(e) => setRetryFeedback(e.target.value)}
                  placeholder="e.g., Remove the lamp on the nightstand, add a plant in the corner, replace the blue rug with a beige one..."
                  className="w-full px-3 py-2 border border-purple-300 dark:border-purple-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                  rows={3}
                  disabled={retryRedesign.isPending}
                />
                <div className="mt-2 flex gap-2">
                  <button
                    onClick={handleRetry}
                    disabled={retryRedesign.isPending || !retryFeedback.trim()}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center gap-2"
                  >
                    {retryRedesign.isPending ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>Applying...</span>
                      </>
                    ) : (
                      <span>Apply Changes</span>
                    )}
                  </button>
                  <button
                    onClick={() => {
                      setShowRetryInput(false);
                      setRetryFeedback("");
                    }}
                    disabled={retryRedesign.isPending}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {actionError && (
              <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
                {actionError}
              </div>
            )}
          </div>

          {/* Show products used in generation */}
          {selectedTrendingProducts.length > 0 && (
            <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <h4 className="font-semibold text-purple-900 dark:text-purple-200 mb-3 flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Products Featured in This Design:
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {selectedTrendingProducts.map((product, idx) => (
                  <a
                    key={idx}
                    href={product.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex flex-col bg-white dark:bg-gray-800 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow"
                  >
                    <img
                      src={product.image_url}
                      alt={product.title}
                      className="w-full aspect-square object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = `https://images.weserv.nl/?url=${encodeURIComponent(product.image_url)}&w=150&h=150&fit=cover`;
                      }}
                    />
                    <div className="p-2">
                      <p className="text-xs font-medium text-gray-900 dark:text-white line-clamp-2">
                        {product.title}
                      </p>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {product.store}
                        </span>
                        {product.price_str && (
                          <span className="text-xs font-semibold text-purple-600 dark:text-purple-400">
                            {product.price_str}
                          </span>
                        )}
                      </div>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* AI Furniture Identification Button */}
          <div className="mt-6 p-4 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-1">
                  Identify Furniture with AI
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Click to mark and identify multiple furniture items in the redesigned room
                </p>
              </div>
              <button
                onClick={() => setShowFurniturePanel(true)}
                className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
              >
                Identify Furniture
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Furniture Identification Panel */}
      {showFurniturePanel && generatedImageBase64 && (
        <FurnitureIdentificationPanel
          projectId={projectId}
          imageBase64={generatedImageBase64}
          imageType="inspiration"
          onClose={() => setShowFurniturePanel(false)}
        />
      )}
      <ImageLightbox
        isOpen={Boolean(lightboxImage)}
        src={lightboxImage?.src || ""}
        alt={lightboxImage?.alt || "Image preview"}
        onClose={() => setLightboxImage(null)}
      />

      {inspirationPrompt && (
        <div className="mt-6 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4">
          <h4 className="font-medium text-indigo-900 dark:text-indigo-200 mb-2">
            Prompt Used:
          </h4>
          <p className="text-indigo-800 dark:text-indigo-300 text-sm whitespace-pre-wrap">
            {inspirationPrompt}
          </p>
        </div>
      )}
    </div>
  );
}
