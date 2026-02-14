"use client";

import {
  useGenerateInspirationRecommendations,
  useSelectProductRecommendation,
} from "@/lib/api";
import { useState } from "react";

interface InspirationRecommendationsProps {
  projectId: string;
  recommendations: string[];
  spaceType: string;
  colorAnalysis?: Record<string, any> | null;
  styleAnalysis?: Record<string, any> | null;
  colorAnalysisSkipped?: boolean;
  styleAnalysisSkipped?: boolean;
  onGenerate?: () => void;
  canGenerate?: boolean;
  isGenerating?: boolean;
  errorMessage?: string;
}

export function InspirationRecommendations({
  projectId,
  recommendations,
  spaceType,
  colorAnalysis,
  styleAnalysis,
  colorAnalysisSkipped,
  styleAnalysisSkipped,
  onGenerate,
  canGenerate = true,
  isGenerating = false,
  errorMessage,
}: InspirationRecommendationsProps) {
  const generateMutation = useGenerateInspirationRecommendations();
  const selectMutation = useSelectProductRecommendation();
  const [selectedRecommendation, setSelectedRecommendation] = useState<string>("");

  const hasColor = Boolean(colorAnalysis) || Boolean(colorAnalysisSkipped);
  const hasStyle = Boolean(styleAnalysis) || Boolean(styleAnalysisSkipped);
  const readyForGeneration = hasColor && hasStyle;

  const handleGenerateRecommendations = () => {
    if (!readyForGeneration || (!canGenerate && !onGenerate)) return;
    if (onGenerate) {
      onGenerate();
    } else {
      generateMutation.mutate(projectId);
    }
  };

  const handleSelectRecommendation = (recommendation: string) => {
    setSelectedRecommendation(recommendation);
    selectMutation.mutate({
      projectId,
      selectedRecommendation: recommendation,
    });
  };

  if (recommendations.length > 0) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Inspiration-Based Recommendations
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            AI-generated recommendations based on your inspiration images for
            your {spaceType}
          </p>
        </div>

        {/* Recommendations Grid */}
        <div className="grid md:grid-cols-2 gap-4">
          {recommendations.map((recommendation, index) => (
            <div
              key={index}
              className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${selectedRecommendation === recommendation
                ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                : "border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-600"
                }`}
              onClick={() => handleSelectRecommendation(recommendation)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${selectedRecommendation === recommendation
                      ? "bg-purple-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                      }`}
                  >
                    {index + 1}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white capitalize">
                      {recommendation}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Click to search for products
                    </p>
                  </div>
                </div>
                {selectedRecommendation === recommendation &&
                  selectMutation.isPending && (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600"></div>
                  )}
              </div>
            </div>
          ))}
        </div>

        {selectMutation.isError && (
          <div className="mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-800 dark:text-red-200 text-sm">
              Error:{" "}
              {selectMutation.error?.message ||
                "Failed to select recommendation"}
            </p>
          </div>
        )}

        {/* Success / Next Step Message */}
        <div className="mt-6 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <svg
                className="w-5 h-5 text-purple-600 dark:text-purple-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <div>
                <span className="text-purple-800 dark:text-purple-200 font-medium block">
                  {selectedRecommendation ? "Recommendation Selected!" : "Ready to execute your vision!"}
                </span>
                <p className="text-purple-700 dark:text-purple-300 text-sm mt-1">
                  {selectedRecommendation
                    ? "Scroll down to the 'Product Search' section to find items matching this recommendation."
                    : "Select one of the inspiration-based recommendations above to find real products that match this style."}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Regenerate Option */}
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleGenerateRecommendations}
            disabled={isGenerating || generateMutation.isPending || !canGenerate}
            className="text-sm text-gray-500 hover:text-purple-600 dark:text-gray-400 dark:hover:text-purple-400 underline transition-colors"
          >
            {isGenerating ? "Regenerating..." : "Regenerate Recommendations"}
          </button>
        </div>
      </div>
    );
  }

  if (!readyForGeneration) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="text-center py-8 space-y-3">
          <div className="w-16 h-16 bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900/20 dark:to-pink-900/20 rounded-full flex items-center justify-center mx-auto">
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
                d="M12 8v4m0 4h.01M4.93 4.93l14.14 14.14"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Finish color & style to enable AI recommendations
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            Select a color palette and design style first, or skip both. Once
            those steps are set, the AI will generate four tailored inspiration
            recommendations for your {spaceType}.
          </p>
          <button
            disabled
            className="px-6 py-2 bg-gradient-to-r from-purple-600/50 to-pink-600/50 text-white rounded-lg opacity-60 cursor-not-allowed"
          >
            Generate Inspiration Recommendations
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900/20 dark:to-pink-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
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
          Generate Inspiration Recommendations
        </h3>
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          Upload inspiration images above, then generate AI recommendations
          based on your design inspiration.
        </p>
        <button
          onClick={handleGenerateRecommendations}
          disabled={isGenerating || generateMutation.isPending || !canGenerate}
          className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
        >
          {isGenerating || generateMutation.isPending
            ? "Generating..."
            : "Generate Inspiration Recommendations"}
        </button>

        {(generateMutation.isError || errorMessage) && (
          <div className="mt-4 text-red-600 dark:text-red-400 text-sm">
            Error: {errorMessage || generateMutation.error?.message}
          </div>
        )}
      </div>
    </div>
  );
}
