"use client";

import { useGenerateImage } from "@/lib/api";
import { useState } from "react";
import { FurnitureIdentificationPanel } from "./FurnitureIdentificationPanel";

interface SelectedProduct {
  url: string;
  title: string;
  image_url: string;
  selected_at: string;
}

interface GeneratedImageDisplayProps {
  projectId: string;
  selectedProduct: SelectedProduct;
  generatedImageBase64?: string; // Changed from URL to base64
  generationPrompt?: string;
}

export function GeneratedImageDisplay({
  projectId,
  selectedProduct,
  generatedImageBase64,
  generationPrompt,
}: GeneratedImageDisplayProps) {
  const generateImageMutation = useGenerateImage();
  const [imageError, setImageError] = useState(false);
  const [showFurniturePanel, setShowFurniturePanel] = useState(false);

  const handleGenerateImage = () => {
    generateImageMutation.mutate(projectId, {
      onError: (error) => {
        console.error("Failed to generate image:", error);
        alert("Failed to generate image. Please try again.");
      },
    });
  };

  // Show generation button if no image exists yet
  if (!generatedImageBase64) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Generate AI Visualization
        </h2>

        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
            Selected Product:
          </h3>
          <div className="flex items-center space-x-4">
            <img
              src={selectedProduct.image_url}
              alt={selectedProduct.title}
              className="w-16 h-16 object-cover rounded-lg"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.src = `https://images.weserv.nl/?url=${encodeURIComponent(
                  selectedProduct.image_url
                )}&w=64&h=64&fit=cover`;
              }}
            />
            <div>
              <p className="font-medium text-gray-900 dark:text-white">
                {selectedProduct.title}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Selected{" "}
                {new Date(selectedProduct.selected_at).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {generationPrompt && (
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 mb-6">
            <h4 className="font-medium text-blue-900 dark:text-blue-200 mb-2">
              Generation Prompt:
            </h4>
            <p className="text-blue-800 dark:text-blue-300 text-sm">
              {generationPrompt}
            </p>
          </div>
        )}

        <div className="text-center">
          <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-purple-600 dark:text-purple-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Generate AI Visualization
          </h3>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            Ready to create a custom visualization of your selected product
            using AI image generation.
          </p>
          <button
            onClick={handleGenerateImage}
            disabled={generateImageMutation.isPending}
            className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {generateImageMutation.isPending ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Generating with Gemini AI...</span>
              </div>
            ) : (
              "Generate Visualization with AI"
            )}
          </button>
          {generateImageMutation.isError && (
            <p className="text-red-600 dark:text-red-400 text-sm mt-2">
              Error generating image. Please try again.
            </p>
          )}
        </div>
      </div>
    );
  }

  // Show generated image
  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        🎨 AI Generated Visualization
      </h2>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Original Product */}
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
            Original Product
          </h3>
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <img
              src={selectedProduct.image_url}
              alt={selectedProduct.title}
              className="w-full h-48 object-cover rounded-lg mb-3"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.src = `https://images.weserv.nl/?url=${encodeURIComponent(
                  selectedProduct.image_url
                )}&w=400&h=300&fit=cover`;
              }}
            />
            <p className="font-medium text-gray-900 dark:text-white text-sm">
              {selectedProduct.title}
            </p>
          </div>
        </div>

        {/* Generated Visualization */}
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
            AI Generated Visualization
          </h3>
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            {!imageError ? (
              <img
                src={`data:image/png;base64,${generatedImageBase64}`}
                alt="AI Generated Visualization"
                className="w-full h-48 object-cover rounded-lg mb-3"
                onError={() => setImageError(true)}
              />
            ) : (
              <div className="w-full h-48 bg-gray-200 dark:bg-gray-600 rounded-lg mb-3 flex items-center justify-center">
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
                    Failed to load generated image
                  </p>
                </div>
              </div>
            )}
            <p className="font-medium text-gray-900 dark:text-white text-sm">
              Generated by Gemini AI
            </p>
          </div>
        </div>
      </div>

      {/* AI Furniture Identification Button */}
      <div className="mt-6 p-4 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-1">
              🔍 Identify Furniture with AI
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Click to mark and identify multiple furniture items in the visualization
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

      {/* Furniture Identification Panel */}
      {showFurniturePanel && generatedImageBase64 && (
        <FurnitureIdentificationPanel
          projectId={projectId}
          imageBase64={generatedImageBase64}
          imageType="product"
          onClose={() => setShowFurniturePanel(false)}
        />
      )}

      {generationPrompt && (
        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 dark:text-blue-200 mb-2">
            Generation Prompt Used:
          </h4>
          <p className="text-blue-800 dark:text-blue-300 text-sm">
            {generationPrompt}
          </p>
        </div>
      )}

      <div className="mt-6 flex justify-center">
        <button
          onClick={handleGenerateImage}
          disabled={generateImageMutation.isPending}
          className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          {generateImageMutation.isPending ? (
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Regenerating...</span>
            </div>
          ) : (
            "Regenerate Image"
          )}
        </button>
      </div>
    </div>
  );
}
