"use client";

import {
  useGenerateProductRecommendations,
  useSelectProductRecommendation,
} from "@/lib/api";
import { useState } from "react";

interface ProductRecommendationsProps {
  projectId: string;
  recommendations: string[];
  spaceType: string;
}

export function ProductRecommendations({
  projectId,
  recommendations,
  spaceType,
}: ProductRecommendationsProps) {
  const generateMutation = useGenerateProductRecommendations();
  const selectMutation = useSelectProductRecommendation();
  const [selectedRecommendation, setSelectedRecommendation] =
    useState<string>("");

  const handleGenerateRecommendations = () => {
    generateMutation.mutate(projectId);
  };

  const handleSelectRecommendation = (recommendation: string) => {
    setSelectedRecommendation(recommendation);
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

  // Show recommendation selection
  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Product Recommendations
      </h2>
      <div className="space-y-4">
        <p className="text-gray-600 dark:text-gray-300">
          Based on your {spaceType} design project, here are two specific
          recommendations to transform your space:
        </p>

        <div className="grid md:grid-cols-2 gap-4">
          {recommendations.map((recommendation, index) => (
            <div
              key={index}
              className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                selectedRecommendation === recommendation
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                  : "border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600"
              }`}
              onClick={() => handleSelectRecommendation(recommendation)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      selectedRecommendation === recommendation
                        ? "bg-blue-500 text-white"
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
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                  )}
              </div>
            </div>
          ))}
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

        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-blue-800 dark:text-blue-200 text-sm">
            💡 <strong>Next step:</strong> Select one of the recommendations
            above to find specific products that match your style and space
            requirements.
          </p>
        </div>
      </div>
    </div>
  );
}
