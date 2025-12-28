"use client";

import {
  useGenerateProductRecommendations,
  useSelectProductRecommendation,
} from "@/lib/api";
import { useState, useEffect } from "react";

interface ProductRecommendationsProps {
  projectId: string;
  recommendations: string[];
  spaceType: string;
  selectedRecommendations?: string[];
}

export function ProductRecommendations({
  projectId,
  recommendations,
  spaceType,
  selectedRecommendations: initialSelected = [],
}: ProductRecommendationsProps) {
  const generateMutation = useGenerateProductRecommendations();
  const selectMutation = useSelectProductRecommendation();
  const [localSelected, setLocalSelected] = useState<string[]>(initialSelected);

  // Sync with props when they change (e.g., after API update)
  useEffect(() => {
    setLocalSelected(initialSelected);
  }, [initialSelected]);

  const handleGenerateRecommendations = () => {
    generateMutation.mutate(projectId);
  };

  const handleToggleRecommendation = (recommendation: string) => {
    // Optimistically update local state
    const newSelected = localSelected.includes(recommendation)
      ? localSelected.filter((r) => r !== recommendation)
      : [...localSelected, recommendation];
    setLocalSelected(newSelected);

    // Call API to toggle
    selectMutation.mutate({
      projectId,
      selectedRecommendation: recommendation,
    });
  };

  // Show generate button if no recommendations yet
  if (recommendations.length === 0) {
    return (
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Product Recommendations
        </h2>
        <div className="text-center">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-blue-600 dark:text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Ready for Product Recommendations
          </h3>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            Get AI-powered product recommendations based on your {spaceType}{" "}
            design project. We'll analyze your style preferences and suggest
            specific items to transform your space.
          </p>
          <button
            onClick={handleGenerateRecommendations}
            disabled={generateMutation.isPending}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {generateMutation.isPending ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Generating Recommendations...</span>
              </div>
            ) : (
              "Get Product Recommendations"
            )}
          </button>
          {generateMutation.isError && (
            <p className="text-red-600 dark:text-red-400 text-sm mt-2">
              Error:{" "}
              {generateMutation.error?.message ||
                "Failed to generate recommendations"}
            </p>
          )}
        </div>
      </div>
    );
  }

  // Show recommendation selection (multi-select)
  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Product Recommendations
        </h2>
        {localSelected.length > 0 && (
          <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
            {localSelected.length} selected
          </span>
        )}
      </div>
      <div className="space-y-4">
        <p className="text-gray-600 dark:text-gray-300">
          Based on your {spaceType} design project, here are four specific
          recommendations to transform your space:
        </p>

        <div className="grid md:grid-cols-2 gap-4">
          {recommendations.map((recommendation, index) => {
            const isSelected = localSelected.includes(recommendation);
            return (
              <div
                key={index}
                className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${isSelected
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                    : "border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600"
                  }`}
                onClick={() => handleToggleRecommendation(recommendation)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center border-2 ${isSelected
                          ? "bg-blue-500 border-blue-500 text-white"
                          : "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600"
                        }`}
                    >
                      {isSelected ? (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <span className="text-gray-500 dark:text-gray-400">{index + 1}</span>
                      )}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white capitalize">
                        {recommendation}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Click to {isSelected ? "deselect" : "select"}
                      </p>
                    </div>
                  </div>
                  {selectMutation.isPending && (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {selectMutation.isError && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-800 dark:text-red-200 text-sm">
              Error:{" "}
              {selectMutation.error?.message ||
                "Failed to select recommendation"}
            </p>
          </div>
        )}

        {/* Next Steps Guidance */}
        <div className={`border rounded-lg p-4 ${localSelected.length > 0
            ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
            : "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800"
          }`}>
          {localSelected.length > 0 ? (
            <div>
              <p className="text-green-800 dark:text-green-200 text-sm font-medium">
                ✅ <strong>{localSelected.length} recommendation{localSelected.length > 1 ? "s" : ""} selected!</strong>
              </p>
              <p className="text-green-700 dark:text-green-300 text-sm mt-1">
                Scroll down to the Product Search section to find real products that match "{localSelected[0]}".
              </p>
            </div>
          ) : (
            <p className="text-blue-800 dark:text-blue-200 text-sm">
              💡 <strong>Next step:</strong> Select one or more recommendations
              above to find specific products that match your style and space
              requirements.
            </p>
          )}
        </div>

        {/* Regenerate Option */}
        <div className="flex justify-end">
          <button
            onClick={handleGenerateRecommendations}
            disabled={generateMutation.isPending}
            className="text-sm text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 underline transition-colors"
          >
            {generateMutation.isPending ? "Regenerating..." : "Regenerate Recommendations"}
          </button>
        </div>
      </div>
    </div>
  );
}

